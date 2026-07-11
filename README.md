# Municipal-Indicators

Reproduzierbare Berechnung kommunaler Nachhaltigkeits­indikatoren für den
**Landkreis Regen** (Kreisschlüssel `09276`, Bayern). Die Pipeline lädt offene
Geo- und Fachdaten herunter, harmonisiert sie auf ein gemeinsames Koordinaten­system
(**EPSG:25832 / UTM 32N**) und berechnet je Gemeinde sechs Indikatoren, aus denen
Choroplethen­karten und Tabellen für den Bericht erzeugt werden.

## Indikatoren

| Indikator | Einheit | Quelle |
|---|---|---|
| Bebauungsdichte | % | OSM-Gebäude, ATKIS-Siedlungsfläche |
| Naturschutzflächenanteil | % | Schutzgebiete (WFS) |
| Ø Netzwerkdistanz Grundversorgung | m | OSM-POI, OSM-Straßennetz |
| ÖPNV-Erschließungsgrad | % | OSM-Haltestellen |
| EE-Ausbaugrad | kW/EW | Marktstammdatenregister (MaStR) |
| Ausschöpfung PV-Dachpotenzial | % | Energie-Atlas Bayern, MaStR |

## Voraussetzungen

- **Python 3.12** (getestet mit 3.12.10; `pandas~=3.0` erfordert eine aktuelle Version)
- Empfohlen: eine virtuelle Umgebung
- Internetzugang für die Download-Stufe (WFS-Dienste, BKG, MaStR-Bulk-Download)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell (Windows)
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
```

## Datenquellen

Die meisten Datensätze werden von der `download`-Stufe automatisch geladen.
**Eine Ausnahme:** der Export des **Energie-Atlas Bayern** hat kein Download-Skript.
Zu Demonstrationszwecken ist dieser Export dem Projekt beigelegt und liegt unter:

```
data/raw/energieatlas_<zeitstempel>.csv
```

`02_ingest.py` sucht per Glob nach `energieatlas*.csv` und verwendet die neueste Datei.

## Pipeline ausführen

Der Einstiegspunkt ist `main.py`. Die vier Stufen laufen unabhängig von der
angegebenen Reihenfolge stets in dieser festen Reihenfolge:

```
download → ingest → analyse → plot
```

```powershell
# Gesamte Pipeline
python main.py

# Einzelne Stufe(n)
python main.py --stages analyse
python main.py --stages analyse,plot
```

Gültige Stufennamen: `download`, `ingest`, `analyse`, `plot`.

### Was die Stufen tun

1. **download:** lädt Gemeindegrenzen (BKG VG250-EW), OSM-Daten, ATKIS-Flächen,
   Schutzgebiete (WFS) und MaStR-Einheiten. Die Gemeindegrenzen werden zuerst geladen
   und definieren als Untersuchungsgebiet (AOI) den Zuschnitt der übrigen Downloads.
2. **ingest:** reprojiziert alles auf EPSG:25832, repariert Geometrien, schneidet auf
   den Landkreis zu und prüft die AGS-Schlüssel aller Quellen auf Deckungsgleichheit.
3. **analyse:** berechnet die sechs Indikatoren je Gemeinde und schreibt sie nach
   `outputs/tables/indikatoren_regen.gpkg`. Dieses GeoPackage lässt sich direkt in
   **QGIS** öffnen und dort weiter erkunden (Attributtabelle, eigene Klassifizierung).
4. **plot:** erzeugt Übersichtskarte, Indikatoren-Panel und Ergebnistabelle.

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
  raw/                     Rohdaten (Downloads, manueller Energie-Atlas-Export)
  processed/               Harmonisierte Daten (EPSG:25832)
outputs/
  maps/                    Choroplethenkarten (PNG, 300 dpi)
  tables/                  indikatoren_regen.gpkg + Ergebnistabellen
```

Die Verzeichnisse unter `data/` und `outputs/` werden von den Skripten bei Bedarf
automatisch angelegt.

## Untersuchungsgebiet

Landkreis Regen, Bayern — Kreisschlüssel **09276**. Der räumliche Bezug aller
Auswertungen ist die Gemeindeebene (AGS-Schlüssel als gemeinsamer Join-Key).
