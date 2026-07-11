from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BOUNDARIES_PATH = PROJECT_ROOT / "data" / "processed" / "gemeinden_regen.gpkg"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CRS = "EPSG:25832"

TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
INDICATORS_PATH = TABLES_DIR / "indikatoren_regen.gpkg"
INDICATORS_LAYER = "indikatoren"


def load_boundaries() -> gpd.GeoDataFrame:
    gemeinden = gpd.read_file(BOUNDARIES_PATH)
    if not gemeinden["ags"].is_unique:
        raise ValueError("gemeinden_regen.gpkg: 'ags' is not unique - cannot key per-Gemeinde indicators on it")
    gemeinden["geometry"] = gemeinden.geometry.make_valid()
    if gemeinden.crs != CRS:
        gemeinden = gemeinden.to_crs(CRS)
    return gemeinden


def dissolve_layer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(geometry=[gdf.geometry.union_all()], crs=gdf.crs)


def area_by_gemeinde(gdf: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> pd.Series:
    pieces = gpd.overlay(gdf[["geometry"]], boundaries[["ags", "geometry"]], how="intersection", keep_geom_type=False)

    is_polygonal = pieces.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    n_dropped = int((~is_polygonal).sum())
    if n_dropped:
        print(f"    dropped {n_dropped} non-polygonal overlay sliver(s)")
    pieces = pieces[is_polygonal].copy()
    pieces["area_m2"] = pieces.geometry.area

    area_m2 = pieces.groupby("ags")["area_m2"].sum()
    return area_m2.reindex(boundaries["ags"], fill_value=0.0)


def merge_indicator(boundaries: gpd.GeoDataFrame, new_columns: pd.DataFrame, *, out_path: Path = INDICATORS_PATH,
                    layer: str = INDICATORS_LAYER, ) -> gpd.GeoDataFrame:
    if out_path.exists():
        base = gpd.read_file(out_path, layer=layer)
    else:
        base = boundaries.copy()

    base = base.drop(columns=[c for c in new_columns.columns if c in base.columns])
    merged = base.merge(new_columns, left_on="ags", right_index=True, how="left")
    return gpd.GeoDataFrame(merged, geometry="geometry", crs=boundaries.crs)


def write_indicator_table(gdf: gpd.GeoDataFrame, *, out_path: Path = INDICATORS_PATH,
                          layer: str = INDICATORS_LAYER) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    gdf.to_file(out_path, layer=layer, driver="GPKG")
