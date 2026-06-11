from .tui import DatabaseTUI
from .backend.file import JsonDatabase
from .backend.csv import CsvDatabase
from .backend.memory import InMemoryDB


def main() -> None:
    print("=== Выбор формата базы данных ===")
    print("1. JSON (файлы .json)")
    print("2. CSV (файлы .csv + .json для схемы)")
    print("3. In-Memory (временное хранение, без сохранения)")
    print()
    
    choice = input("Выберите формат (1, 2 или 3, Enter -> JSON): ").strip()
    
    if choice == "2":
        print("\n Используется CSV-формат хранения (папка data_csv/)")
        db_instance = CsvDatabase(storage_dir="data_csv")
    elif choice == "3":
        print("\n Используется In-Memory хранилище (данные не сохраняются)")
        db_instance = InMemoryDB()
    else:
        print("\n Используемся JSON-формат хранения (папка data/)")
        db_instance = JsonDatabase(storage_dir="data")
    
    app = DatabaseTUI(db_instance=db_instance)
    app.run()


if __name__ == "__main__":
    main()

