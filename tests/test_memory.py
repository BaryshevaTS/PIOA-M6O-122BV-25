import pytest
from src.db.backend.memory import InMemoryDB


@pytest.fixture
def db():
    database = InMemoryDB()
    database.create_table("books", {"title": str, "author": str, "year": int, "pages": int})
    return database


def test_create_table_success(db):
    db.create_table("authors", {"name": str, "birth_year": int})
    assert "authors" in db.list_tables()


def test_create_table_duplicate(db):
    with pytest.raises(ValueError, match="уже существует"):
        db.create_table("books", {"title": str})


def test_create_record_valid(db):
    record = db.create_record("books", title="1984", author="Orwell", year=1949, pages=328)
    assert record["id"] == 1
    assert record["title"] == "1984"


def test_create_record_auto_increment(db):
    db.create_record("books", title="Book1", author="Author1", year=2000, pages=100)
    db.create_record("books", title="Book2", author="Author2", year=2001, pages=200)
    record2 = db.select_record("books", title="Book2")[0]
    assert record2["id"] == 2


def test_create_record_missing_field(db):
    with pytest.raises(ValueError, match="Отсутствуют обязательные поля"):
        db.create_record("books", title="Incomplete", author="Author")


def test_create_record_extra_field(db):
    with pytest.raises(ValueError, match="Недопустимые поля"):
        db.create_record("books", title="Extra", author="Author", year=2000, pages=100, extra="field")


def test_create_record_wrong_type(db):
    with pytest.raises(ValueError, match="ожидает"):
        db.create_record("books", title="Wrong", author="Author", year="not_int", pages=100)


def test_create_record_bool_as_int(db):
    with pytest.raises(ValueError, match="ожидает int"):
        db.create_record("books", title="Bool", author="Author", year=True, pages=100)


def test_create_record_negative_numeric(db):
    with pytest.raises(ValueError, match="не может быть отрицательным"):
        db.create_record("books", title="Negative", author="Author", year=-100, pages=100)


def test_create_record_empty_data(db):
    with pytest.raises(ValueError, match="не могут быть пустыми"):
        db.create_record("books")


def test_create_record_table_not_found(db):
    with pytest.raises(ValueError, match="не найдена"):
        db.create_record("nonexistent", title="Test")


def test_select_all_records(db):
    db.create_record("books", title="Book1", author="Author1", year=2000, pages=100)
    db.create_record("books", title="Book2", author="Author2", year=2001, pages=200)
    records = db.select_record("books")
    assert len(records) == 2


def test_select_with_single_filter(db):
    db.create_record("books", title="Book1", author="Author1", year=2000, pages=100)
    db.create_record("books", title="Book2", author="Author2", year=2001, pages=200)
    records = db.select_record("books", author="Author1")
    assert len(records) == 1
    assert records[0]["title"] == "Book1"


def test_select_with_multiple_filters(db):
    db.create_record("books", title="Book1", author="Author1", year=2000, pages=100)
    db.create_record("books", title="Book2", author="Author1", year=2001, pages=200)
    records = db.select_record("books", author="Author1", year=2000)
    assert len(records) == 1
    assert records[0]["title"] == "Book1"


def test_select_no_match(db):
    db.create_record("books", title="Book1", author="Author1", year=2000, pages=100)
    records = db.select_record("books", author="NonExistent")
    assert len(records) == 0


def test_select_table_not_found(db):
    with pytest.raises(ValueError, match="не найдена"):
        db.select_record("nonexistent")


def test_update_record_valid(db):
    db.create_record("books", title="Old", author="Author", year=2000, pages=100)
    db.update_record("books", 1, title="New")
    record = db.select_record("books", id=1)[0]
    assert record["title"] == "New"
    assert record["year"] == 2000


def test_update_record_partial_fields(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    db.update_record("books", 1, year=2020, pages=200)
    record = db.select_record("books", id=1)[0]
    assert record["year"] == 2020
    assert record["pages"] == 200
    assert record["title"] == "Book"


def test_update_record_invalid_id(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    with pytest.raises(ValueError, match="не найдена"):
        db.update_record("books", 999, title="New")


def test_update_record_validation_fail(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    with pytest.raises(ValueError, match="не может быть отрицательным"):
        db.update_record("books", 1, year=-100)


def test_update_record_empty_data(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    with pytest.raises(ValueError, match="Не указаны поля"):
        db.update_record("books", 1)


def test_delete_record_valid(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    db.delete_record("books", 1)
    assert len(db.select_record("books")) == 0


def test_delete_record_invalid_id(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    with pytest.raises(ValueError, match="не найдена"):
        db.delete_record("books", 999)


def test_list_tables_empty():
    db = InMemoryDB()
    assert db.list_tables() == {}


def test_list_tables_with_data(db):
    db.create_table("authors", {"name": str})
    tables = db.list_tables()
    assert "books" in tables
    assert "authors" in tables
    assert tables["books"]["record_count"] == 0


def test_sort_records_ascending(db):
    db.create_record("books", title="B", author="Author", year=2001, pages=100)
    db.create_record("books", title="A", author="Author", year=2000, pages=200)
    sorted_records = db.sort_records("books", "year", descending=False)
    assert sorted_records[0]["title"] == "A"
    assert sorted_records[1]["title"] == "B"


def test_sort_records_descending(db):
    db.create_record("books", title="B", author="Author", year=2001, pages=100)
    db.create_record("books", title="A", author="Author", year=2000, pages=200)
    sorted_records = db.sort_records("books", "year", descending=True)
    assert sorted_records[0]["title"] == "B"
    assert sorted_records[1]["title"] == "A"


def test_sort_records_invalid_field(db):
    with pytest.raises(ValueError, match="не найдено"):
        db.sort_records("books", "nonexistent")


def test_sort_records_table_not_found(db):
    with pytest.raises(ValueError, match="не найдена"):
        db.sort_records("nonexistent", "year")


def test_sort_records_type_error(db):
    db.create_record("books", title="Book", author="Author", year=2000, pages=100)
    sorted_records = db.sort_records("books", "title")
    assert len(sorted_records) == 1
    