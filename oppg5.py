from pathlib import Path
import json
import re

import numpy as np
import pandas as pd


# Oppgave 1: Les filer og hent transaksjoner

def read_log_file(file_path: str | Path) -> tuple[str, str]:
    """Les UTF-8, med Latin-1 som reserve."""
    path = Path(file_path)

    try:
        return path.read_text(encoding="utf-8"), "utf-8"
    except UnicodeDecodeError:
        return path.read_text(encoding="iso-8859-1"), "iso-8859-1"


def parse_log(file_text: str) -> list[dict]:
    """Hent transaksjoner og ignorer støylinjer."""
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


# Oppgave 2: Rekursive funksjoner

def find_log_files(directory: str | Path) -> list[Path]:
    """Finn alle .log-filer med eksplisitt rekursjon."""
    directory = Path(directory)
    log_files = []

    for entry in sorted(directory.iterdir()):
        if entry.is_dir():
            log_files.extend(find_log_files(entry))
        elif entry.is_file() and entry.suffix.lower() == ".log":
            log_files.append(entry)

    return log_files


def get_active_registers(data: object) -> set[str]:
    """Finn aktive kasse-ID-er i nestede ordbøker og lister."""
    active_registers = set()

    if isinstance(data, dict):
        if data.get("active") is True and isinstance(data.get("id"), str):
            active_registers.add(data["id"])

        for value in data.values():
            active_registers.update(get_active_registers(value))

    elif isinstance(data, list):
        for element in data:
            active_registers.update(get_active_registers(element))

    return active_registers


# Oppgave 3: NumPy

def remove_price_outliers(prices) -> np.ndarray:
    """Erstatt verdier utenfor tre standardavvik med medianen."""
    prices = np.asarray(prices, dtype=float).reshape(-1).copy()

    if prices.size == 0:
        return prices

    mean = np.mean(prices)
    standard_deviation = np.std(prices)

    outliers = np.abs(prices - mean) > 3 * standard_deviation
    valid_prices = prices[~outliers]

    if np.any(outliers) and valid_prices.size > 0:
        prices[outliers] = np.median(valid_prices)

    return prices


def compute_refund_ratio(
    sales_count: np.ndarray,
    refund_count: np.ndarray,
) -> np.ndarray:
    """Beregn antall refusjoner delt på antall salg."""
    return refund_count / (sales_count + 1e-6)


# Oppgave 4: Pandas

def create_dataframe(transactions: list[dict]) -> pd.DataFrame:
    """Lag en DataFrame sortert etter tidspunkt."""
    columns = [
        "timestamp",
        "register_id",
        "item",
        "price",
        "currency",
        "status",
    ]

    df = pd.DataFrame(transactions, columns=columns)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df.set_index("timestamp").sort_index()


def calculate_hourly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Summer price per vare i intervaller på én time."""
    hourly = (
        df.groupby("item")
        .resample("1h")["price"]
        .sum()
        .rename("total_revenue")
        .reset_index()
    )

    return hourly


def create_status_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Summer price per vare og status."""
    pivot = df.pivot_table(
        index="item",
        columns="status",
        values="price",
        aggfunc="sum",
        fill_value=0,
    )

    return pivot.reindex(
        columns=["SUCCESS", "REFUND", "CANCELLED"],
        fill_value=0,
    )


def calculate_item_refund_ratios(df: pd.DataFrame) -> pd.DataFrame:
    """Beregn refusjonsandel per vare ved hjelp av NumPy-funksjonen."""
    counts = (
        df.groupby(["item", "status"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["SUCCESS", "REFUND"], fill_value=0)
    )

    sales_count = counts["SUCCESS"].to_numpy(dtype=float)
    refund_count = counts["REFUND"].to_numpy(dtype=float)

    ratios = compute_refund_ratio(sales_count, refund_count)

    return pd.DataFrame(
        {
            "sales_count": counts["SUCCESS"],
            "refund_count": counts["REFUND"],
            "refund_ratio": ratios,
        },
        index=counts.index,
    )


# Oppgave 5: Full arbeidsflyt

def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    output_dir = base_dir / "output"

    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"Fant ikke data-mappen: {data_dir}. "
            "Kjør datageneratoren først."
        )

    # 1. Finn loggfiler og aktive kasse-ID-er.
    log_files = find_log_files(data_dir)

    config_path = data_dir / "store_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    active_registers = get_active_registers(config)

    print(f"Fant {len(log_files)} loggfiler.")
    print(f"Aktive kasser: {', '.join(sorted(active_registers))}")

    # 2. Les og parse filene. Behold transaksjoner fra aktive kasser.
    transactions = []

    for log_file in log_files:
        text, encoding = read_log_file(log_file)
        records = parse_log(text)

        active_records = [
            record
            for record in records
            if record["register_id"] in active_registers
        ]

        transactions.extend(active_records)

        print(
            f"{log_file.relative_to(data_dir)}: "
            f"{len(active_records)} transaksjoner, {encoding}"
        )

    if not transactions:
        print("Fant ingen gyldige transaksjoner fra aktive kasser.")
        return

    # 3. Lag DataFrame.
    df = create_dataframe(transactions)

    # 4. Rens priser før NOK-korreksjonen.
    original_prices = df["price"].to_numpy(dtype=float)
    cleaned_prices = remove_price_outliers(original_prices)

    number_corrected = int(
        np.count_nonzero(original_prices != cleaned_prices)
    )

    df["price"] = cleaned_prices

    # 5. Rett NOK-priser.
    nok_mask = df["currency"] == "NOK"
    df.loc[nok_mask, "price"] = df.loc[nok_mask, "price"] * 10.0

    # Avrund pengebeløp til to desimaler.
    df["price"] = df["price"].round(2)

    # 6. Lag rapportene.
    hourly_revenue = calculate_hourly_revenue(df)
    status_pivot = create_status_pivot(df)
    refund_ratios = calculate_item_refund_ratios(df)

    # 7. Lagre alle de fire påkrevde resultatfilene.
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(
        output_dir / "cleaned_transactions.csv",
        encoding="utf-8",
        index_label="timestamp",
    )

    hourly_revenue.to_json(
        output_dir / "hourly_revenue.json",
        orient="records",
        date_format="iso",
        indent=2,
        force_ascii=False,
    )

    status_pivot.to_csv(
        output_dir / "status_pivot_table.csv",
        encoding="utf-8",
        index_label="item",
    )

    refund_ratios.to_csv(
        output_dir / "item_refund_ratios.csv",
        encoding="utf-8",
        index_label="item",
    )

    print(f"\nAntall transaksjoner totalt: {len(df)}")
    print(f"Antall prisavvik korrigert: {number_corrected}")
    print(f"Antall NOK-priser korrigert: {int(nok_mask.sum())}")

    print("\nPivottabell:")
    print(status_pivot)

    print("\nRefusjonsandel per vare:")
    print(refund_ratios)

    print(f"\nDe fire resultatfilene er lagret i: {output_dir}")


if __name__ == "__main__":
    main()
