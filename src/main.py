# src/main.py

from pathlib import Path

if __package__:
    from .clean_cases import CleanCases
else:
    from clean_cases import CleanCases


def clean_cases(data_dict: dict | None = None, base_dir: Path | str | None = None) -> CleanCases:
    """Create the Cases cleaner and run its data-cleaning pipeline."""
    cleaner = CleanCases(data_dict=data_dict, base_dir=base_dir)
    cleaner.clean()
    return cleaner


def main():
    cleaner = clean_cases()
    # Imprime os primeros dados das tabelas contidas no objeto cleaner
    print (cleaner.data_dict)

if __name__ == "__main__":
    main()