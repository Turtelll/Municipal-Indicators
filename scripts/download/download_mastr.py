from pathlib import Path

import pandas as pd
from sqlalchemy import text
from open_mastr import Mastr


KREISSCHLUESSEL = "09276"
TECHNOLOGIES = ["solar", "wind", "biomass", "hydro"]

OUTPUT_FILE = Path("data/raw/mastr_units.csv")

COLUMNS = [
    "EinheitMastrNummer",
    "Energietraeger",
    "EinheitBetriebsstatus",
    "Bruttoleistung",
    "Nettonennleistung",
    "Inbetriebnahmedatum",
    "Gemeinde",
    "Gemeindeschluessel",
    "Landkreis",
    "Bundesland",
    "Postleitzahl",
    "Breitengrad",
    "Laengengrad",
    "Lage",
    "ArtDerSolaranlage",
    "Nutzungsbereich",
]


def main():
    db = Mastr()
    db.download(method="bulk", data=TECHNOLOGIES, date="today")

    frames = []

    for tech in TECHNOLOGIES:
        table = f"{tech}_extended"

        sql = text(
            f'SELECT * FROM {table} '
            'WHERE CAST("Gemeindeschluessel" AS TEXT) LIKE :prefix'
        )

        df = pd.read_sql(
            sql,
            con=db.engine,
            params={"prefix": f"{KREISSCHLUESSEL}%"},
        )

        if df.empty:
            continue

        df["technologie"] = tech

        keep = [c for c in COLUMNS if c in df.columns] + ["technologie"]
        frames.append(df[keep])

    if not frames:
        raise RuntimeError("Keine Daten gefunden.")

    units = pd.concat(frames, ignore_index=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    units.to_csv(OUTPUT_FILE, index=False)

    print(f"{len(units)} Einheiten gespeichert.")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()