# Datenquellen

Die meisten Datensätze werden von der `download`-Stufe automatisch geladen; einzige
Ausnahme ist der Energie-Atlas-Export, der manuell beigelegt wird. Alle Downloads
beziehen sich auf das Untersuchungsgebiet (AOI) – die zuvor geladenen Gemeindegrenzen
des Landkreises Regen.

| Quelle | Inhalt | Bezug | Lizenz                     |
|---|---|---|----------------------------|
| BKG VG250-EW | Gemeindegrenzen, Einwohnerzahlen | ZIP-Download | dl-de/by-2-0               |
| OpenStreetMap | Gebäude, POI, Haltestellen, Straßennetz | Overpass (osmnx) | ODbL 1.0                   |
| ATKIS Basis-DLM (LDBV) | Siedlungs- und Verkehrsflächen | WFS 2.0 | CC BY 4.0                  |
| Schutzgebiete (LfU) | Naturschutzflächen | WFS 2.0 | CC BY 4.0               |
| Marktstammdatenregister (MaStR) | EE-Anlagen (Solar, Wind, Biomasse, Wasser) | Bulk-Download (`open_mastr`) | dl-de/by-2-0               |
| Energie-Atlas Bayern | PV-Dachpotenzial | **manueller Export (beigelegt)** | CC BY 4.0 |

## BKG VG250-EW — Gemeindegrenzen und Einwohner

*`download_gemeinden_basis.py`*

**Inhalt.** Verwaltungsgebiete 1:250 000 mit Einwohnerzahlen (VG250-EW). Aus der
Ebene `vg250_gem` werden die Gemeinden des Landkreises (AGS-Präfix **09276**,
Geofaktor `GF = 4` = nur Landfläche ohne Gewässeranteile) übernommen und auf die
Spalten `ags`, `name` (GEN), `einwohner` (EWZ) und `flaeche_km2` (KFL) reduziert.
Dieser Datensatz definiert das AOI und liefert den Nenner (Einwohner) für den
EE-Ausbaugrad.

**Bezug.** Automatischer HTTPS-Download des ZIP-Archivs von
`daten.gdz.bkg.bund.de` (Produkt `vg250-ew_ebenen`, UTM32s, GeoPackage). Das Archiv
wird unter `data/raw/_cache/` zwischengespeichert, das GeoPackage direkt aus dem ZIP
gelesen (`/vsizip/`). Die Daten liegen bereits in EPSG:25832 vor.

**Lizenz.** Datenlizenz Deutschland – Namensnennung 2.0 (**dl-de/by-2-0**).
Quellenangabe: *© GeoBasis-DE / BKG \<Jahr\>*.

## OpenStreetMap — Gebäude, POI, Haltestellen, Straßennetz

*`download_Bebauungsdichte.py`, `download_Grundversorgung.py`, `download_Haltestellen.py`*

**Inhalt.** Vier getrennte OSM-Abfragen:

- **Gebäude** (`building=*`, nur Polygone) — Wohnstandort-Proxy für die Netzwerkdistanz.
- **Grundversorgungs-POI** — Supermarkt (`shop=supermarket`), Hausarzt
  (`amenity=doctors` / `healthcare=doctor`), Apotheke (`amenity=pharmacy`) und
  Grundschule (`amenity=school`, gefiltert über `isced:level` und Namensmuster).
- **Haltestellen** — Bus und Bahn, sowohl im alten Schema (`highway=bus_stop`,
  `railway=*`) als auch im aktuellen (`public_transport=*`).
- **Straßennetz** — fahrbares Netz (`network_type="drive"`, vereinfacht) als Graph.

**Bezug.** Automatisch über die **Overpass-API** mittels `osmnx`
(`features_from_polygon` bzw. `graph_from_polygon`). Damit Randgemeinden nicht
abgeschnitten werden, wird das AOI vor der Abfrage aufgeweitet: **3000 m** für POI und
Straßennetz, **1000 m** für Haltestellen. Gebäude werden exakt im AOI abgefragt und
erst in der `ingest`-Stufe zugeschnitten.

**Lizenz.** Open Database License (**ODbL 1.0**). Quellenangabe:
*© OpenStreetMap-Mitwirkende*. Abgeleitete Datenbanken unterliegen der
Share-alike-Pflicht.

## ATKIS Basis-DLM (LDBV) — Siedlungs- und Verkehrsflächen

*`download_Bebauungsdichte.py`*

**Inhalt.** Amtliche Landbedeckung des ATKIS Basis-DLM, getrennt nach Siedlungs- und
Verkehrsflächen. **Siedlung:** Wohnbau-, Industrie-/Gewerbe-, gemischt genutzte sowie
Flächen besonderer funktionaler Prägung. **Verkehr:** Straßen-, Bahn-, Flug- und
Platzflächen (Schiffsverkehr im AOI leer). Basis für Bebauungsdichte und
ÖPNV-Erschließungsgrad.

**Bezug.** Automatisch über den **WFS 2.0** der Bayerischen Vermessungsverwaltung
(`geoservices.bayern.de/wfs/v1/ogc_atkis_basisdlm.cgi`). Je Objektklasse wird ein
`GetFeature`-Request über die AOI-Bounding-Box gestellt und seitenweise (2000 Features
pro Seite) in EPSG:25832 abgeholt.

**Lizenz.** Offene Geodaten Bayern, **CC BY 4.0**. Quellenangabe: *© Bayerische
Vermessungsverwaltung / Landesamt für Digitalisierung, Breitband und Vermessung (LDBV)*.

## Schutzgebiete (LfU Bayern) — Naturschutzflächen

*`download_Schutzgebiete.py`*

**Inhalt.** Neun Schutzgebietskategorien werden abgefragt (u. a. Naturschutzgebiet,
Nationalpark, FFH-Gebiet, Vogelschutzgebiet, Landschaftsschutzgebiet, flächige
Landschaftsbestandteile und Naturdenkmale); leere Kategorien werden übersprungen. In
den Naturschutzflächenanteil gehen sieben flächig belegte Kategorien ein.

**Bezug.** Automatisch über den **WFS 2.0** des Bayerischen Landesamts für Umwelt
(`lfu.bayern.de/gdi/wfs/natur/schutzgebiete`). Jede Kategorie wird über die
AOI-Bounding-Box geladen und anschließend exakt auf das AOI zugeschnitten (`clip`).

**Lizenz.** **CC BY 4.0**. Quellenangabe: *© Bayerisches Landesamt für Umwelt (LfU)*.

## Marktstammdatenregister (MaStR) — EE-Anlagen

*`download_mastr.py`*

**Inhalt.** Alle registrierten Anlagen der Technologien Solar, Wind, Biomasse und
Wasser im Landkreis. Übernommen werden u. a. Betriebsstatus, Brutto-/Nettonennleistung,
Inbetriebnahmedatum, `ArtDerSolaranlage` und der Gemeindeschlüssel. Grundlage für
EE-Ausbaugrad und (gefiltert auf Gebäudesolaranlagen) die PV-Dachausschöpfung.

**Bezug.** Automatischer **Bulk-Download** des Gesamtregisters über das Paket
`open_mastr` (`Mastr().download(method="bulk", date="today")`). Aus der lokalen
SQLite-Datenbank werden per SQL nur Einheiten mit Gemeindeschlüssel-Präfix **09276**
in eine CSV exportiert. In der `ingest`-Stufe werden ausschließlich Anlagen mit
Betriebsstatus *„In Betrieb"* behalten.

**Lizenz.** Datenlizenz Deutschland – Namensnennung 2.0 (**dl-de/by-2-0**).
Quellenangabe: *Marktstammdatenregister, Bundesnetzagentur*.

## Energie-Atlas Bayern — PV-Dachpotenzial

*manueller Export, kein Download-Skript*

**Inhalt.** Je Gemeinde das theoretische PV-Dachflächenpotenzial (Leistung in MWp,
in `ingest` auf kW umgerechnet), zusätzlich installierte Leistung und der im Atlas
hinterlegte Ausbaugrad. Der Potenzialwert bildet den **Nenner** der PV-Dachausschöpfung
und dient zugleich als Referenz für deren Plausibilisierung.

**Bezug.** **Manueller Export** aus dem Energie-Atlas Bayern (kein automatischer
Abruf). Zu Demonstrationszwecken ist der Export beigelegt:

```
data/raw/energieatlas_<zeitstempel>.csv
```

`02_ingest.py` sucht per Glob nach `energieatlas*.csv` und verwendet die neueste
Datei. Der Gemeindeschlüssel steht dort ohne führende `09` (Spalte
`Verwaltungseinheit`) und wird beim Ingest zum vollständigen AGS ergänzt; das
Potenzial ist im Export auf ganze MWp gerundet.

**Lizenz.** **CC BY 4.0**. Quellenangabe: *Energie-Atlas Bayern*.

## Untersuchungsgebiet

Landkreis Regen, Bayern — Kreisschlüssel **09276**. Der räumliche Bezug aller
Auswertungen ist die Gemeindeebene; der AGS-Schlüssel dient als gemeinsamer
Join-Key. Die `ingest`-Stufe prüft, dass alle Quellen dieselben Gemeinden abdecken.
