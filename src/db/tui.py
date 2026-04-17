import sys
from typing import Any, Dict, List
from .backend import memory

# Схема таблицы по умолчанию: библиотека книг.
DEFAULT_SCHEMA: Dict[str, type] = {
    "title": str,
    "author": str,
    "year": int,
    "pages": int
}

# Инициализация базы данных при загрузке модуля.
memory.create_table("books", DEFAULT_SCHEMA)


def _print_menu() -> None:
    print("\n=== База данных библиотеки ===")
    print("1. Добавить запись")
    print("2. Показать все записи")
    print("3. Найти записи по фильтру")
    print("4. Обновить запись")
    print("5. Удалить запись")
    print("6. Показать доступные таблицы")
    print("7. Создать новую таблицу")
    print("0. Выход")


def _read_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("Ошибка: введите целое число.")


def _read_optional_int(prompt: str) -> int | None:
    while True:
        raw = input(prompt).strip()
        if raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            print("Ошибка: введите целое число или оставьте поле пустым.")


def _read_string(prompt: str) -> str:
    while True:
        raw = input(prompt).strip()
        if raw:
            return raw
        print("Ошибка: поле не может быть пустым.")


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


def _add_record() -> None:
    print("\nДобавление записи")
    table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"

    if table_name not in memory.TABLES:
        print(f"Ошибка: таблица '{table_name}' не найдена.")
        return

    schema = memory.SCHEMAS[table_name]
    data: Dict[str, Any] = {}

    print(f"Введите данные для полей таблицы '{table_name}':")
    for field, expected_type in schema.items():
        if expected_type == int:
            data[field] = _read_int(f"{field} (int): ")
        elif expected_type == float:
            while True:
                try:
                    data[field] = float(input(f"{field} (float): ").strip())
                    break
                except ValueError:
                    print("Ошибка: введите число.")
        else:
            data[field] = _read_string(f"{field} (str): ")

    try:
        record = memory.create_record(table_name, **data)
        print(f"Запись добавлена: {record}")
    except ValueError as exc:
        print(f"Ошибка: {exc}")


def _print_records(records: List[Dict[str, Any]]) -> None:
    if not records:
        print("Записи не найдены.")
        return

    # Вывод заголовков таблицы.
    headers = list(records[0].keys())
    print(" | ".join(f"{h:<12}" for h in headers))
    print("-" * (len(headers) * 14))

    # Последовательный вывод записей.
    for record in records:
        values = [str(record.get(h, "")) for h in headers]
        print(" | ".join(f"{v:<12}" for v in values))


def _show_all_records() -> None:
    print("\nСписок записей")
    table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
    if table_name not in memory.TABLES:
        print(f"Ошибка: таблица '{table_name}' не найдена.")
        return
    _print_records(memory.select_record(table_name))


def _find_records_by_filter() -> None:
    print("\nПоиск по фильтру (Enter = пропустить поле)")
    table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
    if table_name not in memory.TABLES:
        print(f"Ошибка: таблица '{table_name}' не найдена.")
        return

    schema = memory.SCHEMAS[table_name]
    filters: Dict[str, Any] = {}

    print(f"Введите значения для фильтрации таблицы '{table_name}':")
    for field, expected_type in schema.items():
        if expected_type == int:
            val = _read_optional_int(f"{field} (int): ")
        elif expected_type == float:
            raw = input(f"{field} (float): ").strip()
            val = float(raw) if raw else None
        else:
            raw = input(f"{field} (str): ").strip()
            val = raw or None

        if val is not None:
            filters[field] = val

    records = memory.select_record(table_name, **filters)
    _print_records(records)


def _update_record() -> None:
    print("\nОбновление записи")
    table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
    if table_name not in memory.TABLES:
        print(f"Ошибка: таблица '{table_name}' не найдена.")
        return

    record_id = _read_int("ID записи: ")
    schema = memory.SCHEMAS[table_name]
    update_data: Dict[str, Any] = {}

    print("Введите новые значения (Enter = не изменять поле):")
    for field, expected_type in schema.items():
        if expected_type == int:
            val = _read_optional_int(f"{field} (int): ")
        elif expected_type == float:
            raw = input(f"{field} (float): ").strip()
            val = float(raw) if raw else None
        else:
            raw = input(f"{field} (str): ").strip()
            val = raw or None

        if val is not None:
            update_data[field] = val

    if not update_data:
        print("Не выбрано полей для обновления.")
        return

    try:
        memory.update_record(table_name, record_id, **update_data)
        print("Запись успешно обновлена.")
    except ValueError as exc:
        print(f"Ошибка: {exc}")


def _delete_record() -> None:
    print("\nУдаление записи")
    table_name = input("Имя таблицы (Enter -> books): ").strip() or "books"
    if table_name not in memory.TABLES:
        print(f"Ошибка: таблица '{table_name}' не найдена.")
        return

    record_id = _read_int("ID записи для удаления: ")
    try:
        memory.delete_record(table_name, record_id)
        print("Запись успешно удалена.")
    except ValueError as exc:
        print(f"Ошибка: {exc}")


def _show_tables() -> None:
    print("\n=== Доступные таблицы ===")
    tables_info = memory.list_tables()

    if not tables_info:
        print("Таблицы отсутствуют.")
        return

    for name, info in tables_info.items():
        schema = info["schema"]
        count = info["record_count"]
        schema_str = ", ".join(f"{field}:{t.__name__}" for field, t in schema.items())
        print(f"- {name} [Схема: {schema_str}, Записей: {count}]")


def _create_new_table() -> None:
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
        schema = _parse_schema_input(schema_raw)
        memory.create_table(table_name, schema)
        print(f"Таблица '{table_name}' успешно создана.")
    except ValueError as exc:
        print(f"Ошибка создания таблицы: {exc}")


def main() -> None:

    while True:
        _print_menu()
        choice = input("Выберите действие: ").strip()

        try:
            if choice == "1":
                _add_record()
            elif choice == "2":
                _show_all_records()
            elif choice == "3":
                _find_records_by_filter()
            elif choice == "4":
                _update_record()
            elif choice == "5":
                _delete_record()
            elif choice == "6":
                _show_tables()
            elif choice == "7":
                _create_new_table()
            elif choice == "0":
                print("Завершение работы.")
                break
            else:
                print("Неверный ввод. Выберите число от 0 до 7.")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота прервана пользователем.")
            sys.exit(0)
        except Exception as exc:
            print(f"Непредвиденная ошибка: {exc}")