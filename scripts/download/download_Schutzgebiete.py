from __future__ import annotations

import datetime as dt

import geopandas as gpd

from common import CRS, RAW_DIR, fetch_wfs_layer, load_aoi

SCHUTZGEBIETE_WFS_URL = "https://www.lfu.bayern.de/gdi/wfs/natur/schutzgebiete"

SCHUTZGEBIETE_LAYERS = [("natur_wfsschutzgebiete:naturschutzgebiet", "naturschutzgebiet"),
    ("natur_wfsschutzgebiete:nationalpark", "nationalpark"),
    ("natur_wfsschutzgebiete:nationales_naturmonument", "nationales_naturmonument"),
    ("natur_wfsschutzgebiete:landschaftsbestandteil_flaechig", "landschaftsbestandteil_flaechig"),
    ("natur_wfsschutzgebiete:naturdenkmal_flaechig", "naturdenkmal_flaechig"),
    ("natur_wfsschutzgebiete:fauna_flora_habitat_gebiet", "fauna_flora_habitat_gebiet"),
    ("natur_wfsschutzgebiete:vogelschutzgebiet", "vogelschutzgebiet"),
    ("natur_wfsschutzgebiete:landschaftsschutzgebiet", "landschaftsschutzgebiet"),
    ("natur_wfsschutzgebiete:biosphaerenreservat", "biosphaerenreservat"), ]


def download_schutzgebiete(aoi: gpd.GeoDataFrame) -> dict[str, gpd.GeoDataFrame]:
    minx, miny, maxx, maxy = aoi.total_bounds
    bbox = f"{minx},{miny},{maxx},{maxy},{CRS}"
    aoi_polygon = aoi.geometry.iloc[0]

    clipped_layers: dict[str, gpd.GeoDataFrame] = {}
    for type_name, gpkg_layer in SCHUTZGEBIETE_LAYERS:
        fetched = fetch_wfs_layer(SCHUTZGEBIETE_WFS_URL, type_name, bbox)
        if fetched.empty:
            print(f"  {gpkg_layer}: 0 Features im Bbox - uebersprungen")
            continue

        clipped = gpd.clip(fetched, aoi_polygon)
        if clipped.empty:
            print(f"  {gpkg_layer}: 0 Features nach AOI-Clip - uebersprungen")
            continue

        clipped_layers[gpkg_layer] = clipped

    return clipped_layers


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    retrieved = dt.date.today().isoformat()

    aoi = load_aoi()
    aoi_area_km2 = aoi.geometry.area.sum() / 1e6

    print("Downloading LfU Bayern Schutzgebiete layers (WFS query + AOI clip)...")
    layers = download_schutzgebiete(aoi)

    out_path = RAW_DIR / "schutzgebiete_regen.gpkg"
    if out_path.exists():
        out_path.unlink()
    for gpkg_layer, gdf in layers.items():
        gdf.to_file(out_path, layer=gpkg_layer, driver="GPKG")

    print(f"\nRetrieved: {retrieved}")
    print(f"AOI (Landkreis Regen) area: {aoi_area_km2:.1f} km2")
    print(f"Saved {len(layers)} layers -> {out_path}")
    for gpkg_layer, gdf in layers.items():
        area_km2 = gdf.geometry.area.sum() / 1e6
        print(f"  {gpkg_layer}: {len(gdf)} features, {area_km2:.2f} km2 ({100 * area_km2 / aoi_area_km2:.1f}% of AOI)")


if __name__ == "__main__":
    main()
