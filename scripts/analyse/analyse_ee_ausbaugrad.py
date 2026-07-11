from __future__ import annotations

import datetime as dt

import pandas as pd

from common import INDICATORS_PATH, PROCESSED_DIR, load_boundaries, merge_indicator, write_indicator_table


GEMEINDE_KEY = "ags"
MASTR_PATH = PROCESSED_DIR / "mastr_units_regen.csv"
LEISTUNGSSPALTE = "Nettonennleistung"
BETRIEBSSTATUS_AKTIV = "In Betrieb"


def load_mastr() -> pd.DataFrame:
    units = pd.read_csv(MASTR_PATH, dtype={GEMEINDE_KEY: str})
    stati = set(units["EinheitBetriebsstatus"].unique())
    if stati != {BETRIEBSSTATUS_AKTIV}:
        raise ValueError(f"{MASTR_PATH.name}: erwartet nur '{BETRIEBSSTATUS_AKTIV}', gefunden {sorted(stati)}")

    return units


def installierte_leistung(units: pd.DataFrame) -> pd.Series:
    return units.groupby(GEMEINDE_KEY)[LEISTUNGSSPALTE].sum().rename("ee_leistung_kw")


def compute_ee_ausbaugrad(boundaries) -> pd.DataFrame:
    print("Computing EE-Ausbaugrad (installierte EE-Leistung je Einwohner)...")

    units = load_mastr()
    einwohner = boundaries.set_index(GEMEINDE_KEY)["einwohner"]
    leistung = installierte_leistung(units).reindex(einwohner.index, fill_value=0.0)
    print(f"  {len(units)} Anlagen, {leistung.sum() / 1000:.1f} MW netto in {len(einwohner)} Gemeinden")

    if (einwohner <= 0).any():
        raise ValueError("Einwohnerzahl <= 0 - Normierung nicht moeglich")

    indikator = (leistung / einwohner).rename("ee_ausbaugrad_kw_ew")
    print(f"Median: {indikator.median():.3f} kW/EW, "
          f"Spannweite {indikator.min():.2f}-{indikator.max():.2f} kW/EW")

    indicator_df = pd.DataFrame({
        "ee_leistung_kw": leistung.round(1),
        "ee_ausbaugrad_kw_ew": indikator.round(4),
    })
    indicator_df.index.name = GEMEINDE_KEY
    return indicator_df


def report(indicator_df: pd.DataFrame, boundaries) -> None:
    schau = indicator_df.join(boundaries.set_index(GEMEINDE_KEY)["name"])
    spalten = ["name", "ee_leistung_kw", "ee_ausbaugrad_kw_ew"]
    print("\n  Top 3 / Bottom 3 (kW/EW):")
    print(schau.nlargest(3, "ee_ausbaugrad_kw_ew")[spalten].to_string(index=False))
    print(schau.nsmallest(3, "ee_ausbaugrad_kw_ew")[spalten].to_string(index=False))


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df = compute_ee_ausbaugrad(boundaries)
    report(indicator_df, boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"\nWrote {len(merged)} rows -> {INDICATORS_PATH}")
    print(f"Analysed: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()