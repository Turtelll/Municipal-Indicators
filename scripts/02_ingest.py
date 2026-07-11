from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
import pyogrio
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download.common import CRS, PROCESSED_DIR, RAW_DIR, load_aoi


@dataclass
class DatasetSpec:
    kind: str  # "vector" | "graphml"
    raw_path: Path
    out_path: Path
    clip: bool = False
    polygonal: bool = True


DATASETS: list[DatasetSpec] = [
    DatasetSpec("vector", RAW_DIR / "osm_buildings_regen.gpkg", PROCESSED_DIR / "osm_buildings_regen.gpkg", clip=True,
                polygonal=True), DatasetSpec("vector", RAW_DIR / "atkis_siedlungsflaeche_regen.gpkg",
                                             PROCESSED_DIR / "atkis_siedlungsflaeche_regen.gpkg", clip=True,
                                             polygonal=True),
    DatasetSpec("vector", RAW_DIR / "atkis_verkehrsflaeche_regen.gpkg",
                PROCESSED_DIR / "atkis_verkehrsflaeche_regen.gpkg", clip=True, polygonal=True),
    DatasetSpec("vector", RAW_DIR / "schutzgebiete_regen.gpkg", PROCESSED_DIR / "schutzgebiete_regen.gpkg", clip=True,
                polygonal=True), DatasetSpec("vector", RAW_DIR / "osm_poi_grundversorgung_regen.gpkg",
                                             PROCESSED_DIR / "osm_poi_grundversorgung_regen.gpkg", clip=False,
                                             polygonal=False),
    DatasetSpec("vector", RAW_DIR / "osm_haltestellen_regen.gpkg", PROCESSED_DIR / "osm_haltestellen_regen.gpkg",
                clip=False, polygonal=False),
    DatasetSpec("graphml", RAW_DIR / "strassennetz_regen.graphml", PROCESSED_DIR / "strassennetz_regen.graphml"),
    DatasetSpec("vector", RAW_DIR / "gemeinden_regen.gpkg", PROCESSED_DIR / "gemeinden_regen.gpkg", clip=False,
                polygonal=True)]

# Gemeindegrenzen (BKG VG250-EW): liegen bereits in EPSG:25832 und sind ueber den
# AGS-Praefix auf den Landkreis begrenzt -> kein Clip noetig, nur Geometrie-Check.


# Tabellarische Quellen der Energie-Indikatoren (MaStR, Energie-Atlas Bayern)
KREISSCHLUESSEL = "09276"

MASTR_RAW = RAW_DIR / "mastr_units.csv"
MASTR_OUT = PROCESSED_DIR / "mastr_units_regen.csv"
ENERGIEATLAS_OUT = PROCESSED_DIR / "pv_dachpotenzial_regen.csv"
GEMEINDEN_OUT = PROCESSED_DIR / "gemeinden_regen.gpkg"

MASTR_LEISTUNGSSPALTEN = ["Bruttoleistung", "Nettonennleistung"]
BETRIEBSSTATUS_AKTIV = "In Betrieb"

ENERGIEATLAS_COLUMNS = {"Name": "name", "Anzahl Photovoltaik Anlagen": "anzahl_pv_anlagen",
                        "Photovoltaik-Potenzial (Stromproduktion) (MWh)": "pv_potenzial_ertrag_mwh",
                        "Photovoltaik-Potenzial (Leistung) (MWp)": "pv_potenzial_leistung_mwp",
                        "Installierte Photovoltaik Leistung (MWp)": "pv_installiert_ea_mwp",
                        "Verbleibendes Photovoltaik-Potenzial (Leistung) (MWp)": "pv_restpotenzial_mwp",
                        "Ausbaugrad (Photovoltaik) (%)": "pv_ausbaugrad_ea_prozent", }


def discover_layers(path: Path) -> list[str]:
    return [name for name, _geom_type in pyogrio.list_layers(path)]


def ensure_crs(gdf: gpd.GeoDataFrame, *, source: str) -> tuple[gpd.GeoDataFrame, str]:
    if gdf.crs is None:
        raise ValueError(f"{source}: missing CRS - refusing to guess one")
    if gdf.crs != CRS:
        return gdf.to_crs(CRS), f"reprojected -> {CRS}"
    return gdf, f"CRS ok ({CRS})"


def _extract_polygonal(geom):
    # GeometryCollection artifacts from WFS/GML parsing; keep only the
    # polygonal parts (e.g. schutzgebiete's nationalpark/vogelschutzgebiet).
    polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
    return unary_union(polys) if polys else None


def clean_geometries(gdf: gpd.GeoDataFrame, *, polygonal: bool) -> tuple[gpd.GeoDataFrame, int]:
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    # make_valid() runs first: repairing a self-intersecting/degenerate Polygon
    # can itself produce a GeometryCollection, so collection-extraction has to
    # happen after make_valid(), not before it, or that case slips through.
    gdf["geometry"] = gdf.geometry.make_valid()
    gdf = gdf[~gdf.geometry.is_empty]

    n_collections = 0
    if polygonal:
        is_collection = gdf.geometry.geom_type == "GeometryCollection"
        n_collections = int(is_collection.sum())
        if n_collections:
            gdf.loc[is_collection, "geometry"] = gdf.loc[is_collection, "geometry"].apply(_extract_polygonal)
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty]

    return gdf, n_collections


def clip_to_aoi(gdf: gpd.GeoDataFrame, aoi_polygon) -> tuple[gpd.GeoDataFrame, float]:
    area_before_km2 = gdf.geometry.area.sum() / 1e6
    clipped = gpd.clip(gdf, aoi_polygon)
    area_after_km2 = clipped.geometry.area.sum() / 1e6
    return clipped, area_before_km2 - area_after_km2


def ingest_vector_dataset(spec: DatasetSpec, aoi_polygon) -> dict[str, gpd.GeoDataFrame]:
    note = "" if spec.clip else " (buffered dataset, NOT clipped to Landkreis boundary)"
    print(f"Ingesting {spec.raw_path.name}{note}...")

    layers = discover_layers(spec.raw_path)
    multi = len(layers) > 1

    result: dict[str, gpd.GeoDataFrame] = {}
    for layer in layers:
        gdf = gpd.read_file(spec.raw_path, layer=layer if multi else None)
        n_before = len(gdf)
        gdf, crs_msg = ensure_crs(gdf, source=layer)
        gdf, n_repaired = clean_geometries(gdf, polygonal=spec.polygonal)

        parts = [crs_msg]
        if spec.clip:
            gdf, removed_km2 = clip_to_aoi(gdf, aoi_polygon)
            gdf, n_repaired_post_clip = clean_geometries(gdf, polygonal=spec.polygonal)
            n_repaired += n_repaired_post_clip
            parts.append(f"AOI clip removed {removed_km2:.2f} km2")

        repaired_note = f", {n_repaired} GeometryCollection repaired" if n_repaired else ""
        parts.append(f"{n_before} -> {len(gdf)} features{repaired_note}")
        print(f"  {layer}: {', '.join(parts)}")
        result[layer] = gdf
    return result


def write_vector_dataset(spec: DatasetSpec, layers: dict[str, gpd.GeoDataFrame]) -> None:
    if spec.out_path.exists():
        spec.out_path.unlink()
    for layer, gdf in layers.items():
        gdf.to_file(spec.out_path, layer=layer, driver="GPKG")
    print(f"  Saved {len(layers)} layer(s) -> {spec.out_path}")


def ingest_graphml_dataset(spec: DatasetSpec) -> None:
    print(f"Ingesting {spec.raw_path.name} (reproject -> {CRS})...")
    graph = ox.load_graphml(spec.raw_path)
    graph_crs = str(graph.graph.get("crs"))
    if graph_crs.lower() != "epsg:4326":
        raise ValueError(f"{spec.raw_path.name}: expected CRS epsg:4326, got {graph_crs!r}")

    # osmnx sets the 'length' edge attribute geodesically (in meters) at
    # graph-build time; project_graph only reprojects node/edge coordinates,
    # so 'length' stays numerically valid across the reprojection.
    graph = ox.project_graph(graph, to_crs=CRS)
    ox.save_graphml(graph, filepath=spec.out_path)
    print(f"  Reprojected {graph_crs} -> {CRS}, {graph.number_of_nodes()} nodes, "
          f"{graph.number_of_edges()} edges -> {spec.out_path}")


def find_energieatlas_export() -> Path:
    # Der Export traegt einen Zeitstempel im Namen: energieatlas_<ts>.csv
    exports = sorted(RAW_DIR.glob("energieatlas*.csv"))
    if not exports:
        raise FileNotFoundError(f"Kein energieatlas*.csv in {RAW_DIR} gefunden")
    return exports[-1]


def ingest_mastr() -> pd.DataFrame:
    print(f"Ingesting {MASTR_RAW.name} (tabular, joined by AGS - no geometry)...")
    units = pd.read_csv(MASTR_RAW, dtype={"Gemeindeschluessel": str, "Postleitzahl": str})
    n_before = len(units)

    # AGS muss die fuehrende Null behalten (Bayern = 09...) und im AOI liegen.
    outside = ~units["Gemeindeschluessel"].str.startswith(KREISSCHLUESSEL, na=False)
    if outside.any():
        raise ValueError(f"MaStR: {int(outside.sum())} Einheiten ausserhalb {KREISSCHLUESSEL}")

    for col in MASTR_LEISTUNGSSPALTEN:
        units[col] = pd.to_numeric(units[col], errors="coerce")
    if units[MASTR_LEISTUNGSSPALTEN].isna().any().any():
        raise ValueError("MaStR: fehlende Leistungswerte nach numerischer Konvertierung")

    aktiv = units[units["EinheitBetriebsstatus"] == BETRIEBSSTATUS_AKTIV].copy()
    aktiv = aktiv.rename(columns={"Gemeindeschluessel": "ags"})

    print(f"  Betriebsstatus '{BETRIEBSSTATUS_AKTIV}': {n_before} -> {len(aktiv)} Einheiten")
    print(f"  {aktiv['ags'].nunique()} Gemeinden, "
          f"{aktiv['Nettonennleistung'].sum() / 1000:.1f} MW netto installiert")
    return aktiv


def ingest_energieatlas() -> pd.DataFrame:
    raw_path = find_energieatlas_export()
    print(f"Ingesting {raw_path.name} (tabular, joined by AGS - no geometry)...")
    atlas = pd.read_csv(raw_path, dtype={"Verwaltungseinheit": str})

    # Export-Bug: der Header fuehrt "Anteil Sonstige (%)" doppelt; die zweite Spalte enthaelt in Wahrheit den Datenstand.
    duplicate = "Anteil Sonstige (%).1"
    if duplicate in atlas.columns:
        atlas = atlas.rename(columns={duplicate: "datenstand"})
        print("  Doppelte Spalte 'Anteil Sonstige (%)' enthaelt den Datenstand -> 'datenstand'")

    # "Verwaltungseinheit" ist der AGS OHNE die fuehrende 09 (Bayern): 276135
    atlas["ags"] = "09" + atlas["Verwaltungseinheit"].str.zfill(6)

    keep = ["ags"] + [c for c in ENERGIEATLAS_COLUMNS if c in atlas.columns]
    if "datenstand" in atlas.columns:
        keep.append("datenstand")
    tabelle = atlas[keep].rename(columns=ENERGIEATLAS_COLUMNS)

    # MaStR rechnet in kW, der Energie-Atlas in MWp -> gemeinsame Einheit kW.
    tabelle["pv_potenzial_leistung_kw"] = tabelle["pv_potenzial_leistung_mwp"] * 1000
    tabelle["pv_installiert_ea_kw"] = tabelle["pv_installiert_ea_mwp"] * 1000

    print(f"  {len(tabelle)} Gemeinden, Dachpotenzial "
          f"{tabelle['pv_potenzial_leistung_mwp'].sum():.0f} MWp "
          f"(Datenstand {tabelle['datenstand'].iloc[0]})")
    print("  Note: Potenzial auf ganze MWp gerundet -> Rundungsunschaerfe bei kleinen Gemeinden")
    return tabelle.sort_values("name").reset_index(drop=True)


def validate_join_keys(mastr: pd.DataFrame, atlas: pd.DataFrame) -> None:
    # Ein AGS-Mismatch faellt sonst erst als weisses Loch in der Choroplethenkarte auf.
    print("Validating AGS join keys across sources...")
    gemeinden = gpd.read_file(GEMEINDEN_OUT)
    keys = {"gemeinden": set(gemeinden["ags"]), "mastr": set(mastr["ags"]), "energieatlas": set(atlas["ags"])}
    for name, key_set in keys.items():
        print(f"  {name}: {len(key_set)} AGS")

    reference = keys["gemeinden"]
    for name, key_set in keys.items():
        if key_set != reference:
            raise ValueError(f"AGS-Mismatch in {name}: fehlt {sorted(reference - key_set)}, "
                             f"zusaetzlich {sorted(key_set - reference)}")
    print(f"  OK: alle Quellen decken dieselben {len(reference)} Gemeinden ab")


def write_table(table: pd.DataFrame, out_path: Path) -> None:
    table.to_csv(out_path, index=False, encoding="utf-8")
    print(f"  Saved {len(table)} rows -> {out_path}")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    aoi_polygon = load_aoi().geometry.iloc[0]

    for spec in DATASETS:
        if spec.kind == "vector":
            layers = ingest_vector_dataset(spec, aoi_polygon)
            write_vector_dataset(spec, layers)
        else:
            ingest_graphml_dataset(spec)
        print()

    mastr = ingest_mastr()
    write_table(mastr, MASTR_OUT)
    print()

    energieatlas = ingest_energieatlas()
    write_table(energieatlas, ENERGIEATLAS_OUT)
    print()

    validate_join_keys(mastr, energieatlas)
    print()

    print(f"Ingested: {dt.date.today().isoformat()}")


if __name__ == "__main__":
    main()
