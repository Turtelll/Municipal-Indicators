# Pipeline

Der Einstiegspunkt ist `main.py`. Die vier Stufen laufen – unabhängig von der
angegebenen Reihenfolge – stets in dieser festen Reihenfolge:

```
download → ingest → analyse → plot
```

## Ausführen

```powershell
# Gesamte Pipeline
python main.py

# Einzelne Stufe(n)
python main.py --stages analyse
python main.py --stages analyse,plot
```

Gültige Stufennamen: `download`, `ingest`, `analyse`, `plot`.

## Was die Stufen tun

1. **download** — lädt Gemeindegrenzen (BKG VG250-EW), OSM-Daten, ATKIS-Flächen,
   Schutzgebiete (WFS) und MaStR-Einheiten. Die Gemeindegrenzen werden zuerst geladen
   und definieren als Untersuchungsgebiet (AOI) den Zuschnitt der übrigen Downloads.
2. **ingest** — reprojiziert alles auf EPSG:25832, repariert Geometrien, schneidet auf
   den Landkreis zu und prüft die AGS-Schlüssel aller Quellen auf Deckungsgleichheit.
3. **analyse** — berechnet die sechs Indikatoren je Gemeinde und schreibt sie nach
   `outputs/tables/indikatoren_regen.gpkg`.
4. **plot** — erzeugt Übersichtskarte, Indikatoren-Panel und Ergebnistabelle.

!!! tip "Ergebnis in QGIS ansehen"
    Das GeoPackage `outputs/tables/indikatoren_regen.gpkg` lässt sich direkt in
    **QGIS** öffnen und dort weiter erkunden (Attributtabelle, eigene
    Klassifizierung).

## Verzeichnisstruktur

```
main.py                    Pipeline-Einstiegspunkt (Stufensteuerung)
requirements.txt
scripts/
  01_download.py           Orchestriert die Download-Skripte
  02_ingest.py             Harmonisierung / Zuschnitt / Validierung
  03_analyse.py            Orchestriert die Analyse-Skripte
  04_plot.py               Karten & Tabellen
  download/                Ein Skript je Datenquelle + common.py
  analyse/                 Ein Skript je Indikator + common.py
data/
  raw/                     Rohdaten (Downloads, beigelegter Energie-Atlas-Export)
  processed/               Harmonisierte Daten (EPSG:25832)
outputs/
  maps/                    Choroplethenkarten (PNG, 300 dpi)
  tables/                  indikatoren_regen.gpkg + Ergebnistabellen
```

Die Verzeichnisse unter `data/` und `outputs/` werden von den Skripten bei Bedarf
automatisch angelegt.
