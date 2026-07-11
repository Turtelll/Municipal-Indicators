from __future__ import annotations

import datetime as dt

import geopandas as gpd
import osmnx as ox
import pandas as pd

from common import CRS, RAW_DIR, fetch_wfs_layer, load_aoi

ATKIS_WFS_URL = "https://geoservices.bayern.de/wfs/v1/ogc_atkis_basisdlm.cgi"
ATKIS_NAMESPACES = "xmlns(adv,http://www.adv-online.de/namespaces/adv/gid/7.1)"
ATKIS_LAYERS = ["adv:AX_Wohnbauflaeche", "adv:AX_IndustrieUndGewerbeflaeche", "adv:AX_FlaecheGemischterNutzung",
                "adv:AX_FlaecheBesondererFunktionalerPraegung", ]
VERKEHR_LAYERS = ["adv:AX_Strassenverkehr", "adv:AX_Bahnverkehr", "adv:AX_Flugverkehr", "adv:AX_Platz",
                   "adv:AX_Schiffsverkehr", ]  # Schiffsverkehr is empty for this AOI; kept for completeness


def download_osm_buildings(aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Fetch OSM building footprints within the AOI via Overpass (osmnx).
    aoi_polygon_4326 = aoi.to_crs("EPSG:4326").geometry.iloc[0]
    buildings = ox.features_from_polygon(aoi_polygon_4326, tags={"building": True})
    buildings = buildings[buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    buildings = buildings.reset_index()[["element", "id", "building", "geometry"]]
    return buildings.to_crs(CRS)


def download_atkis_siedlungsflaeche(aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Fetch and combine the ATKIS Basis-DLM settlement-area object classes.
    minx, miny, maxx, maxy = aoi.total_bounds
    bbox = f"{minx},{miny},{maxx},{maxy},{CRS}"

    layers = []
    for type_name in ATKIS_LAYERS:
        layer = fetch_wfs_layer(ATKIS_WFS_URL, type_name, bbox, namespaces=ATKIS_NAMESPACES)
        layer["nutzungsart"] = type_name.split(":")[-1]
        layers.append(layer)

    combined = pd.concat(layers, ignore_index=True)
    return gpd.GeoDataFrame(combined, crs=CRS)


def download_atkis_verkehrsflaeche(aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Fetch and combine the ATKIS Basis-DLM Verkehrsflaeche object classes
    # (the transport-area part of Siedlungs- und Verkehrsflaeche).
    minx, miny, maxx, maxy = aoi.total_bounds
    bbox = f"{minx},{miny},{maxx},{maxy},{CRS}"

    layers = []
    for type_name in VERKEHR_LAYERS:
        layer = fetch_wfs_layer(ATKIS_WFS_URL, type_name, bbox, namespaces=ATKIS_NAMESPACES)
        if layer.empty:
            print(f"  {type_name}: 0 Features - uebersprungen")
            continue
        layer["nutzungsart"] = type_name.split(":")[-1]
        layers.append(layer)

    combined = pd.concat(layers, ignore_index=True)
    return gpd.GeoDataFrame(combined, crs=CRS)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    retrieved = dt.date.today().isoformat()

    aoi = load_aoi()

    print("Downloading OSM building footprints...")
    buildings = download_osm_buildings(aoi)
    buildings_path = RAW_DIR / "osm_buildings_regen.gpkg"
    buildings.to_file(buildings_path, driver="GPKG")

    print("Downloading ATKIS Basis-DLM settlement area layers...")
    siedlungsflaeche = download_atkis_siedlungsflaeche(aoi)
    siedlungsflaeche_path = RAW_DIR / "atkis_siedlungsflaeche_regen.gpkg"
    siedlungsflaeche.to_file(siedlungsflaeche_path, driver="GPKG")

    print("Downloading ATKIS Basis-DLM Verkehrsflaeche layers...")
    verkehrsflaeche = download_atkis_verkehrsflaeche(aoi)
    verkehrsflaeche_path = RAW_DIR / "atkis_verkehrsflaeche_regen.gpkg"
    verkehrsflaeche.to_file(verkehrsflaeche_path, driver="GPKG")


if __name__ == "__main__":
    main()
