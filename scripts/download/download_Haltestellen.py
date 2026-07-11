from __future__ import annotations

import datetime as dt

import geopandas as gpd
import osmnx as ox
import pandas as pd

from common import CRS, RAW_DIR, load_aoi

# Legacy scheme (highway=bus_stop, railway=*) and current scheme
# (public_transport=*) both appear in this rural AOI - query both.
HALTESTELLEN_TAGS = {
    "public_transport": ["stop_position", "platform", "station"],
    "highway": "bus_stop",
    "railway": ["stop", "halt", "station", "tram_stop"],
    "amenity": "bus_station",
}

TAG_COLUMNS = ["public_transport", "highway", "railway", "amenity", "name"]


def buffer_aoi(aoi: gpd.GeoDataFrame, distance_m: float = 1000) -> gpd.GeoDataFrame:
    # Margin beyond the 600 m Einzugsbereich so stops just across the Landkreis border aren't missed for edge Gemeinden.
    return gpd.GeoDataFrame(geometry=aoi.geometry.buffer(distance_m), crs=aoi.crs)


def download_haltestellen(aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Fetch OSM public-transport stops (bus + Bahn) via Overpass (osmnx).
    aoi_polygon_4326 = aoi.to_crs("EPSG:4326").geometry.iloc[0]
    stops = ox.features_from_polygon(aoi_polygon_4326, tags=HALTESTELLEN_TAGS)
    stops = stops[stops.geometry.geom_type == "Point"]
    stops = stops.reset_index()

    for col in TAG_COLUMNS:
        if col not in stops.columns:
            stops[col] = pd.NA

    stops["kategorie"] = "bus"
    stops.loc[stops["railway"].notna(), "kategorie"] = "bahn"

    keep_cols = ["element", "id", *TAG_COLUMNS, "kategorie", "geometry"]
    return stops[keep_cols].to_crs(CRS)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    retrieved = dt.date.today().isoformat()

    aoi = load_aoi()
    aoi_buffered = buffer_aoi(aoi, distance_m=1000)

    print("Downloading OSM Haltestellen (OePNV: Bus + Bahn)...")
    haltestellen = download_haltestellen(aoi_buffered)

    out_path = RAW_DIR / "osm_haltestellen_regen.gpkg"
    haltestellen.to_file(out_path, driver="GPKG")

    n_bus = int((haltestellen["kategorie"] == "bus").sum())
    n_bahn = int((haltestellen["kategorie"] == "bahn").sum())
    print(f"  bus: {n_bus} Features")
    print(f"  bahn: {n_bahn} Features")
    print(f"\nRetrieved: {retrieved}")


if __name__ == "__main__":
    main()
