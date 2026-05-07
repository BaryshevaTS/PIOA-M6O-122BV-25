import pytest
from src.db.backend.memory import InMemoryDB
from src.db.tui import DatabaseTUI


@pytest.fixture
def tui():
    app = DatabaseTUI()
    app.db = InMemoryDB()
    app.db.create_table("books", {"title": str, "year": int})
    return app


def test_read_int_valid(monkeypatch, tui):
    monkeypatch.setattr("builtins.input", lambda _: "42")
    assert tui._read_int("Введите: ") == 42


def test_read_int_invalid_then_valid(monkeypatch, tui, capsys):
    inputs = iter(["abc", "10"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_int("Введите: ") == 10
    captured = capsys.readouterr()
    assert "Ошибка: введите целое число." in captured.out


def test_read_optional_int_empty(monkeypatch, tui):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert tui._read_optional_int("Введите: ") is None


def test_read_string_valid(monkeypatch, tui):
    monkeypatch.setattr("builtins.input", lambda _: "Test")
    assert tui._read_string("Введите: ") == "Test"


def test_parse_schema_input_valid(tui):
    schema = tui._parse_schema_input("name:str, age:int")
    assert schema == {"name": str, "age": int}


def test_parse_schema_input_invalid(tui):
    with pytest.raises(ValueError, match="Ожидался формат"):
        tui._parse_schema_input("name str")


def test_has_table_method():
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    assert db.has_table("books") is True
    assert db.has_table("nonexistent") is False


def test_get_schema_method():
    db = InMemoryDB()
    db.create_table("books", {"title": str, "year": int})
    schema = db.get_schema("books")
    assert "title" in schema
    assert schema["title"] is str


def test_add_record_via_tui(monkeypatch, tui):
    inputs = iter(["books", "1984", "1949"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._add_record()
    records = tui.db.select_record("books", title="1984")
    assert len(records) == 1
    assert records[0]["year"] == 1949


def test_show_all_records(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="Test", year=2020)
    monkeypatch.setattr("builtins.input", lambda _: "books")
    tui._show_all_records()
    captured = capsys.readouterr()
    assert "Test" in captured.out


def test_update_record_via_tui(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="Old", year=1990)
    inputs = iter(["books", "1", "New", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._update_record()
    record = tui.db.select_record("books", id=1)[0]
    assert record["title"] == "New"
    captured = capsys.readouterr()
    assert "успешно обновлена" in captured.out


def test_delete_record_via_tui(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="Del", year=2000)
    inputs = iter(["books", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._delete_record()
    assert tui.db.select_record("books") == []
    captured = capsys.readouterr()
    assert "успешно удалена" in captured.out


def test_create_new_table(monkeypatch, tui, capsys):
    inputs = iter(["users", "name:str, age:int"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._create_new_table()
    assert tui.db.has_table("users")
    captured = capsys.readouterr()
    assert "успешно создана" in captured.out


def test_sort_records_view(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="B", year=2000)
    tui.db.create_record("books", title="A", year=1990)
    inputs = iter(["books", "year", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._sort_records_view()
    captured = capsys.readouterr()
    assert "B" in captured.out or "A" in captured.out


def test_read_int_multiple_errors(monkeypatch, tui):
    inputs = iter(["abc", "12.5", "42"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_int("Введите: ") == 42


def test_read_float_error_then_valid(monkeypatch, tui):
    inputs = iter(["not_float", "3.14"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_float("Введите: ") == 3.14


def test_read_optional_int_error_then_valid(monkeypatch, tui):
    inputs = iter(["abc", "100"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_optional_int("Введите: ") == 100


def test_read_optional_float_error_then_valid(monkeypatch, tui):
    inputs = iter(["xyz", "9.9"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_optional_float("Введите: ") == 9.9


def test_read_string_multiple_empty(monkeypatch, tui):
    inputs = iter(["", "", "Final"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    assert tui._read_string("Введите: ") == "Final"


def test_parse_schema_multiple_fields(monkeypatch, tui):
    schema = tui._parse_schema_input(" name : str , age : int , score : float ")
    assert schema == {"name": str, "age": int, "score": float}


def test_tui_run_invalid_choice_then_exit(monkeypatch, tui, capsys):
    inputs = iter(["99", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    with pytest.raises(SystemExit):
        tui.run()
    captured = capsys.readouterr()
    assert "Неверный ввод" in captured.out


def test_tui_method_errors_nonexistent_table(monkeypatch, tui, capsys):
    tui.db.has_table = lambda name: False
    for method_name in ["_add_record", "_show_all_records", "_find_records_by_filter",
                        "_update_record", "_delete_record", "_sort_records_view"]:
        method = getattr(tui, method_name)
        inputs = iter(["nonexistent"] + [""] * 5)
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        method()
    captured = capsys.readouterr()
    assert captured.out.count("не найдена") == 6


def test_tui_sort_invalid_field(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="Test", year=2020)
    inputs = iter(["books", "invalid_field", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._sort_records_view()
    captured = capsys.readouterr()
    assert "не найдено в схеме" in captured.out


def test_tui_create_table_empty_inputs(monkeypatch, tui, capsys):
    inputs = iter(["", "valid_name", "name:str"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._create_new_table()
    inputs = iter(["users", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._create_new_table()
    captured = capsys.readouterr()
    assert captured.out.count("не может быть пуст") >= 2


def test_tui_update_no_fields_selected(monkeypatch, tui, capsys):
    tui.db.create_record("books", title="Old", year=1990)
    inputs = iter(["books", "1", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._update_record()
    captured = capsys.readouterr()
    assert "Не выбрано полей" in captured.out


def test_memory_create_record_empty(monkeypatch):
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    with pytest.raises(ValueError, match="не могут быть пустыми"):
        db.create_record("books")


def test_memory_update_record_empty(monkeypatch):
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    db.create_record("books", title="Test")
    with pytest.raises(ValueError, match="Не указаны поля"):
        db.update_record("books", 1)


def test_memory_delete_record_not_found(monkeypatch):
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    db.create_record("books", title="Test")
    with pytest.raises(ValueError, match="не найдена"):
        db.delete_record("books", 999)


def test_tui_show_tables_empty(monkeypatch, tui, capsys):
    tui.db = InMemoryDB()
    monkeypatch.setattr("builtins.input", lambda _: "6")
    tui._show_tables()
    captured = capsys.readouterr()
    assert "Таблицы отсутствуют." in captured.out


def test_tui_create_table_invalid_schema_format(monkeypatch, tui, capsys):
    inputs = iter(["users", "bad_format"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._create_new_table()
    captured = capsys.readouterr()
    assert "Ожидался формат" in captured.out


def test_tui_create_table_unsupported_type(monkeypatch, tui, capsys):
    inputs = iter(["users", "age:bool"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._create_new_table()
    captured = capsys.readouterr()
    assert "Неподдерживаемый тип" in captured.out


def test_tui_sort_empty_field(monkeypatch, tui, capsys):
    inputs = iter(["books", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    tui._sort_records_view()
    captured = capsys.readouterr()
    assert "поле не может быть пустым" in captured.out


def test_memory_create_record_empty_strict():
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    with pytest.raises(ValueError, match="не могут быть пустыми"):
        db.create_record("books")


def test_memory_update_record_empty_strict():
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    db.create_record("books", title="Test")
    with pytest.raises(ValueError, match="Не указаны поля"):
        db.update_record("books", 1)


def test_memory_delete_not_found_strict():
    db = InMemoryDB()
    db.create_table("books", {"title": str})
    db.create_record("books", title="Test")
    with pytest.raises(ValueError, match="не найдена"):
        db.delete_record("books", 999)
        