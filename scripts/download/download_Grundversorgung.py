from __future__ import annotations

import datetime as dt
import re

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd

from common import CRS, RAW_DIR, load_aoi

# Combined Overpass tag filter for all 4 Grundversorgung categories.
GRUNDVERSORGUNG_TAGS = {
    "shop": "supermarket",
    "amenity": ["pharmacy", "doctors", "school"],
    "healthcare": "doctor",
}

GRUNDSCHULE_NAME_PATTERN = re.compile(
    r"grundschule|volksschule|grund-?\s*(?:und|/)\s*(?:mittel|haupt)schule",
    re.IGNORECASE,
)

TAG_COLUMNS = ["shop", "amenity", "healthcare", "isced:level", "name"]


def buffer_aoi(aoi: gpd.GeoDataFrame, distance_m: float = 3000) -> gpd.GeoDataFrame:
    # Buffer outward so the POI/road-network queries aren't truncated at the Landkreis boarder
    return gpd.GeoDataFrame(geometry=aoi.geometry.buffer(distance_m), crs=aoi.crs)


def download_grundversorgung_pois(aoi: gpd.GeoDataFrame) -> dict[str, gpd.GeoDataFrame]:
    # Fetch all OSM POIs matching the 4 Grundversorgung categories via Overpass (osmnx).
    aoi_polygon_4326 = aoi.to_crs("EPSG:4326").geometry.iloc[0]
    pois = ox.features_from_polygon(aoi_polygon_4326, tags=GRUNDVERSORGUNG_TAGS)
    pois = pois.reset_index()

    for col in TAG_COLUMNS:
        if col not in pois.columns:
            pois[col] = pd.NA

    supermarkt = pois[pois["shop"] == "supermarket"]
    hausarzt = pois[(pois["amenity"] == "doctors") | (pois["healthcare"] == "doctor")]
    apotheke = pois[pois["amenity"] == "pharmacy"]

    schools = pois[pois["amenity"] == "school"]
    isced_primary = schools["isced:level"].astype("string").str.contains("1", na=False)
    name_primary = schools["name"].astype("string").str.contains(GRUNDSCHULE_NAME_PATTERN, na=False)
    grundschule = schools[isced_primary | name_primary]

    keep_cols = ["element", "id", *TAG_COLUMNS, "geometry"]
    layers = {"supermarkt": supermarkt, "hausarzt": hausarzt, "apotheke": apotheke, "grundschule": grundschule}
    return {name: gdf[keep_cols].to_crs(CRS) for name, gdf in layers.items()}


def download_road_network(aoi: gpd.GeoDataFrame) -> nx.MultiDiGraph:
    # Fetch the drivable road network via Overpass (osmnx). network_type="drive"
    aoi_polygon_4326 = aoi.to_crs("EPSG:4326").geometry.iloc[0]
    return ox.graph_from_polygon(aoi_polygon_4326, network_type="drive", simplify=True)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    retrieved = dt.date.today().isoformat()

    aoi = load_aoi()
    aoi_buffered = buffer_aoi(aoi, distance_m=3000)

    print("Downloading OSM Grundversorgung POIs (Supermarkt, Hausarzt, Apotheke, Grundschule)...")
    poi_layers = download_grundversorgung_pois(aoi_buffered)

    poi_path = RAW_DIR / "osm_poi_grundversorgung_regen.gpkg"
    if poi_path.exists():
        poi_path.unlink()
    for layer_name, gdf in poi_layers.items():
        if gdf.empty:
            print(f"  {layer_name}: 0 Features - uebersprungen")
            continue
        gdf.to_file(poi_path, layer=layer_name, driver="GPKG")
        print(f"  {layer_name}: {len(gdf)} Features")

    print("Downloading OSM road network (osmnx, network_type='drive')...")
    road_network = download_road_network(aoi_buffered)
    road_network_path = RAW_DIR / "strassennetz_regen.graphml"
    ox.save_graphml(road_network, filepath=road_network_path)
    print(f"  {road_network.number_of_nodes()} nodes, {road_network.number_of_edges()} edges -> {road_network_path}")
    print(f"\nRetrieved: {retrieved}")


if __name__ == "__main__":
    main()
