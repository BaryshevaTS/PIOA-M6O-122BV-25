import copy
from typing import Any, Dict, List


class InMemoryDB:

    def __init__(self) -> None:
        self._tables: Dict[str, List[Dict[str, Any]]] = {}
        self._schemas: Dict[str, Dict[str, type]] = {}
        self._id_counters: Dict[str, int] = {}

    def create_table(self, table_name: str, schema: Dict[str, type]) -> None:
        if table_name in self._tables:
            raise ValueError(f"Таблица '{table_name}' уже существует.")
        self._tables[table_name] = []
        self._schemas[table_name] = schema.copy()
        self._id_counters[table_name] = 1

    def list_tables(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "schema": self._schemas[name],
                "record_count": len(self._tables[name])
            }
            for name in self._tables
        }

    def has_table(self, table_name: str) -> bool:
        return table_name in self._tables

    def get_schema(self, table_name: str) -> Dict[str, type]:
        if table_name not in self._schemas:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        return self._schemas[table_name].copy()

    @staticmethod
    def _validate_record(schema: Dict[str, type], data: Dict[str, Any]) -> None:
        extra = set(data.keys()) - set(schema.keys()) - {"id"}
        if extra:
            raise ValueError(f"Недопустимые поля: {', '.join(extra)}")

        missing = [field for field in schema if field not in data]
        if missing:
            raise ValueError(f"Отсутствуют обязательные поля: {', '.join(missing)}")

        for field, expected_type in schema.items():
            value = data[field]
            if not isinstance(value, expected_type) or (expected_type is int and isinstance(value, bool)):
                raise ValueError(
                    f"Поле '{field}' ожидает {expected_type.__name__}, "
                    f"получено {type(value).__name__}."
                )

        for field in ("year", "age", "pages", "price", "quantity"):
            if field in data and isinstance(data[field], (int, float)) and data[field] < 0:
                raise ValueError(f"Поле '{field}' не может быть отрицательным.")

    def create_record(self, table_name: str, **data: Any) -> Dict[str, Any]:
        if table_name not in self._tables:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValueError("Данные записи не могут быть пустыми.")

        self._validate_record(self._schemas[table_name], data)

        record_id = self._id_counters[table_name]
        new_record = {"id": record_id, **data}
        self._tables[table_name].append(new_record)
        self._id_counters[table_name] += 1
        return copy.deepcopy(new_record)

    def select_record(self, table_name: str, **filters: Any) -> List[Dict[str, Any]]:
        if table_name not in self._tables:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        if not filters:
            return [copy.deepcopy(record) for record in self._tables[table_name]]
        return [
            copy.deepcopy(r) for r in self._tables[table_name]
            if all(r.get(k) == v for k, v in filters.items())
        ]

    def update_record(self, table_name: str, record_id: int, **data: Any) -> None:
        if table_name not in self._tables:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        if not data:
            raise ValueError("Не указаны поля для обновления.")

        target = next((r for r in self._tables[table_name] if r["id"] == record_id), None)
        if target is None:
            raise ValueError(f"Запись с id={record_id} не найдена.")

        temp = {**target, **data}
        self._validate_record(self._schemas[table_name], temp)
        target.update(data)

    def delete_record(self, table_name: str, record_id: int) -> None:
        if table_name not in self._tables:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        for i, record in enumerate(self._tables[table_name]):
            if record["id"] == record_id:
                del self._tables[table_name][i]
                return
        raise ValueError(f"Запись с id={record_id} не найдена.")

    def sort_records(self, table_name: str, field: str, descending: bool = False) -> List[Dict[str, Any]]:
        if table_name not in self._tables:
            raise ValueError(f"Таблица '{table_name}' не найдена.")
        if field not in self._schemas.get(table_name, {}):
            raise ValueError(f"Поле '{field}' не найдено в схеме таблицы '{table_name}'.")
        try:
            return [
                copy.deepcopy(r) for r in sorted(
                    self._tables[table_name],
                    key=lambda x: x.get(field),
                    reverse=descending
                )
            ]
        except TypeError as exc:
            raise ValueError(f"Невозможно отсортировать по полю '{field}': {exc}") from exc
        