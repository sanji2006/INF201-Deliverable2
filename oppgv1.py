from pathlib import Path  # Brukes til å håndtere filstier.
import re                # Brukes til regulære uttrykk.


def read_log_file(file_path: str | Path) -> tuple[str, str]:
    """Returner filens tekst og tegnkodingen som ble brukt."""

    # Gjør filstien om til et Path-objekt.
    path = Path(file_path)

    try:
        # Prøv først å lese filen med UTF-8.
        text = path.read_text(encoding="utf-8")

        # Returner en tuple med teksten og tegnkodingen.
        return text, "utf-8"

    except UnicodeDecodeError:
        # Hvis UTF-8 ikke kan dekode filen, brukes Latin-1.
        text = path.read_text(encoding="iso-8859-1")
        return text, "iso-8859-1"


def parse_log(file_text: str) -> list[dict]:
    """Hent gyldige transaksjoner fra teksten og ignorer støy."""

    # Lag et regulært uttrykk som beskriver en gyldig transaksjon.
    # (?P<navn>...) gir hver gruppe et navn.
    # r foran strengene gjør at backslash behandles bokstavelig.
    pattern = re.compile(
        # Tidspunkt, for eksempel [2026-10-15 08:30:00].
        r"\[(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] "

        # Kasse-ID, for eksempel [POS_01].
        r"\[(?P<register_id>POS_\d+)\] "

        # Varenavn. .+? henter teksten frem til neste del av mønsteret.
        r"item=(?P<item>.+?) "

        # Pris med to desimaler, for eksempel 4.50.
        r"price=(?P<price>\d+\.\d{2}) "

        # Valuta må være EUR, NOK eller USD.
        r"(?P<currency>EUR|NOK|USD) "

        # Status må være SUCCESS, REFUND eller CANCELLED.
        r"\((?P<status>SUCCESS|REFUND|CANCELLED)\)"
    )

    # Her samler vi de gyldige transaksjonene.
    transactions = []

    # Del teksten i linjer og behandle én linje om gangen.
    for line in file_text.splitlines():

        # strip() fjerner mellomrom i starten og slutten.
        # fullmatch() krever at hele linjen passer til mønsteret.
        match = pattern.fullmatch(line.strip())

        # Bare linjer som passer til mønsteret, blir lagt til.
        # Støylinjer blir dermed ignorert.
        if match:
            # Gjør de navngitte gruppene om til en ordbok.
            transaction = match.groupdict()

            # Verdiene er først tekst. Gjør prisen om til et desimaltall.
            transaction["price"] = float(transaction["price"])

            # Legg transaksjonen til i listen.
            transactions.append(transaction)

    return transactions


def main():
    # Finn mappen der denne Python-filen ligger.
    base_dir = Path(__file__).resolve().parent

    # Bygg stien til én av loggfilene.
    # / brukes av Path til å sette sammen mapper og filnavn.
    file_path = (
        base_dir
        / "data"
        / "2026"
        / "library_cafe"
        / "POS_01"
        / "register_sales.log"
    )

    try:
        # Les filen og pakk ut de to returverdiene.
        text, encoding = read_log_file(file_path)

    except FileNotFoundError:
        # Gi en forståelig beskjed dersom filen mangler.
        print(f"Fant ikke filen: {file_path}")
        print("Kjør generate_data_for_d2.py først.")
        return

    except OSError as error:
        # Håndter andre problemer, for eksempel manglende lesetilgang.
        print(f"Kunne ikke lese filen: {error}")
        return

    # Hent transaksjonene fra teksten.
    transactions = parse_log(text)

    # Skriv informasjon om filen og resultatet til terminalen.
    print(f"Fil: {file_path.name}")
    print(f"Tegnkoding brukt: {encoding}")
    print(f"Antall gyldige transaksjoner: {len(transactions)}")

    # [:5] velger de første fem transaksjonene.
    print("\nDe første fem transaksjonene:")
    for transaction in transactions[:5]:
        print(transaction)


# Kjør main() når filen kjøres direkte.
# Ved import fra en annen Python-fil blir main() ikke kjørt automatisk.
if __name__ == "__main__":
    main()
