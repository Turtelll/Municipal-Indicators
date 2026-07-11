from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse.common import INDICATORS_LAYER, INDICATORS_PATH, PROJECT_ROOT


MAPS_DIR = PROJECT_ROOT / "outputs" / "maps"
TABLES_DIR = PROJECT_ROOT / "outputs" / "tables"
K_KLASSEN = 5
DPI = 300

GEMEINDE_KANTE = "0.45"
GEMEINDE_KANTE_LW = 0.4
LANDKREIS_KANTE = "0.15"
LANDKREIS_KANTE_LW = 1.4

KOPF_FARBE = "#33475b"
ZEBRA_FARBE = "#f4f6f8"
MEDIAN_FARBE = "#e8ecef"
LINIEN_FARBE = "#c9d1d9"


class Indikator:
    def __init__(self, spalte: str, titel: str, einheit: str, cmap: str, hoch_ist_gut: bool = True,
                 nachkomma: int = 1, kurzname: str | None = None):
        self.spalte = spalte
        self.titel = titel
        self.einheit = einheit
        self.cmap = cmap
        self.hoch_ist_gut = hoch_ist_gut
        self.nachkomma = nachkomma
        self.kurzname = kurzname or titel

    @property
    def colormap(self) -> str:
        return self.cmap if self.hoch_ist_gut else f"{self.cmap}_r"


INDIKATOREN = [
    Indikator("bebauungsdichte", "Bebauungsdichte", "%", "Oranges",
              kurzname="Bebauungs-\ndichte\n[%]"),
    Indikator("naturschutzflaechenanteil", "Naturschutzflächenanteil", "%", "Greens",
              kurzname="Naturschutz-\nanteil\n[%]"),
    Indikator("netzwerkdistanz_grundversorgung", "Ø Netzwerkdistanz Grundversorgung", "m", "Purples",
              hoch_ist_gut=False, nachkomma=0, kurzname="Ø Distanz\nGrundvers.\n[m]"),
    Indikator("oepnv_erschliessungsgrad_prozent", "ÖPNV-Erschließungsgrad", "%", "Blues",
              kurzname="ÖPNV-Er-\nschließung\n[%]"),
    Indikator("ee_ausbaugrad_kw_ew", "EE-Ausbaugrad", "kW/EW", "YlGn", nachkomma=2,
              kurzname="EE-Ausbau-\ngrad\n[kW/EW]"),
    Indikator("pv_dach_ausschoepfung_prozent", "Ausschöpfung PV-Dachpotenzial", "%", "OrRd",
              kurzname="PV-Dach-\nausschöpfung\n[%]"),
]


def load_indikatoren() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(INDICATORS_PATH, layer=INDICATORS_LAYER)
    fehlend = [i.spalte for i in INDIKATOREN if i.spalte not in gdf.columns]
    if fehlend:
        raise ValueError(f"Spalten fehlen in {INDICATORS_PATH.name}: {fehlend}. "
                         "Alle Analyse-Skripte nacheinander ausfuehren.")
    return gdf.sort_values("name").reset_index(drop=True)


def quantil_klassen(werte: pd.Series, k: int = K_KLASSEN) -> tuple[pd.Series, np.ndarray]:
    klassen, grenzen = pd.qcut(werte, k, labels=False, retbins=True, duplicates="drop")
    return klassen, grenzen


def legenden_texte(grenzen: np.ndarray, nachkomma: int) -> list[str]:
    fmt = f"{{:.{nachkomma}f}}"
    return [f"{fmt.format(grenzen[i])} – {fmt.format(grenzen[i + 1])}" for i in range(len(grenzen) - 1)]


def zeichne_umriss(ax, gdf: gpd.GeoDataFrame) -> None:
    umriss = gpd.GeoDataFrame(geometry=[gdf.geometry.union_all()], crs=gdf.crs)
    umriss.boundary.plot(ax=ax, color=LANDKREIS_KANTE, linewidth=LANDKREIS_KANTE_LW, zorder=5)


def beschrifte_gemeinden(ax, gdf: gpd.GeoDataFrame, fontsize: float = 6.5) -> None:
    for _, row in gdf.iterrows():
        punkt = row.geometry.representative_point()
        ax.annotate(row["name"], (punkt.x, punkt.y), ha="center", va="center",
                    fontsize=fontsize, color="black", zorder=6,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])


def zeichne_choropleth(ax, gdf: gpd.GeoDataFrame, ind: Indikator, *, labels: bool = False,
                       legendengroesse: int = 8) -> None:
    klassen, grenzen = quantil_klassen(gdf[ind.spalte])
    n_klassen = len(grenzen) - 1
    cmap = plt.get_cmap(ind.colormap, n_klassen)

    gdf = gdf.assign(_klasse=klassen)
    gdf.plot(column="_klasse", cmap=cmap, vmin=0, vmax=n_klassen - 1,
             edgecolor=GEMEINDE_KANTE, linewidth=GEMEINDE_KANTE_LW, ax=ax)
    zeichne_umriss(ax, gdf)

    texte = legenden_texte(grenzen, ind.nachkomma)
    patches = [mpatches.Patch(facecolor=cmap(i), edgecolor="grey", linewidth=0.4, label=texte[i])
               for i in range(n_klassen)]
    ax.legend(handles=patches, title=ind.einheit, loc="lower right", fontsize=legendengroesse - 1,
              title_fontsize=legendengroesse, frameon=True, framealpha=0.9)

    if labels:
        beschrifte_gemeinden(ax, gdf)

    ax.set_axis_off()


def abbildung_uebersicht(gdf: gpd.GeoDataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(9, 9))

    gdf.plot(ax=ax, color="#f2f2ef", edgecolor=GEMEINDE_KANTE, linewidth=GEMEINDE_KANTE_LW)
    zeichne_umriss(ax, gdf)
    beschrifte_gemeinden(ax, gdf, fontsize=7.5)
    ax.set_axis_off()

    pfad = MAPS_DIR / "abb1_uebersichtskarte.png"
    fig.savefig(pfad, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return pfad


def abbildung_panel(gdf: gpd.GeoDataFrame) -> Path:
    fig, axes = plt.subplots(2, 3, figsize=(16.5, 11))

    for ax, ind in zip(axes.flat, INDIKATOREN):
        zeichne_choropleth(ax, gdf, ind, labels=False, legendengroesse=7)
        ax.set_title(ind.titel, fontsize=11, weight="bold", pad=8, y=1.0)

    plt.tight_layout()

    pfad = MAPS_DIR / "abb2_panel_indikatoren.png"
    fig.savefig(pfad, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    return pfad


def zahl_de(wert: float, nachkomma: int) -> str:
    text = f"{wert:,.{nachkomma}f}"
    return text.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")


def tabelle_indikatoren(gdf: gpd.GeoDataFrame) -> Path:
    kopf = ["Gemeinde"] + [i.kurzname for i in INDIKATOREN]

    zeilen = [[row["name"]] + [zahl_de(row[i.spalte], i.nachkomma) for i in INDIKATOREN]
              for _, row in gdf.iterrows()]
    zeilen.append(["Median (Landkreis)"] + [zahl_de(gdf[i.spalte].median(), i.nachkomma)
                                            for i in INDIKATOREN])

    n_zeilen = len(zeilen)
    fig, ax = plt.subplots(figsize=(11, 0.30 * n_zeilen + 2.2))
    ax.set_axis_off()

    tab = ax.table(cellText=zeilen, colLabels=kopf, cellLoc="right", loc="center",
                   colWidths=[0.238] + [0.127] * len(INDIKATOREN))
    tab.auto_set_font_size(False)
    tab.set_fontsize(8.5)
    tab.scale(1, 1.5)

    for (zeile, spalte), zelle in tab.get_celld().items():
        zelle.set_edgecolor(LINIEN_FARBE)
        zelle.set_linewidth(0.5)

        if zeile == 0:
            zelle.set_facecolor(KOPF_FARBE)
            zelle.set_text_props(color="white", weight="bold", fontsize=8)
            zelle.set_height(zelle.get_height() * 3.0)
        elif zeile == n_zeilen:
            zelle.set_facecolor(MEDIAN_FARBE)
            zelle.set_text_props(weight="bold")
        elif zeile % 2 == 0:
            zelle.set_facecolor(ZEBRA_FARBE)

        if spalte == 0 and zeile > 0:
            zelle.set_text_props(ha="left")
            zelle.PAD = 0.03

    pfad = TABLES_DIR / "tab2_indikatoren.png"
    fig.savefig(pfad, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pfad.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return pfad


def main() -> None:
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    gdf = load_indikatoren()

    abbildung_uebersicht(gdf)
    abbildung_panel(gdf)
    tabelle_indikatoren(gdf)


if __name__ == "__main__":
    main()