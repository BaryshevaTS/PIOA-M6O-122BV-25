import pytest
from pathlib import Path
from src.db.backend.file import JsonDatabase
from src.db.backend.csv import CsvDatabase
from src.db.backend.indexed import IndexedDatabaseMixin
from src.db.backend.errors import TableNotFoundError


@pytest.fixture
def json_db(tmp_path: Path) -> JsonDatabase:
    return JsonDatabase(storage_dir=str(tmp_path))


@pytest.fixture
def csv_db(tmp_path: Path) -> CsvDatabase:
    return CsvDatabase(storage_dir=str(tmp_path))


def test_indexed_mixin_inheritance(json_db: JsonDatabase) -> None:
    assert isinstance(json_db, IndexedDatabaseMixin)
    assert hasattr(json_db, "create_index")
    assert hasattr(json_db, "_update_index_on_create")


def test_mixin_init_and_indexes_structure(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    assert hasattr(json_db, "_indexes")
    assert json_db._indexes == {}


def test_create_and_drop_index(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    
    assert json_db.create_index("books", "year") is True
    assert "year" in json_db._indexes["books"]
    
    assert json_db.drop_index("books", "year") is True
    assert "year" not in json_db._indexes["books"]


def test_create_duplicate_index(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    assert json_db.create_index("books", "year") is False


def test_index_on_nonexistent_table(json_db: JsonDatabase) -> None:
    with pytest.raises(TableNotFoundError, match="не найдена"):
        json_db.create_index("ghost", "id")


def test_index_speeds_up_search(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    
    for i in range(10):
        json_db.create_record("books", title=f"B{i}", year=2000 + (i % 3))
    
    results = json_db.select_record("books", year=2001)
    assert len(results) == 3
    assert 2001 in json_db._indexes["books"]["year"]


def test_index_update_on_create(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    
    json_db.create_record("books", title="New", year=2024)
    assert 2024 in json_db._indexes["books"]["year"]
    assert json_db._indexes["books"]["year"][2024] == {1}


def test_index_update_on_update(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    
    json_db.create_record("books", title="Old", year=2000)
    json_db.update_record("books", 1, year=2024)
    
    assert 2000 not in json_db._indexes["books"]["year"]
    assert 2024 in json_db._indexes["books"]["year"]


def test_index_update_on_delete(json_db: JsonDatabase) -> None:
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    
    json_db.create_record("books", title="Del", year=2000)
    json_db.delete_record("books", 1)
    
    assert 2000 not in json_db._indexes["books"]["year"]


def test_csv_index_integration(csv_db: CsvDatabase) -> None:
    csv_db.create_table("books", {"title": str, "year": int})
    csv_db.create_index("books", "year")
    
    csv_db.create_record("books", title="A", year=2000)
    csv_db.create_record("books", title="B", year=2000)
    
    results = csv_db.select_record("books", year=2000)
    assert len(results) == 2
    assert isinstance(csv_db, IndexedDatabaseMixin)


def test_csv_index_on_update(csv_db: CsvDatabase) -> None:
    csv_db.create_table("books", {"title": str, "year": int})
    csv_db.create_index("books", "year")
    
    csv_db.create_record("books", title="Book", year=2000)
    csv_db.update_record("books", 1, year=2024)
    
    assert len(csv_db.select_record("books", year=2000)) == 0
    assert len(csv_db.select_record("books", year=2024)) == 1


def test_drop_non_existent_index(json_db: JsonDatabase):
    json_db.create_table("books", {"title": str})
    result = json_db.drop_index("books", "year")
    assert result is False


def test_index_persistence_after_reload(json_db: JsonDatabase, tmp_path: Path):
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")
    json_db.create_record("books", title="A", year=2000)

    db2 = JsonDatabase(storage_dir=str(tmp_path))

    results = db2.select_record("books", year=2000)
    assert len(results) == 1
    
    assert "year" in db2._indexes.get("books", {})


def test_index_restore_on_invalid_field(json_db: JsonDatabase, tmp_path: Path):
    json_db.create_table("books", {"title": str, "year": int})
    json_db.create_index("books", "year")

    json_db._cache["books"]["indexed_fields"].append("author")
    json_db._save_table("books")

    db2 = JsonDatabase(storage_dir=str(tmp_path))
    assert "books" in db2._cache
