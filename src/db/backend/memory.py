import copy
from typing import Any, Dict, List
from .database import Database
from .errors import (
    TableExistsError,
    TableNotFoundError,
    RecordNotFoundError,
    ValidationError,
)

class InMemoryDB(Database):
    def __init__(self) -> None:
        self._tables: Dict[str, List[Dict[str, Any]]] = {}
        self._schemas: Dict[str, Dict[str, type]] = {}
        self._id_counters: Dict[str, int] = {}

    def create_table(self, table_name: str, schema: Dict[str, type]) -> None:
        if table_name in self._tables:
            raise TableExistsError(f"Таблица '{table_name}' уже существует.")
        self._tables[table_name] = []
        self._schemas[table_name] = schema.copy()
        self._id_counters[table_name] = 1

    def list_tables(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "schema": self._schemas[name].copy(),
                "record_count": len(self._tables[name])
            }
            for name in self._tables
        }

    def has_table(self, table_name: str) -> bool:
        return table_name in self._tables

    def get_schema(self, table_name: str) -> Dict[str, type]:
        if table_name not in self._schemas:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        return self._schemas[table_name].copy()

    def _get_tables(self) -> Dict[str, Any]:
        return {
            name: {
                "schema": self._schemas[name],
                "records": self._tables[name],
                "id_counter": self._id_counters[name]
            }
            for name in self._tables
        }

    def _get_records(self, table_name: str) -> List[Dict[str, Any]]:
        return self._tables.get(table_name, [])

    @staticmethod
    def _validate_record(schema: Dict[str, type], data: Dict[str, Any]) -> None:
        extra = set(data.keys()) - set(schema.keys()) - {"id"}
        if extra:
            raise ValidationError(f"Недопустимые поля: {', '.join(extra)}")
        missing = [f for f in schema if f not in data]
        if missing:
            raise ValidationError(f"Отсутствуют обязательные поля: {', '.join(missing)}")
        for f, t in schema.items():
            v = data[f]
            if not isinstance(v, t) or (t is int and isinstance(v, bool)):
                raise ValidationError(f"Поле '{f}' ожидает {t.__name__}, получено {type(v).__name__}.")
        for f in ("year", "age", "pages", "price", "quantity"):
            if f in data and isinstance(data[f], (int, float)) and data[f] < 0:
                raise ValidationError(f"Поле '{f}' не может быть отрицательным.")

    def create_record(self, table_name: str, **data: Any) -> Dict[str, Any]:
        if table_name not in self._tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValidationError("Данные записи не могут быть пустыми.")
        self._validate_record(self._schemas[table_name], data)
        record_id = self._id_counters[table_name]
        new_record = {**data, "id": record_id}
        self._tables[table_name].append(new_record)
        self._id_counters[table_name] += 1
        return copy.deepcopy(new_record)

    def select_record(self, table_name: str, **filters: Any) -> List[Dict[str, Any]]:
        if table_name not in self._tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        recs = self._tables[table_name]
        if not filters:
            return [copy.deepcopy(r) for r in recs]
        return [copy.deepcopy(r) for r in recs if all(r.get(k) == v for k, v in filters.items())]

    def update_record(self, table_name: str, record_id: int, **data: Any) -> None:
        if table_name not in self._tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValidationError("Не указаны поля для обновления.")
        target = next((r for r in self._tables[table_name] if r["id"] == record_id), None)
        if target is None:
            raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")
        safe_data = {k: v for k, v in data.items() if k != "id"}
        self._validate_record(self._schemas[table_name], {**target, **safe_data})
        target.update(safe_data)

    def delete_record(self, table_name: str, record_id: int) -> None:
        if table_name not in self._tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        for i, r in enumerate(self._tables[table_name]):
            if r["id"] == record_id:
                del self._tables[table_name][i]
                return
        raise RecordNotFoundError(f"Запись с id={record_id} не найдена.")

    def sort_records(self, table_name: str, field: str, descending: bool = False) -> List[Dict[str, Any]]:
        if table_name not in self._tables:
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        if field not in self._schemas.get(table_name, {}):
            raise ValidationError(f"Поле '{field}' не найдено.")
        try:
            return [copy.deepcopy(r) for r in sorted(self._tables[table_name], key=lambda x: x.get(field), reverse=descending)]
        except TypeError as exc:
            raise ValidationError(f"Невозможно отсортировать по полю '{field}': {exc}") from exc
