from __future__ import annotations

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd

from common import CRS, INDICATORS_PATH, PROCESSED_DIR, load_boundaries, merge_indicator, write_indicator_table

BUILDINGS_PATH = PROCESSED_DIR / "osm_buildings_regen.gpkg"
BUILDINGS_LAYER = "osm_buildings_regen"
POI_PATH = PROCESSED_DIR / "osm_poi_grundversorgung_regen.gpkg"
POI_CATEGORIES = ["supermarkt", "hausarzt", "apotheke", "grundschule"]
GRAPH_PATH = PROCESSED_DIR / "strassennetz_regen.graphml"


def assign_gemeinde(gdf: gpd.GeoDataFrame, boundaries: gpd.GeoDataFrame) -> pd.Series:
    # Which Gemeinde each building belongs to (by footprint, not centroid).
    joined = gpd.sjoin(gdf[["geometry"]], boundaries[["ags", "geometry"]], how="left", predicate="intersects")
    joined = joined[~joined.index.duplicated(keep="first")]
    return joined["ags"].reindex(gdf.index)


def load_road_network() -> nx.MultiDiGraph:
    graph = ox.load_graphml(GRAPH_PATH)
    graph_crs = str(graph.graph.get("crs", "")).lower()
    if graph_crs != CRS.lower():
        raise ValueError(f"{GRAPH_PATH.name}: expected graph CRS {CRS}, got {graph_crs!r}")

    graph = ox.truncate.largest_component(graph, strongly=True)
    return graph


def nearest_nodes_for(graph: nx.MultiDiGraph, gdf: gpd.GeoDataFrame) -> pd.Series:
    # Snap each geometry onto the road network (its nearest routable point).
    points = gdf.geometry.where(gdf.geometry.geom_type == "Point", gdf.geometry.centroid)
    nodes = ox.distance.nearest_nodes(graph, X=points.x.to_numpy(), Y=points.y.to_numpy())
    return pd.Series(nodes, index=gdf.index)


def distance_to_nearest_poi(graph: nx.MultiDiGraph, graph_reversed: nx.MultiDiGraph, poi_nodes: pd.Series) -> dict[
    int, float]:
    # Driving distance to the nearest POI of one category, from every point in the network
    sources = set(poi_nodes.to_numpy())
    return nx.multi_source_dijkstra_path_length(graph_reversed, sources=sources, weight="length")


def compute_netzwerkdistanz_grundversorgung(boundaries: gpd.GeoDataFrame) -> pd.DataFrame:
    # Every building footprint stands in for a residential location ("Wohnstandort").
    print("Computing Netzwerkdistanz zur Grundversorgung...")
    graph = load_road_network()
    graph_reversed = graph.reverse(copy=False)
    poi_layers = {category: gpd.read_file(POI_PATH, layer=category) for category in POI_CATEGORIES}
    buildings = gpd.read_file(BUILDINGS_PATH, layer=BUILDINGS_LAYER)

    # 1) Driving distance to the nearest Supermarkt/Hausarzt/Apotheke/Grundschule
    category_distances: dict[str, dict[int, float]] = {}
    for category, poi_gdf in poi_layers.items():
        poi_nodes = nearest_nodes_for(graph, poi_gdf)
        dist = distance_to_nearest_poi(graph, graph_reversed, poi_nodes)
        category_distances[category] = dist

    # 2) Where each building sits on the network, and which Gemeinde it's in.
    building_nodes = nearest_nodes_for(graph, buildings)
    buildings["ags"] = assign_gemeinde(buildings, boundaries)

    # 3) Per building: distance to each of the 4 categories.
    dist_df = pd.DataFrame({category: building_nodes.map(dist) for category, dist in category_distances.items()})

    # 4) Average the 4 categories per building
    building_mean_m = dist_df.mean(axis=1, skipna=True)
    n_unreachable = int(building_mean_m.isna().sum())
    if n_unreachable:
        print(f"  {n_unreachable} building(s) with no reachable Grundversorgung category - excluded")

    # 5) Average across all buildings in a Gemeinde
    per_building = pd.DataFrame({"ags": buildings["ags"], "distanz_m": building_mean_m})
    gemeinde_mean_m = per_building.groupby("ags")["distanz_m"].mean().reindex(boundaries["ags"])

    netzwerkdistanz = gemeinde_mean_m.round(0)
    percentile = netzwerkdistanz.rank(pct=True) * 100

    return pd.DataFrame({"netzwerkdistanz_grundversorgung": netzwerkdistanz,
                         "netzwerkdistanz_grundversorgung_perzentil": percentile.round(1), })


def main() -> None:
    boundaries = load_boundaries()
    print(f"Loaded {len(boundaries)} Gemeinde-level boundary rows")

    indicator_df = compute_netzwerkdistanz_grundversorgung(boundaries)

    merged = merge_indicator(boundaries, indicator_df)
    write_indicator_table(merged)
    print(f"Wrote {len(merged)} rows -> {INDICATORS_PATH}")


if __name__ == "__main__":
    main()
