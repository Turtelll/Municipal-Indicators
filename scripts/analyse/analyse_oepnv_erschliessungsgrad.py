from __future__ import annotations

import datetime as dt

import geopandas as gpd
import pandas as pd

from common import INDICATORS_PATH, PROCESSED_DIR, area_by_gemeinde, dissolve_layer, load_boundaries, merge_indicator, \
    write_indicator_table


GEMEINDE_KEY = "ags"
HALTESTELLEN_PATH = PROCESSED_DIR / "osm_haltestellen_regen.gpkg"
HALTESTELLEN_LAYER = "osm_haltestellen_regen"
SIEDLUNGSFLAECHE_PATH = PROCESSED_DIR / "atkis_siedlungsflaeche_regen.gpkg"
SIEDLUNGSFLAECHE_LAYER = "atkis_siedlungsflaeche_regen"
EINZUGSBEREICH_M = 600
NUR_WOHNBAUFLAECHE = False
WOHNBAUFLAECHE_KLASSE = "AX_Wohnbauflaeche"
HALTESTELLEN_KATEGORIEN = None


def load_haltestellen() -> gpd.GeoDataFrame:
    stops = gpd.read_file(HALTESTELLEN_PATH, layer=HALTESTELLEN_LAYER)

    # Die Haltestellen wurden mit 1000-m-Puffer ueber die Kreisgrenze hinaus geladen; sie werden bewusst NICHT auf den Landkreis geclippt, damit Randgemeinden nicht kuenstlich schlechter dastehen.
    if HALTESTELLEN_KATEGORIEN is not None:
        stops = stops[stops["kategorie"].isin(HALTESTELLEN_KATEGORIEN)]

    verteilung = stops["kategorie"].value_counts().to_dict()
    print(f"  Haltestellen: {len(stops)} ({', '.join(f'{k}: {v}' for k, v in verteilung.items())})")
    return stops


def load_siedlungsflaeche() -> gpd.GeoDataFrame:
    siedlung = gpd.read_file(SIEDLUNGSFLAECHE_PATH, layer=SIEDLUNGSFLAECHE_LAYER)

    if NUR_WOHNBAUFLAECHE:
        siedlung = siedlung[siedlung["nutzungsart"] == WOHNBAUFLAECHE_KLASSE]
        print(f"Siedlungsflaeche: {len(siedlung)} features (nur {WOHNBAUFLAECHE_KLASSE})")
    else:
        print(f"Siedlungsflaeche: {len(siedlung)} features (alle ATKIS-Klassen)")
    return siedlung


def einzugsbereich(stops: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    puffer = gpd.GeoDataFrame(geometry=stops.geometry.buffer(EINZUGSBEREICH_M), crs=stops.crs)
    vereinigt = dissolve_layer(puffer)
    print(f"  {EINZUGSBEREICH_M}-m-Einzugsbereich: {vereinigt.geometry.area.sum() / 1e6:.1f} km2 (vereinigt)")
    return vereinigt


def compute_oepnv_erschliessungsgrad(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    print(f"Computing OePNV-Erschliessungsgrad der Siedlungsflaeche "
          f"(Anteil im {EINZUGSBEREICH_M}-m-Einzugsbereich)...")

    stops = load_haltestellen()
    siedlung = load_siedlungsflaeche()
    siedlung_union = dissolve_layer(siedlung)
    ez = einzugsbereich(stops)

    erschlossen = gpd.overlay(siedlung_union, ez, how="intersection", keep_geom_type=False)

    siedlung_m2 = area_by_gemeinde(siedlung_union, boundaries)
    erschlossen_m2 = area_by_gemeinde(erschlossen, boundaries)

    zero_mask = siedlung_m2 == 0
    if zero_mask.any():
        print(f"  WARNING: zero Siedlungsflaeche for {GEMEINDE_KEY}={siedlung_m2[zero_mask].index.tolist()} "
              "-> oepnv_erschliessungsgrad set to NaN")

    ratio_pct = (erschlossen_m2 / siedlung_m2.where(~zero_mask)) * 100

    # Der Anteil kann konstruktionsbedingt nicht ueber 100 % liegen.
    if (ratio_pct > 100.001).any():
        print("  WARNING: Anteil ueber 100 % - Ueberlappung im Einzugsbereich pruefen")

    perzentil = ratio_pct.rank(pct=True) * 100

    print(f"\nMedian: {ratio_pct.median():.1f} %, Spannweite {ratio_pct.min():.1f}-{ratio_pct.max():.1f} %")

    indicator_df = pd.DataFrame({
        "oepnv_siedlungsflaeche_km2": (siedlung_m2 / 1e6).round(2),
        "oepnv_erschlossen_km2": (erschlossen_m2 / 1e6).round(2),
        "oepnv_erschliessungsgrad_prozent": ratio_pct.round(1),
        "oepnv_erschliessungsgrad_perzentil": perzentil.round(1),
    })
    indicator_df.index.name = GEMEINDE_KEY
    return indicator_df


def report(indicator_df: pd.DataFrame, boundaries: gpd.GeoDataFrame) -> None:
    schau = indicator_df.join(boundaries.set_index(GEMEINDE_KEY)["name"])
    spalten = ["name", "oepnv_siedlungsflaeche_km2", "oepnv_erschlossen_km2",
               "oepnv_erschliessungsgrad_prozent"]
    print("\n  Top 3 / Bottom 3:")
    print(schau.nlargest(3, "oepnv_erschliessungsgrad_prozent")[spalten].to_string(index=False))
    print(schau.nsmallest(3, "oepnv_erschliessungsgrad_prozent")[spalten].to_string(index=False))


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df = compute_oepnv_erschliessungsgrad(boundaries)
    report(indicator_df, boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"\nWrote {len(merged)} rows -> {INDICATORS_PATH}")
    print(f"Analysed: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()