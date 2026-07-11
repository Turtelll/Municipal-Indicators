from __future__ import annotations

import datetime as dt
import zipfile
from pathlib import Path

import geopandas as gpd
import requests

from common import CRS, RAW_DIR


VG250EW_URL = ("https://daten.gdz.bkg.bund.de/produkte/vg/vg250-ew_ebenen_1231/aktuell/vg250-ew_12-31.utm32s.gpkg.ebenen.zip")

GEM_LAYER = "vg250_gem"
KREISSCHLUESSEL = "09276"
GF_LAND = 4
OUT_PATH = RAW_DIR / "gemeinden_regen.gpkg"


def download_zip() -> Path:
    cache_dir = RAW_DIR / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / "vg250-ew.zip"

    if not zip_path.exists():
        response = requests.get(VG250EW_URL, stream=True, timeout=300)
        response.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

    return zip_path


def load_gemeinden(zip_path: Path) -> gpd.GeoDataFrame:
    with zipfile.ZipFile(zip_path) as z:
        gpkg = next(name for name in z.namelist() if name.endswith(".gpkg"))

    gdf = gpd.read_file(f"/vsizip/{zip_path.as_posix()}/{gpkg}", layer=GEM_LAYER)

    gdf = gdf[
        gdf["AGS"].astype(str).str.startswith(KREISSCHLUESSEL)
        & (gdf["GF"] == GF_LAND)
    ]

    gemeinden = gdf.rename(columns={
        "AGS": "ags",
        "GEN": "name",
        "EWZ": "einwohner",
        "KFL": "flaeche_km2",
    })[["ags", "name", "einwohner", "flaeche_km2", "geometry"]]

    gemeinden["ags"] = gemeinden["ags"].astype(str)
    return gemeinden.to_crs(CRS).sort_values("name").reset_index(drop=True)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = download_zip()
    gemeinden = load_gemeinden(zip_path)

    gemeinden.to_file(OUT_PATH, driver="GPKG")


if __name__ == "__main__":
    main()