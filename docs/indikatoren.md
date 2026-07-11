# Indikatoren

Je Gemeinde werden sechs Indikatoren berechnet. Jeder wird von einem eigenen Skript
unter `scripts/analyse/` erzeugt und in `outputs/tables/indikatoren_regen.gpkg`
zusammengeführt.

| Indikator | Einheit | Quelle | Spalte im GeoPackage |
|---|---|---|---|
| Bebauungsdichte | % | OSM-Gebäude, ATKIS-Siedlungsfläche | `bebauungsdichte` |
| Naturschutzflächenanteil | % | Schutzgebiete (WFS) | `naturschutzflaechenanteil` |
| Ø Netzwerkdistanz Grundversorgung | m | OSM-POI, OSM-Straßennetz | `netzwerkdistanz_grundversorgung` |
| ÖPNV-Erschließungsgrad | % | OSM-Haltestellen | `oepnv_erschliessungsgrad_prozent` |
| EE-Ausbaugrad | kW/EW | Marktstammdatenregister (MaStR) | `ee_ausbaugrad_kw_ew` |
| Ausschöpfung PV-Dachpotenzial | % | Energie-Atlas Bayern, MaStR | `pv_dach_ausschoepfung_prozent` |

!!! note "Bebauungsdichte"
    Der Indikator trägt aus fachlichen Gründen den Namen *Bebauungsdichte*, obwohl
    rechnerisch ein Flächenanteil bestimmt wird.

## Darstellung

Die Stufe `plot` erzeugt aus dem GeoPackage:

- eine **Übersichtskarte** der Gemeinden,
- ein **Panel** mit je einer Choroplethenkarte pro Indikator (Quantilklassen),
- eine **Ergebnistabelle** inklusive Landkreis-Median.

Die Ausgaben liegen als PNG (300 dpi) unter `outputs/maps/` bzw. `outputs/tables/`.
