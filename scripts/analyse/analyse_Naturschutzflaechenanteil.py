from __future__ import annotations

import geopandas as gpd
import pandas as pd

from common import INDICATORS_PATH, PROCESSED_DIR, area_by_gemeinde, dissolve_layer, load_boundaries, merge_indicator, \
    write_indicator_table

SCHUTZGEBIETE_PATH = PROCESSED_DIR / "schutzgebiete_regen.gpkg"
SCHUTZGEBIETE_LAYERS = ["naturschutzgebiet", "nationalpark", "landschaftsbestandteil_flaechig", "naturdenkmal_flaechig",
                        "fauna_flora_habitat_gebiet", "vogelschutzgebiet", "landschaftsschutzgebiet", ]


def compute_naturschutzflaechenanteil(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    print("Computing Naturschutzflaechenanteil (geschuetzte Flaeche / Gesamtflaeche)...")

    layers = [gpd.read_file(SCHUTZGEBIETE_PATH, layer=layer) for layer in SCHUTZGEBIETE_LAYERS]
    for layer, gdf in zip(SCHUTZGEBIETE_LAYERS, layers):
        print(f"  {layer}: {len(gdf)} features")

    # Union of all protection-category layers; dissolve first so overlapping
    # designations (e.g. FFH-Gebiet inside a Landschaftsschutzgebiet) aren't double-counted.
    combined = pd.concat([gdf[["geometry"]] for gdf in layers], ignore_index=True)
    combined = gpd.GeoDataFrame(combined, crs=layers[0].crs)
    print("  Dissolving Schutzgebiete union...")
    schutz_area_m2 = area_by_gemeinde(dissolve_layer(combined), boundaries)

    gesamtflaeche_m2 = boundaries.set_index("ags").geometry.area

    zero_mask = gesamtflaeche_m2 == 0
    if zero_mask.any():
        print(f"  WARNING: zero Gesamtflaeche for ags={gesamtflaeche_m2[zero_mask].index.tolist()} "
              "-> naturschutzflaechenanteil set to NaN")

    ratio_pct = (schutz_area_m2 / gesamtflaeche_m2.where(~zero_mask)) * 100
    percentile = ratio_pct.rank(pct=True) * 100

    return pd.DataFrame(
        {"naturschutzflaechenanteil": ratio_pct.round(1), "naturschutzflaechenanteil_perzentil": percentile.round(1)})


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df = compute_naturschutzflaechenanteil(boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"Wrote {len(merged)} rows -> {INDICATORS_PATH}")


if __name__ == "__main__":
    main()
