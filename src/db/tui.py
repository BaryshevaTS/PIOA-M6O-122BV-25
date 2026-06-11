import sys
from typing import Any, Dict, List, Optional
from .backend.database import Database


class DatabaseTUI:
    DEFAULT_SCHEMA: Dict[str, type] = {"title": str, "author": str, "year": int, "pages": int}

    def __init__(self, db_instance: Database) -> None:
        self.db = db_instance
        if "books" not in self.db.list_tables():
            self.db.create_table("books", self.DEFAULT_SCHEMA)

    def run(self) -> None:
        while True:
            self._print_menu()
            choice = input("Выберите действие: ").strip()
            try:
                actions = {
                    "1": self._add_record,
                    "2": self._show_all_records,
                    "3": self._find_records_by_filter,
                    "4": self._update_record,
                    "5": self._delete_record,
                    "6": self._show_tables,
                    "7": self._create_new_table,
                    "8": self._sort_records_view,
                    "9": self._create_index_view,
                    "0": self._exit,
                }
                action = actions.get(choice)
                if action:
                    action()
                else:
                    print("Неверный ввод. Выберите число от 0 до 9.")
            except (EOFError, KeyboardInterrupt):
                print("\nРабота прервана пользователем.")
                break
            except Exception as exc:
                print(f"Непредвиденная ошибка: {exc}")
        print("Завершение работы.")

    def _print_menu(self) -> None:
        print("\n=== База данных библиотеки ===")
        print(f"Формат хранения: {self._get_format_name()}")
        print("1. Добавить запись")
        print("2. Показать все записи")
        print("3. Найти записи по фильтру")
        print("4. Обновить запись")
        print("5. Удалить запись")
        print("6. Показать доступные таблицы")
        print("7. Создать новую таблицу")
        print("8. Сортировать записи")
        print("9. Создать индекс")
        print("0. Выход")

    def _get_format_name(self) -> str:
        class_name = self.db.__class__.__name__
        if class_name == "JsonDatabase":
            return "JSON"
        elif class_name == "CsvDatabase":
            return "CSV"
        elif class_name == "InMemoryDB":
            return "In-Memory"
        return class_name

    @staticmethod
    def _read_int(prompt: str) -> int:
        while True:
            raw = input(prompt).strip()
            try:
                return int(raw)
            except ValueError:
                print("Ошибка: введите целое число.")

    @staticmethod
    def _read_float(prompt: str) -> float:
        while True:
            raw = input(prompt).strip()
            try:
                return float(raw)
            except ValueError:
                print("Ошибка: введите число.")

    @staticmethod
    def _read_optional_int(prompt: str) -> Optional[int]:
        while True:
            raw = input(prompt).strip()
            if raw == "":
                return None
            try:
                return int(raw)
            except ValueError:
                print("Ошибка: введите целое число или оставьте поле пустым.")

    @staticmethod
    def _read_optional_float(prompt: str) -> Optional[float]:
        while True:
            raw = input(prompt).strip()
            if raw == "":
                return None
            try:
                return float(raw)
            except ValueError:
                print("Ошибка: введите число или оставьте поле пустым.")

    @staticmethod
    def _read_string(prompt: str) -> str:
        while True:
            raw = input(prompt).strip()
            if raw:
                return raw
            print("Ошибка: поле не может быть пустым.")

    @staticmethod
    def _parse_schema_input(raw: str) -> Dict[str, type]:
        schema: Dict[str, type] = {}
        type_map = {"str": str, "int": int, "float": float}
        for pair in raw.split(","):
            if ":" not in pair:
                raise ValueError("Ожидался формат: поле:тип, поле:тип")
            field, type_name = pair.strip().split(":", 1)
            field, type_name = field.strip(), type_name.strip()
            if type_name not in type_map:
                raise ValueError(f"Неподдерживаемый тип: {type_name}. Доступные: str, int, float.")
            schema[field] = type_map[type_name]
        if not schema:
            raise ValueError("Схема не может быть пустой.")
        return schema

    def _add_record(self) -> None:
        print("\nДобавление записи")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        tables = self.db.list_tables()
        if table_name not in tables:
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return

        schema = tables[table_name]["schema"]
        data: Dict[str, Any] = {}
        print(f"Введите данные для полей таблицы '{table_name}':")
        for field, expected_type in schema.items():
            if expected_type is int:
                data[field] = self._read_int(f"{field} (int): ")
            elif expected_type is float:
                data[field] = self._read_float(f"{field} (float): ")
            else:
                data[field] = self._read_string(f"{field} (str): ")

        try:
            record = self.db.create_record(table_name, **data)
            print(f"Запись добавлена: {record}")
        except ValueError as exc:
            print(f"Ошибка: {exc}")

    @staticmethod
    def _print_records(records: List[Dict[str, Any]]) -> None:
        if not records:
            print("Записи не найдены.")
            return
        headers = list(records[0].keys())
        print(" | ".join(f"{h:<12}" for h in headers))
        print("-" * (len(headers) * 14))
        for record in records:
            values = [str(record.get(h, "")) for h in headers]
            print(" | ".join(f"{v:<12}" for v in values))

    def _show_all_records(self) -> None:
        print("\nСписок записей")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return
        self._print_records(self.db.select_record(table_name))

    def _find_records_by_filter(self) -> None:
        print("\nПоиск по фильтру (Enter = пропустить поле)")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return

        schema = self.db.list_tables()[table_name]["schema"]
        filters: Dict[str, Any] = {}
        print(f"Введите значения для фильтрации таблицы '{table_name}':")
        for field, expected_type in schema.items():
            if expected_type is int:
                val = self._read_optional_int(f"{field} (int): ")
            elif expected_type is float:
                val = self._read_optional_float(f"{field} (float): ")
            else:
                raw = input(f"{field} (str): ").strip()
                val = raw or None
            if val is not None:
                filters[field] = val

        records = self.db.select_record(table_name, **filters)
        self._print_records(records)

    def _update_record(self) -> None:
        print("\nОбновление записи")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return

        record_id = self._read_int("ID записи: ")
        schema = self.db.list_tables()[table_name]["schema"]
        update_data: Dict[str, Any] = {}

        print("Введите новые значения (Enter = не изменять поле):")
        for field, expected_type in schema.items():
            if expected_type is int:
                val = self._read_optional_int(f"{field} (int): ")
            elif expected_type is float:
                val = self._read_optional_float(f"{field} (float): ")
            else:
                raw = input(f"{field} (str): ").strip()
                val = raw or None
            if val is not None:
                update_data[field] = val

        if not update_data:
            print("Не выбрано полей для обновления.")
            return

        try:
            self.db.update_record(table_name, record_id, **update_data)
            print("Запись успешно обновлена.")
        except ValueError as exc:
            print(f"Ошибка: {exc}")

    def _delete_record(self) -> None:
        print("\nУдаление записи")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return

        record_id = self._read_int("ID записи для удаления: ")
        try:
            self.db.delete_record(table_name, record_id)
            print("Запись успешно удалена.")
        except ValueError as exc:
            print(f"Ошибка: {exc}")

    def _show_tables(self) -> None:
        print("\n=== Доступные таблицы ===")
        tables_info = self.db.list_tables()
        if not tables_info:
            print("Таблицы отсутствуют.")
            return
        for name, info in tables_info.items():
            schema = info["schema"]
            count = info["record_count"]
            schema_str = ", ".join(f"{field}:{t.__name__}" for field, t in schema.items())
            print(f"- {name} [Схема: {schema_str}, Записей: {count}]")

    def _create_new_table(self) -> None:
        print("\nСоздание новой таблицы")
        table_name = input("Введите имя таблицы: ").strip()
        if not table_name:
            print("Ошибка: имя таблицы не может быть пустым.")
            return
        schema_raw = input("Введите схему (формат: поле:тип, поле:тип): ").strip()
        if not schema_raw:
            print("Ошибка: схема не может быть пустой.")
            return
        try:
            schema = self._parse_schema_input(schema_raw)
            self.db.create_table(table_name, schema)
            print(f"Таблица '{table_name}' успешно создана.")
        except ValueError as exc:
            print(f"Ошибка создания таблицы: {exc}")

    def _sort_records_view(self) -> None:
        print("\nСортировка записей")
        table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return

        field = input("Поле для сортировки: ").strip()
        if not field:
            print("Ошибка: поле не может быть пустым.")
            return

        desc = input("По убыванию? (y/n, Enter -> возрастание): ").strip().lower() == "y"
        try:
            records = self.db.sort_records(table_name, field, descending=desc)
            self._print_records(records)
        except ValueError as exc:
            print(f"Ошибка: {exc}")

    def _create_index_view(self) -> None:
        print("\nСоздание индекса")
        table_name = input("Имя таблицы: ").strip()
        if table_name not in self.db.list_tables():
            print(f"Ошибка: таблица '{table_name}' не найдена.")
            return
        
        field = input("Поле для индексации: ").strip()
        if not field:
            print("Ошибка: поле не может быть пустым.")
            return
        
        try:
            if hasattr(self.db, 'create_index'):
                result = self.db.create_index(table_name, field)
                if result:
                    print(f"Индекс по полю '{field}' создан успешно!")
                else:
                    print(f"Индекс по полю '{field}' уже существует.")
            else:
                print("Ошибка: текущая БД не поддерживает индексы.")
        except ValueError as exc:
            print(f"Ошибка: {exc}")

    def _exit(self) -> None:
        sys.exit(0)
