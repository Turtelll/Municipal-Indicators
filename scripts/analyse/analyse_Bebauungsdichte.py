from __future__ import annotations

import geopandas as gpd
import pandas as pd

from common import INDICATORS_PATH, PROCESSED_DIR, area_by_gemeinde, dissolve_layer, load_boundaries, merge_indicator, \
    write_indicator_table

SIEDLUNGSFLAECHE_PATH = PROCESSED_DIR / "atkis_siedlungsflaeche_regen.gpkg"
SIEDLUNGSFLAECHE_LAYER = "atkis_siedlungsflaeche_regen"
VERKEHRSFLAECHE_PATH = PROCESSED_DIR / "atkis_verkehrsflaeche_regen.gpkg"
VERKEHRSFLAECHE_LAYER = "atkis_verkehrsflaeche_regen"


def compute_bebauungsdichte(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    print("Computing Bebauungsdichte (Siedlungs- und Verkehrsflaeche / Gesamtflaeche)...")

    siedlung = gpd.read_file(SIEDLUNGSFLAECHE_PATH, layer=SIEDLUNGSFLAECHE_LAYER)
    verkehr = gpd.read_file(VERKEHRSFLAECHE_PATH, layer=VERKEHRSFLAECHE_LAYER)
    print(f"  Siedlungsflaeche: {len(siedlung)} features, Verkehrsflaeche: {len(verkehr)} features")

    # Built-up footprint = Siedlungsflaeche + Verkehrsflaeche; dissolve first so
    # overlapping polygons (e.g. a road cutting through a settlement patch) aren't double-counted.
    combined = pd.concat([siedlung[["geometry"]], verkehr[["geometry"]]], ignore_index=True)
    combined = gpd.GeoDataFrame(combined, crs=siedlung.crs)
    print("  Dissolving Siedlungs- und Verkehrsflaeche union...")
    suv_area_m2 = area_by_gemeinde(dissolve_layer(combined), boundaries)

    gesamtflaeche_m2 = boundaries.set_index("ags").geometry.area

    zero_mask = gesamtflaeche_m2 == 0
    if zero_mask.any():
        print(f"  WARNING: zero Gesamtflaeche for ags={gesamtflaeche_m2[zero_mask].index.tolist()} "
              "-> bebauungsdichte set to NaN")

    ratio_pct = (suv_area_m2 / gesamtflaeche_m2.where(~zero_mask)) * 100
    percentile = ratio_pct.rank(pct=True) * 100

    return pd.DataFrame({"bebauungsdichte": ratio_pct.round(1), "bebauungsdichte_perzentil": percentile.round(1)})


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df = compute_bebauungsdichte(boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"Wrote {len(merged)} rows -> {INDICATORS_PATH}")


if __name__ == "__main__":
    main()
