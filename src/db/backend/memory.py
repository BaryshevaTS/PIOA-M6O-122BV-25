from typing import Any, Dict, List

Record = Dict[str, Any]
Schema = Dict[str, type]

# Реестр таблиц: ключ - имя таблицы, значение - список записей.
TABLES: Dict[str, List[Record]] = {}

# Реестр схем таблиц: хранит определение структуры и типов полей.
SCHEMAS: Dict[str, Schema] = {}

# Счётчики уникальных идентификаторов для каждой таблицы.
ID_COUNTERS: Dict[str, int] = {}


def create_table(table_name: str, schema: Schema) -> None:
    if table_name in TABLES:
        raise ValueError(f"Таблица '{table_name}' уже существует.")

    TABLES[table_name] = []
    SCHEMAS[table_name] = schema.copy()
    ID_COUNTERS[table_name] = 1


def list_tables() -> Dict[str, Dict[str, Any]]:
    result = {}
    for name in TABLES:
        result[name] = {
            "schema": SCHEMAS[name],
            "record_count": len(TABLES[name])
        }
    return result


def _validate_record(table_name: str, data: Dict[str, Any]) -> None:
    schema = SCHEMAS[table_name]

    # Проверка наличия всех обязательных полей.
    missing_fields = [field for field in schema if field not in data]
    if missing_fields:
        raise ValueError(f"Отсутствуют обязательные поля: {', '.join(missing_fields)}")

    # Проверка соответствия типов данных.
    for field, expected_type in schema.items():
        value = data[field]
        if not isinstance(value, expected_type):
            raise ValueError(
                f"Поле '{field}' ожидает тип {expected_type.__name__}, "
                f"получено {type(value).__name__}."
            )

    # Проверка логической корректности числовых полей.
    # Значения, обозначающие год, возраст или количество, не могут быть отрицательными.
    for field in ("year", "age", "pages", "price", "quantity"):
        if field in data and isinstance(data[field], (int, float)) and data[field] < 0:
            raise ValueError(f"Поле '{field}' не может быть отрицательным.")


def create_record(table_name: str, **data: Any) -> Record:
    if table_name not in TABLES:
        raise ValueError(f"Таблица '{table_name}' не найдена. Сначала создайте её.")

    if not data:
        raise ValueError("Данные записи не могут быть пустыми.")

    _validate_record(table_name, data)

    # Генерация уникального идентификатора.
    record_id = ID_COUNTERS[table_name]

    # Формирование новой записи с автоматическим добавлением id.
    # Словари сохраняют порядок вставки, поэтому id будет первым полем.
    new_record: Record = {"id": record_id, **data}

    # Добавление записи в таблицу.
    TABLES[table_name].append(new_record)
    ID_COUNTERS[table_name] += 1

    # Возврат копии записи для предотвращения изменения внутреннего состояния.
    return new_record.copy()


def select_record(table_name: str, **filters: Any) -> List[Record]:
    if table_name not in TABLES:
        raise ValueError(f"Таблица '{table_name}' не найдена.")

    # Проверка отсутствия всех фильтров.
    # В этом случае возвращается копия списка записей.
    if not filters:
        return [record.copy() for record in TABLES[table_name]]

    # Формирование результирующего списка.
    result: List[Record] = []

    # Итерация по всем записям таблицы.
    for record in TABLES[table_name]:
        # Проверка соответствия каждому фильтру.
        match = True
        for key, value in filters.items():
            if record.get(key) != value:
                match = False
                break

        # Если запись удовлетворяет всем заданным условиям,
        # она добавляется в результирующий список.
        if match:
            result.append(record.copy())

    return result


def update_record(table_name: str, record_id: int, **data: Any) -> None:
    if table_name not in TABLES:
        raise ValueError(f"Таблица '{table_name}' не найдена.")

    if not data:
        raise ValueError("Не указаны поля для обновления.")

    # Поиск целевой записи.
    current_record = None
    for record in TABLES[table_name]:
        if record["id"] == record_id:
            current_record = record
            break

    if current_record is None:
        raise ValueError(f"Запись с id={record_id} не найдена.")

    # Для обновления проверяем только переданные поля.
    # Создаём временную запись для валидации без изменения оригинала.
    temp_data = {**current_record, **data}
    _validate_record(table_name, temp_data)

    # Применение обновлений.
    current_record.update(data)


def delete_record(table_name: str, record_id: int) -> None:
    if table_name not in TABLES:
        raise ValueError(f"Таблица '{table_name}' не найдена.")

    for index, record in enumerate(TABLES[table_name]):
        if record["id"] == record_id:
            del TABLES[table_name][index]
            return

    raise ValueError(f"Запись с id={record_id} не найдена.")