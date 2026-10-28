from pathlib import Path
import re


def read_log_file(file_path: str | Path) -> tuple[str, str]:
    """Les filen med UTF-8 eller Latin-1 og returner tekst og tegnkoding."""
    path = Path(file_path)

    try:
        text = path.read_text(encoding="utf-8")
        return text, "utf-8"

    except UnicodeDecodeError:
        text = path.read_text(encoding="iso-8859-1")
        return text, "iso-8859-1"


def parse_log(file_text: str) -> list[dict]:
    """Returner gyldige transaksjoner som en liste med ordbøker."""
    pattern = re.compile(
        r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] "
        r"\[(?P<register_id>POS_\d+)\] "
        r"item=(?P<item>.+?) "
        r"price=(?P<price>\d+\.\d{2}) "
        r"(?P<currency>EUR|NOK|USD) "
        r"\((?P<status>SUCCESS|REFUND|CANCELLED)\)"
    )

    transactions = []

    for line in file_text.splitlines():
        match = pattern.fullmatch(line.strip())

        if match:
            transaction = match.groupdict()
            transaction["price"] = float(transaction["price"])
            transactions.append(transaction)

    return transactions


def main():
    # Stien regnes fra mappen der denne Python-filen ligger.
    base_dir = Path(__file__).resolve().parent
    file_path = (
        base_dir
        / "data"
        / "2026"
        / "library_cafe"
        / "POS_01"
        / "register_sales.log"
    )

    try:
        text, encoding = read_log_file(file_path)
    except FileNotFoundError:
        print(f"Fant ikke filen: {file_path}")
        print("Kjør generate_data_for_d2.py først med BASE_DIR = Path('data').")
        return
    except OSError as error:
        print(f"Kunne ikke lese filen: {error}")
        return

    transactions = parse_log(text)

    print(f"Fil: {file_path.name}")
    print(f"Tegnkoding brukt: {encoding}")
    print(f"Antall gyldige transaksjoner: {len(transactions)}")

    print("\nDe første fem transaksjonene:")
    for transaction in transactions[:5]:
        print(transaction)


if __name__ == "__main__":
    main()
