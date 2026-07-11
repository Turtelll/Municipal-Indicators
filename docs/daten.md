# Datenquellen

Die meisten Datensätze werden von der `download`-Stufe automatisch geladen.

| Quelle | Inhalt | Bezug |
|---|---|---|
| BKG VG250-EW | Gemeindegrenzen, Einwohnerzahlen | automatischer Download |
| OpenStreetMap | Gebäude, POI, Haltestellen, Straßennetz | automatischer Download |
| ATKIS (WFS) | Siedlungs- und Verkehrsflächen | automatischer Download |
| Schutzgebiete (WFS) | Naturschutzflächen | automatischer Download |
| Marktstammdatenregister (MaStR) | EE-Anlagen (Solar, Wind, Biomasse, Wasser) | automatischer Bulk-Download |
| Energie-Atlas Bayern | PV-Dachpotenzial | **manueller Export (beigelegt)** |

## Energie-Atlas-Export

Der Export des **Energie-Atlas Bayern** hat kein Download-Skript. Zu
Demonstrationszwecken ist dieser Export dem Projekt beigelegt und liegt unter:

```
data/raw/energieatlas_<zeitstempel>.csv
```

`02_ingest.py` sucht per Glob nach `energieatlas*.csv` und verwendet die neueste
Datei.

## Untersuchungsgebiet

Landkreis Regen, Bayern — Kreisschlüssel **09276**. Der räumliche Bezug aller
Auswertungen ist die Gemeindeebene; der AGS-Schlüssel dient als gemeinsamer
Join-Key. Die `ingest`-Stufe prüft, dass alle Quellen dieselben Gemeinden abdecken.
