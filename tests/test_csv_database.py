import pytest
from pathlib import Path
from src.db.backend.csv import CsvDatabase
from src.db.backend.errors import TableExistsError


@pytest.fixture
def db(tmp_path: Path) -> CsvDatabase:
    return CsvDatabase(storage_dir=str(tmp_path))


def test_create_and_load_persistence(db: CsvDatabase, tmp_path: Path) -> None:
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="1984", year=1949)

    assert (tmp_path / "books.csv").exists()
    assert (tmp_path / "books_schema.json").exists()

    db2 = CsvDatabase(storage_dir=str(tmp_path))
    records = db2.select_record("books", year=1949)
    
    assert len(records) == 1
    assert records[0]["title"] == "1984"
    assert records[0]["year"] == 1949  


def test_create_table_duplicate(db: CsvDatabase) -> None:
    db.create_table("authors", {"name": str})
    with pytest.raises(TableExistsError, match="уже существует"):
        db.create_table("authors", {"name": str})


def test_create_record_valid(db: CsvDatabase) -> None:
    db.create_table("books", {"title": str, "pages": int})
    rec = db.create_record("books", title="Dune", pages=688)
    assert rec["id"] == 1
    assert rec["title"] == "Dune"


def test_update_and_persist(db: CsvDatabase, tmp_path: Path) -> None:
    db.create_table("books", {"title": str})
    db.create_record("books", title="Old")
    db.update_record("books", 1, title="New")

    db2 = CsvDatabase(storage_dir=str(tmp_path))
    assert db2.select_record("books", id=1)[0]["title"] == "New"


def test_delete_record(db: CsvDatabase) -> None:
    db.create_table("books", {"title": str})
    db.create_record("books", title="Del")
    db.delete_record("books", 1)
    assert db.select_record("books") == []


def test_sort_records(db: CsvDatabase) -> None:
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="B", year=200)
    db.create_record("books", title="A", year=100)
    
    sorted_desc = db.sort_records("books", "year", descending=True)
    assert [r["title"] for r in sorted_desc] == ["B", "A"]


def test_csv_file_format(db: CsvDatabase, tmp_path: Path) -> None:
    db.create_table("students", {"name": str, "age": int, "gpa": float})
    db.create_record("students", name="Иван", age=20, gpa=4.5)
    
    csv_content = (tmp_path / "students.csv").read_text(encoding="utf-8")
    assert "id,name,age,gpa" in csv_content
    assert "Иван" in csv_content

def test_select_with_filters(db: CsvDatabase):
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="A", year=2000)
    db.create_record("books", title="B", year=2001)
    records = db.select_record("books", year=2000)
    assert len(records) == 1
    assert records[0]["title"] == "A"


def test_csv_corrupted_int_value(db: CsvDatabase, tmp_path: Path):
    db.create_table("books", {"title": str, "year": int})

    csv_path = tmp_path / "books.csv"
    csv_path.write_text("id,title,year\n1,Test,not_a_number\n", encoding="utf-8")
    
    from src.db.backend.errors import FileStorageError
    with pytest.raises(FileStorageError, match="некорректное int значение"):
        CsvDatabase(storage_dir=str(tmp_path))


def test_csv_empty_int_value(db: CsvDatabase, tmp_path: Path):
    db.create_table("books", {"title": str, "year": int})

    csv_path = tmp_path / "books.csv"
    csv_path.write_text("id,title,year\n1,Test,\n", encoding="utf-8")
    
    from src.db.backend.errors import FileStorageError
    with pytest.raises(FileStorageError, match="пустое значение для int"):
        CsvDatabase(storage_dir=str(tmp_path))


def test_csv_invalid_id_counter(db: CsvDatabase, tmp_path: Path):
    db.create_table("books", {"title": str, "year": int})
    
    schema_path = tmp_path / "books_schema.json"
    import json
    meta = json.loads(schema_path.read_text(encoding="utf-8"))
    meta["id_counter"] = "invalid"
    schema_path.write_text(json.dumps(meta), encoding="utf-8")
    
    from src.db.backend.errors import FileStorageError
    with pytest.raises(FileStorageError, match="Некорректный id_counter"):
        CsvDatabase(storage_dir=str(tmp_path))
