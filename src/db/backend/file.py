import json
import re
import copy
from pathlib import Path
from typing import Any, Dict, List
from .database import Database
from .errors import (
    FileStorageError,
    TableNotFoundError,
    TableExistsError,
    RecordNotFoundError,
    ValidationError,
)
from .memory import InMemoryDB
from .indexed import IndexedDatabaseMixin

class JsonDatabase(IndexedDatabaseMixin, Database):
    TYPE_MAP = {"str": str, "int": int, "float": float}
    REVERSE_TYPE_MAP = {v: k for k, v in TYPE_MAP.items()}

    def __init__(self, storage_dir: str = "data") -> None:
        super().__init__()
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    @staticmethod
    def _validate_table_name(table_name: str) -> None:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", table_name):
            raise ValueError(f"Недопустимое имя таблицы '{table_name}': используйте только буквы, цифры, '_' и '-'.")

    def _load_all(self) -> None:
        for p in self._storage_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = json.load(f)
                
                if not isinstance(content, dict):
                    raise FileStorageError(f"Неверная структура файла '{p.stem}': ожидается объект JSON.")
                
                required_keys = {"schema", "records", "id_counter"}
                if not required_keys.issubset(content.keys()):
                    raise FileStorageError(f"Неверная структура файла '{p.stem}': отсутствуют обязательные поля {required_keys}.")
                
                if not isinstance(content["schema"], dict):
                    raise FileStorageError(f"Неверная структура файла '{p.stem}': поле 'schema' должно быть объектом.")
                
                if not isinstance(content["records"], list):
                    raise FileStorageError(f"Неверная структура файла '{p.stem}': поле 'records' должно быть массивом.")
                
                if not isinstance(content["id_counter"], int):
                    raise FileStorageError(f"Неверная структура файла '{p.stem}': поле 'id_counter' должно быть числом.")
                
                self._cache[p.stem] = content

                for field in content.get("indexed_fields", []):
                    try:
                        self.create_index(p.stem, field)
                    except (ValueError, ValidationError):
                        pass
            except json.JSONDecodeError as e:
                raise FileStorageError(f"Ошибка чтения '{p.stem}': невалидный JSON - {e}")
            except FileStorageError:
                raise
            except IOError as e:
                raise FileStorageError(f"Ошибка чтения '{p.stem}': {e}")

    def _save_table(self, table_name: str) -> None:
        try:
            with open(self._storage_dir / f"{table_name}.json", "w", encoding="utf-8") as f:
                json.dump(self._cache[table_name], f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise FileStorageError(f"Ошибка записи '{table_name}': {e}")

    def _deserialize_schema(self, s: Dict[str, str]) -> Dict[str, type]:
        schema: Dict[str, type] = {}
        for field, type_name in s.items():
            if type_name not in self.TYPE_MAP:
                raise FileStorageError(f"Неподдерживаемый тип '{type_name}' в поле '{field}' файла схемы.")
            schema[field] = self.TYPE_MAP[type_name]
        return schema

    def _serialize_schema(self, s: Dict[str, type]) -> Dict[str, str]:
        return {f: self.REVERSE_TYPE_MAP.get(t, "str") for f, t in s.items()}

    def create_table(self, table_name: str, schema: Dict[str, type]) -> None:
        self._validate_table_name(table_name)
        if table_name in self._cache:
            raise TableExistsError(f"Таблица '{table_name}' уже существует.")
        self._cache[table_name] = {
            "schema": self._serialize_schema(schema),
            "records": [],
            "id_counter": 1,
            "indexed_fields": []
        }
        self._save_table(table_name)

    def list_tables(self) -> Dict[str, Dict[str, Any]]:
        return {
            n: {
                "schema": self._deserialize_schema(t["schema"]).copy(),
                "record_count": len(t["records"])
            }
            for n, t in self._cache.items()
        }

    def get_schema(self, table_name: str) -> Dict[str, type]:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        return self._deserialize_schema(self._cache[table_name]["schema"]).copy()

    def _get_tables(self) -> Dict[str, Any]:
        return self._cache

    def _get_records(self, table_name: str) -> List[Dict[str, Any]]:
        return self._cache.get(table_name, {}).get("records", [])

    def create_record(self, table_name: str, **data: Any) -> Dict[str, Any]:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValidationError("Данные записи не могут быть пустыми.")
        InMemoryDB._validate_record(self._deserialize_schema(self._cache[table_name]["schema"]), data)
        rid = self._cache[table_name]["id_counter"]
        new = {**data, "id": rid}
        self._cache[table_name]["records"].append(new)
        self._cache[table_name]["id_counter"] += 1
        self._update_index_on_create(table_name, new)
        self._save_table(table_name)
        return copy.deepcopy(new)

    def select_record(self, table_name: str, **filters: Any) -> List[Dict[str, Any]]:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        recs = self._cache[table_name]["records"]
        if not filters:
            return [copy.deepcopy(r) for r in recs]
        if self._has_index_for_filter(table_name, filters):
            ids = self._get_indexed_ids(table_name, filters)
            if ids is not None:
                return [copy.deepcopy(r) for r in recs if r["id"] in ids and all(r.get(k) == v for k, v in filters.items())]
        return [copy.deepcopy(r) for r in recs if all(r.get(k) == v for k, v in filters.items())]

    def update_record(self, table_name: str, record_id: int, **data: Any) -> None:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValidationError("Не указаны поля для обновления.")
        target = next((r for r in self._cache[table_name]["records"] if r["id"] == record_id), None)
        if target is None:
            raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")
        safe_data = {k: v for k, v in data.items() if k != "id"}
        InMemoryDB._validate_record(self._deserialize_schema(self._cache[table_name]["schema"]), {**target, **safe_data})
        old = target.copy()
        target.update(safe_data)
        self._update_index_on_update(table_name, old, target)
        self._save_table(table_name)

    def delete_record(self, table_name: str, record_id: int) -> None:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        recs = self._cache[table_name]["records"]
        for i, r in enumerate(recs):
            if r["id"] == record_id:
                self._update_index_on_delete(table_name, r)
                del recs[i]
                self._save_table(table_name)
                return
        raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")

    def sort_records(self, table_name: str, field: str, descending: bool = False) -> List[Dict[str, Any]]:
        if table_name not in self._cache:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if field not in self._deserialize_schema(self._cache[table_name]["schema"]):
            raise ValidationError(f"Поле '{field}' не найдено.")
        try:
            return [copy.deepcopy(r) for r in sorted(self._cache[table_name]["records"], key=lambda x: x.get(field), reverse=descending)]
        except TypeError as exc:
            raise ValidationError(f"Невозможно отсортировать по полю '{field}': {exc}") from exc

    def create_index(self, table_name: str, field: str) -> bool:
        created = super().create_index(table_name, field)
        if created:
            self._cache[table_name].setdefault("indexed_fields", []).append(field)
            self._save_table(table_name)
        return created

    def drop_index(self, table_name: str, field: str) -> bool:
        dropped = super().drop_index(table_name, field)
        if dropped:
            fields = self._cache[table_name].get("indexed_fields", [])
            if field in fields:
                fields.remove(field)
                self._save_table(table_name)
        return dropped
