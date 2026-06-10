from typing import Any, Dict, List, Optional, Set
from .errors import TableNotFoundError, ValidationError

class IndexedDatabaseMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._indexes: Dict[str, Dict[str, Dict[Any, Set[int]]]] = {}

    def create_index(self, table_name: str, field: str) -> bool:
        if table_name not in self._get_tables():
            raise TableNotFoundError(f"Таблица '{table_name}' не найдена.")
        
        schema = self.get_schema(table_name)
        if field not in schema:
            raise ValidationError(f"Поле '{field}' не найдено в схеме таблицы '{table_name}'.")
        
        if table_name not in self._indexes:
            self._indexes[table_name] = {}
        if field in self._indexes[table_name]:
            return False
            
        self._indexes[table_name][field] = {}
        for rec in self._get_records(table_name):
            val = rec.get(field)
            if val is not None:
                self._indexes[table_name][field].setdefault(val, set()).add(rec["id"])
        return True

    def drop_index(self, table_name: str, field: str) -> bool:
        if table_name in self._indexes and field in self._indexes[table_name]:
            del self._indexes[table_name][field]
            return True
        return False

    def _update_index_on_create(self, table_name: str, record: Dict[str, Any]) -> None:
        if table_name in self._indexes:
            for field, idx in self._indexes[table_name].items():
                val = record.get(field)
                if val is not None:
                    idx.setdefault(val, set()).add(record["id"])

    def _update_index_on_update(self, table_name: str, old: Dict[str, Any], new: Dict[str, Any]) -> None:
        if table_name in self._indexes:
            for field, idx in self._indexes[table_name].items():
                ov, nv = old.get(field), new.get(field)
                if ov != nv:
                    if ov is not None and ov in idx:
                        idx[ov].discard(new["id"])
                        if not idx[ov]:
                            del idx[ov]
                    if nv is not None:
                        idx.setdefault(nv, set()).add(new["id"])

    def _update_index_on_delete(self, table_name: str, record: Dict[str, Any]) -> None:
        if table_name in self._indexes:
            for field, idx in self._indexes[table_name].items():
                val = record.get(field)
                if val is not None and val in idx:
                    idx[val].discard(record["id"])
                    if not idx[val]:
                        del idx[val]

    def _has_index_for_filter(self, table_name: str, filters: Dict[str, Any]) -> bool:
        if table_name not in self._indexes:
            return False
        return any(f in self._indexes[table_name] for f in filters)

    def _get_indexed_ids(self, table_name: str, filters: Dict[str, Any]) -> Optional[Set[int]]:
        if table_name not in self._indexes:
            return None
        for f, v in filters.items():
            if f in self._indexes[table_name]:
                return self._indexes[table_name][f].get(v)
        return None

    def _get_tables(self) -> Dict[str, Any]:
        raise NotImplementedError

    def _get_records(self, table_name: str) -> List[Dict[str, Any]]:
        raise NotImplementedError
