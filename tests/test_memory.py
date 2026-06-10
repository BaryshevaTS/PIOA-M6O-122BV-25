import pytest
from src.db.backend.memory import InMemoryDB
from src.db.backend.errors import (
    TableExistsError,
    TableNotFoundError,
    RecordNotFoundError,
    ValidationError,
)


@pytest.fixture
def db():
    database = InMemoryDB()
    database.create_table("books", {"title": str, "author": str, "year": int, "pages": int})
    return database


def test_create_table_success(db: InMemoryDB) -> None:
    db.create_table("authors", {"name": str, "birth_year": int})
    tables = db.list_tables()
    assert "authors" in tables
    assert tables["authors"]["schema"] == {"name": str, "birth_year": int}
    assert tables["authors"]["record_count"] == 0


def test_create_table_duplicate(db: InMemoryDB) -> None:
    with pytest.raises(TableExistsError, match="уже существует"):
        db.create_table("books", {"title": str})


def test_create_record_valid(db: InMemoryDB) -> None:
    rec = db.create_record("books", title="1984", author="Orwell", year=1949, pages=328)
    assert rec["id"] == 1
    assert rec["title"] == "1984"
    assert isinstance(rec, dict)


def test_create_record_auto_increment(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=100, pages=10)
    db.create_record("books", title="B", author="Auth2", year=200, pages=20)
    rec = db.create_record("books", title="C", author="Auth3", year=300, pages=30)
    assert rec["id"] == 3


def test_create_record_missing_field(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="Отсутствуют обязательные поля"):
        db.create_record("books", title="OnlyTitle")


def test_create_record_extra_field(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="Недопустимые поля"):
        db.create_record("books", title="Test", author="Auth", year=2000, pages=100, isbn="123")


def test_create_record_wrong_type(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="ожидает str"):
        db.create_record("books", title=123, author="Auth", year=2000, pages=100)


def test_create_record_bool_as_int(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="ожидает int"):
        db.create_record("books", title="Book", author="Auth", year=True, pages=10)


def test_create_record_negative_numeric(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="не может быть отрицательным"):
        db.create_record("books", title="Book", author="Auth", year=-50, pages=10)
    with pytest.raises(ValidationError, match="не может быть отрицательным"):
        db.create_record("books", title="Book", author="Auth", year=2000, pages=-1)


def test_create_record_empty_data(db: InMemoryDB) -> None:
    with pytest.raises(ValidationError, match="не могут быть пустыми"):
        db.create_record("books")


def test_create_record_table_not_found(db: InMemoryDB) -> None:
    with pytest.raises(TableNotFoundError, match="не найдена"):
        db.create_record("nonexistent", field="value")


def test_select_all_records(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=100, pages=10)
    db.create_record("books", title="B", author="Auth2", year=200, pages=20)
    records = db.select_record("books")
    assert len(records) == 2
    assert records[0]["id"] == 1
    assert records[1]["id"] == 2


def test_select_with_single_filter(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=100, pages=10)
    db.create_record("books", title="B", author="Auth2", year=200, pages=20)
    records = db.select_record("books", year=100)
    assert len(records) == 1
    assert records[0]["title"] == "A"


def test_select_with_multiple_filters(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=2000, pages=300)
    db.create_record("books", title="B", author="Auth2", year=2000, pages=500)
    records = db.select_record("books", year=2000, pages=500)
    assert len(records) == 1
    assert records[0]["title"] == "B"


def test_select_no_match(db: InMemoryDB) -> None:
    records = db.select_record("books", year=9999)
    assert records == []


def test_select_table_not_found(db: InMemoryDB) -> None:
    with pytest.raises(TableNotFoundError, match="не найдена"):
        db.select_record("nonexistent")


def test_update_record_valid(db: InMemoryDB) -> None:
    db.create_record("books", title="Old", author="Auth", year=1990, pages=300)
    db.update_record("books", 1, title="New")
    recs = db.select_record("books", id=1)
    assert recs[0]["title"] == "New"
    assert recs[0]["year"] == 1990


def test_update_record_partial_fields(db: InMemoryDB) -> None:
    db.create_record("books", title="Book", author="Auth", year=2000, pages=100)
    db.update_record("books", 1, year=2024, pages=150)
    recs = db.select_record("books", id=1)
    assert recs[0] == {"id": 1, "title": "Book", "author": "Auth", "year": 2024, "pages": 150}


def test_update_record_invalid_id(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth", year=100, pages=10)
    with pytest.raises(RecordNotFoundError, match="не найдена"):
        db.update_record("books", 999, title="Fail")


def test_update_record_validation_fail(db: InMemoryDB) -> None:
    db.create_record("books", title="Valid", author="Auth", year=2000, pages=100)
    with pytest.raises(ValidationError, match="ожидает int"):
        db.update_record("books", 1, year="not_int")


def test_update_record_empty_data(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth", year=1, pages=1)
    with pytest.raises(ValidationError, match="Не указаны поля"):
        db.update_record("books", 1)


def test_delete_record_valid(db: InMemoryDB) -> None:
    db.create_record("books", title="ToDel", author="Auth", year=2020, pages=50)
    db.delete_record("books", 1)
    assert len(db.select_record("books")) == 0


def test_list_tables_empty() -> None:
    db = InMemoryDB()
    assert db.list_tables() == {}


def test_list_tables_with_data(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=100, pages=10)
    db.create_record("books", title="B", author="Auth2", year=200, pages=20)
    tables = db.list_tables()
    assert tables["books"]["record_count"] == 2


def test_sort_records_ascending(db: InMemoryDB) -> None:
    db.create_record("books", title="B", author="Auth1", year=200, pages=20)
    db.create_record("books", title="A", author="Auth2", year=100, pages=10)
    sorted_recs = db.sort_records("books", "year", descending=False)
    assert [r["title"] for r in sorted_recs] == ["A", "B"]


def test_sort_records_descending(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth1", year=100, pages=10)
    db.create_record("books", title="B", author="Auth2", year=200, pages=20)
    sorted_recs = db.sort_records("books", "year", descending=True)
    assert [r["title"] for r in sorted_recs] == ["B", "A"]


def test_sort_records_invalid_field(db):
    with pytest.raises(ValidationError, match="не найдено"):
        db.sort_records("books", "nonexistent")


def test_sort_records_table_not_found(db: InMemoryDB) -> None:
    with pytest.raises(TableNotFoundError, match="не найдена"):
        db.sort_records("nonexistent", "year")


def test_sort_records_type_error(db: InMemoryDB) -> None:
    db.create_record("books", title="A", author="Auth", year=100, pages=10)
    db._tables["books"].append({"id": 2, "title": "B", "author": "Auth", "year": "text", "pages": 10})
    with pytest.raises(ValidationError, match="Невозможно отсортировать"):
        db.sort_records("books", "year")


def test_create_record_with_id_in_data(db):
    record = db.create_record("books", title="Test", author="Auth", year=2020, pages=100, id=999)
    assert record["id"] == 1
    assert record["title"] == "Test"


def test_update_record_cannot_change_id(db):
    db.create_record("books", title="Test", author="Auth", year=2020, pages=100)
    db.update_record("books", 1, title="New", id=999)
    record = db.select_record("books", id=1)[0]
    assert record["id"] == 1
    assert record["title"] == "New"

