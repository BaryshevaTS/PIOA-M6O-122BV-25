from .tui import DatabaseTUI

def main() -> None:
    app = DatabaseTUI()
    app.run()

if __name__ == "__main__":
    main()
    