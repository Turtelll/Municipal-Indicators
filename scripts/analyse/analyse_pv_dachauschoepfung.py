from __future__ import annotations

import datetime as dt

import pandas as pd

from common import INDICATORS_PATH, PROCESSED_DIR, load_boundaries, merge_indicator, write_indicator_table


GEMEINDE_KEY = "ags"
MASTR_PATH = PROCESSED_DIR / "mastr_units_regen.csv"
POTENZIAL_PATH = PROCESSED_DIR / "pv_dachpotenzial_regen.csv"
LEISTUNGSSPALTE = "Nettonennleistung"
DACH_KATEGORIE = "Gebäudesolaranlage"
ZIELWERT_PROZENT = 100.0


def dach_pv_leistung() -> pd.Series:
    units = pd.read_csv(MASTR_PATH, dtype={GEMEINDE_KEY: str})
    solar = units[units["technologie"] == "solar"]
    dach = solar[solar["ArtDerSolaranlage"] == DACH_KATEGORIE]

    print(f"  Zaehler: {len(dach)} Gebaeudesolaranlagen "
          f"(ausgeschlossen: {len(solar) - len(dach)} Freiflaeche/Balkon/Sonstige)")
    return dach.groupby(GEMEINDE_KEY)[LEISTUNGSSPALTE].sum().rename("pv_dach_installiert_kw")


def dach_potenzial() -> pd.DataFrame:
    atlas = pd.read_csv(POTENZIAL_PATH, dtype={GEMEINDE_KEY: str}).set_index(GEMEINDE_KEY)
    print(f"  Nenner: Energie-Atlas Bayern, Datenstand {atlas['datenstand'].iloc[0]}, "
          f"{atlas['pv_potenzial_leistung_kw'].sum() / 1000:.0f} MWp Dachpotenzial")
    return atlas


def validiere_gegen_energieatlas(indicator_df: pd.DataFrame, atlas: pd.DataFrame) -> None:
    eigen = indicator_df["pv_dach_ausschoepfung_prozent"]
    referenz = atlas["pv_ausbaugrad_ea_prozent"].reindex(eigen.index)
    delta = eigen - referenz
    korrelation = eigen.corr(referenz)

    print("\nValidierung gegen Energie-Atlas (pv_ausbaugrad_ea_prozent):")
    print(f"Korrelation: r = {korrelation:.3f}")
    print(f"Mittlere Abweichung:{delta.mean():+.2f} Prozentpunkte")
    print(f"Spannweite: {delta.min():+.2f} bis {delta.max():+.2f} pp")
    print("(eigener Zaehler ist aktueller; Potenzial im Atlas auf ganze MWp gerundet)")

    if abs(delta.mean()) > 5 or korrelation < 0.9:
        print("WARNING: starke Abweichung - Dach-Filter oder Einheiten pruefen")


def compute_pv_dachausschoepfung(boundaries) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("Computing Ausschoepfungsgrad des PV-Dachflaechenpotenzials "
          "(installierte Dach-PV / Dachpotenzial)...")

    installiert = dach_pv_leistung()
    atlas = dach_potenzial()

    index = boundaries[GEMEINDE_KEY]
    installiert = installiert.reindex(index, fill_value=0.0)
    potenzial = atlas["pv_potenzial_leistung_kw"].reindex(index)

    if potenzial.isna().any() or (potenzial <= 0).any():
        raise ValueError("Dachpotenzial fehlt oder ist <= 0 - Quotient nicht definiert")

    ausschoepfung = (ZIELWERT_PROZENT * installiert / potenzial).rename("pv_dach_ausschoepfung_prozent")

    if (ausschoepfung > ZIELWERT_PROZENT).any():
        n = int((ausschoepfung > ZIELWERT_PROZENT).sum())
        print(f"  WARNING: {n} Gemeinde(n) ueber 100 % - Zaehler/Nenner-Scope pruefen")

    perzentil = ausschoepfung.rank(pct=True) * 100
    restpotenzial = (potenzial - installiert).clip(lower=0)

    indicator_df = pd.DataFrame({
        "pv_dach_installiert_kw": installiert.round(1),
        "pv_dach_potenzial_kw": potenzial.round(0),
        "pv_dach_restpotenzial_kw": restpotenzial.round(0),
        "pv_dach_ausschoepfung_prozent": ausschoepfung.round(2),
        "pv_dach_ausschoepfung_perzentil": perzentil.round(1),
    })
    indicator_df.index.name = GEMEINDE_KEY
    return indicator_df, atlas


def report(indicator_df: pd.DataFrame, boundaries) -> None:
    schau = indicator_df.join(boundaries.set_index(GEMEINDE_KEY)["name"])
    spalten = ["name", "pv_dach_installiert_kw", "pv_dach_potenzial_kw", "pv_dach_ausschoepfung_prozent"]

    werte = indicator_df["pv_dach_ausschoepfung_prozent"]
    print(f"\nAusschoepfung: Median {werte.median():.1f} %, "
          f"Spannweite {werte.min():.1f}-{werte.max():.1f} %")
    print("\nTop 3 / Bottom 3:")
    print(schau.nlargest(3, "pv_dach_ausschoepfung_prozent")[spalten].to_string(index=False))
    print(schau.nsmallest(3, "pv_dach_ausschoepfung_prozent")[spalten].to_string(index=False))


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df, atlas = compute_pv_dachausschoepfung(boundaries)
    validiere_gegen_energieatlas(indicator_df, atlas)
    report(indicator_df, boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"\nWrote {len(merged)} rows -> {INDICATORS_PATH}")
    print(f"Analysed: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()