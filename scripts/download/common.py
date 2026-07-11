from __future__ import annotations

import tempfile
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BOUNDARIES_PATH = PROJECT_ROOT / "data" / "raw" / "gemeinden_regen.gpkg"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CRS = "EPSG:25832"


def load_aoi() -> gpd.GeoDataFrame:
    gemeinden = gpd.read_file(BOUNDARIES_PATH)
    aoi = gemeinden.union_all()
    return gpd.GeoDataFrame(geometry=[aoi], crs=gemeinden.crs)


def fetch_wfs_layer(url: str, type_name: str, bbox: str, namespaces: str | None = None, page_size: int = 2000,
        timeout: int = 120, ) -> gpd.GeoDataFrame:
    # Fetch all features of one WFS 2.0 layer within a bbox, paging as needed.
    frames = []
    start_index = 0
    with tempfile.TemporaryDirectory() as tmp_dir:
        while True:
            params = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": type_name,
                "srsName": CRS, "bbox": bbox, "count": page_size, "startIndex": start_index, }
            if namespaces:
                params["namespaces"] = namespaces
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()

            if b'numberReturned="0"' in response.content:
                break

            tmp_path = Path(tmp_dir) / f"{type_name.split(':')[-1]}_{start_index}.gml"
            tmp_path.write_bytes(response.content)
            with warnings.catch_warnings():
                # ATKIS GML redundantly declares "identifier" as both a
                # gml:identifier and a plain attribute; pyogrio warns and
                # silently drops the duplicate, which is the correct outcome.
                warnings.filterwarnings("ignore", message="Field with same name")
                page = gpd.read_file(tmp_path)

            if page.empty:
                break
            frames.append(page)
            if len(page) < page_size:
                break
            start_index += page_size

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=CRS)
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=CRS)
