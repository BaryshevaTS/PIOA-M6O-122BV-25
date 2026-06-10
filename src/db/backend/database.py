from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Database(ABC):
    @abstractmethod
    def create_table(self, table_name: str, schema: Dict[str, type]) -> None: pass

    @abstractmethod
    def list_tables(self) -> Dict[str, Dict[str, Any]]: pass

    @abstractmethod
    def create_record(self, table_name: str, **data: Any) -> Dict[str, Any]: pass

    @abstractmethod
    def select_record(self, table_name: str, **filters: Any) -> List[Dict[str, Any]]: pass

    @abstractmethod
    def update_record(self, table_name: str, record_id: int, **data: Any) -> None: pass

    @abstractmethod
    def delete_record(self, table_name: str, record_id: int) -> None: pass

    @abstractmethod
    def sort_records(self, table_name: str, field: str, descending: bool = False) -> List[Dict[str, Any]]: pass
    
    @abstractmethod
    def get_schema(self, table_name: str) -> Dict[str, type]: pass
