import pytest
from pathlib import Path
from src.db.backend.file import JsonDatabase
from src.db.backend.errors import TableExistsError, FileStorageError


@pytest.fixture
def db(tmp_path: Path) -> JsonDatabase:
    return JsonDatabase(storage_dir=str(tmp_path))


def test_create_and_load_persistence(db: JsonDatabase, tmp_path: Path) -> None:
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="1984", year=1949)

    assert (tmp_path / "books.json").exists()

    db2 = JsonDatabase(storage_dir=str(tmp_path))
    assert db2.select_record("books", year=1949)[0]["title"] == "1984"


def test_create_table_duplicate(db: JsonDatabase) -> None:
    db.create_table("authors", {"name": str})
    with pytest.raises(TableExistsError, match="уже существует"):
        db.create_table("authors", {"name": str})


def test_create_record_valid(db: JsonDatabase) -> None:
    db.create_table("books", {"title": str, "pages": int})
    rec = db.create_record("books", title="Dune", pages=688)
    assert rec["id"] == 1
    assert rec["title"] == "Dune"


def test_update_and_persist(db: JsonDatabase, tmp_path: Path) -> None:
    db.create_table("books", {"title": str})
    db.create_record("books", title="Old")
    db.update_record("books", 1, title="New")

    db2 = JsonDatabase(storage_dir=str(tmp_path))
    assert db2.select_record("books", id=1)[0]["title"] == "New"


def test_delete_record(db: JsonDatabase) -> None:
    db.create_table("books", {"title": str})
    db.create_record("books", title="Del")
    db.delete_record("books", 1)
    assert db.select_record("books") == []


def test_corrupted_file_handling(tmp_path: Path):
    json_file = tmp_path / "bad_table.json"
    json_file.write_text("{ invalid json content")
    with pytest.raises(FileStorageError):
        JsonDatabase(storage_dir=str(tmp_path))


def test_sort_records(db: JsonDatabase) -> None:
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="B", year=200)
    db.create_record("books", title="A", year=100)
    sorted_desc = db.sort_records("books", "year", descending=True)
    assert [r["title"] for r in sorted_desc] == ["B", "A"]


def test_select_with_filters(db: JsonDatabase) -> None:
    db.create_table("books", {"title": str, "year": int})
    db.create_record("books", title="A", year=100)
    db.create_record("books", title="B", year=200)
    result = db.select_record("books", year=100)
    assert len(result) == 1
    assert result[0]["title"] == "A"


def test_json_invalid_structure(db: JsonDatabase, tmp_path: Path):
    json_path = tmp_path / "bad_table.json"
    json_path.write_text('{"schema": {}, "id_counter": 1}', encoding="utf-8")
    
    from src.db.backend.errors import FileStorageError
    with pytest.raises(FileStorageError, match="отсутствуют обязательные поля"):
        JsonDatabase(storage_dir=str(tmp_path))


def test_json_invalid_schema_type(db: JsonDatabase, tmp_path: Path):
    json_path = tmp_path / "bad_table.json"
    json_path.write_text('{"schema": [], "records": [], "id_counter": 1}', encoding="utf-8")
    
    from src.db.backend.errors import FileStorageError
    with pytest.raises(FileStorageError, match="поле 'schema' должно быть объектом"):
        JsonDatabase(storage_dir=str(tmp_path))
