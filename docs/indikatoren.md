# Indikatoren

Je Gemeinde werden sechs Indikatoren berechnet. Jeder wird von einem eigenen Skript
unter `scripts/analyse/` erzeugt und in `outputs/tables/indikatoren_regen.gpkg`
zusammengeführt.

| Indikator | Einheit | Quelle | Spalte im GeoPackage |
|---|---|---|---|
| Bebauungsdichte | % | ATKIS Basis-DLM (Siedlungs- und Verkehrsfläche), VG250-EW (Gemeindefläche) | `bebauungsdichte` |
| Naturschutzflächenanteil | % | LfU Bayern – Schutzgebiete (WFS), VG250-EW (Gemeindefläche) | `naturschutzflaechenanteil` |
| Ø Netzwerkdistanz Grundversorgung | m | OSM-Gebäude, OSM-POI, OSM-Straßennetz | `netzwerkdistanz_grundversorgung` |
| ÖPNV-Erschließungsgrad | % | OSM-Haltestellen, ATKIS Basis-DLM (Siedlungsfläche) | `oepnv_erschliessungsgrad_prozent` |
| EE-Ausbaugrad | kW/EW | Marktstammdatenregister (MaStR), VG250-EW (Einwohner) | `ee_ausbaugrad_kw_ew` |
| Ausschöpfung PV-Dachpotenzial | % | Energie-Atlas Bayern, MaStR | `pv_dach_ausschoepfung_prozent` |

!!! note "Bebauungsdichte"
    Der Indikator trägt aus fachlichen Gründen den Namen *Bebauungsdichte*, obwohl
    rechnerisch ein Flächenanteil bestimmt wird.

## Berechnung

Jedes Skript lädt zunächst die Gemeindegrenzen (`load_boundaries`), rechnet alles in
**EPSG:25832** (metrisch, Flächen in m², Distanzen in m) und schreibt am Ende seine
Spalten über `merge_indicator` in das gemeinsame GeoPackage. Zusätzlich zum Kennwert
speichert jedes Skript einen **Perzentilrang** (`…_perzentil`), der die Gemeinde
innerhalb des Landkreises einordnet.

Drei der Indikatoren sind reine Flächenanteile und teilen sich dieselbe Mechanik:

- **`dissolve_layer`** verschmilzt alle Eingangspolygone zu einer einzigen Geometrie
  (`union_all`). So werden **Überlappungen nicht doppelt gezählt** – etwa eine Straße,
  die durch eine Siedlungsfläche verläuft, oder ein FFH-Gebiet innerhalb eines
  Landschaftsschutzgebiets.
- **`area_by_gemeinde`** verschneidet diese Geometrie mit den Gemeindegrenzen
  (`overlay`, `intersection`), verwirft nicht-polygonale Verschnitt-Splitter und
  summiert die Teilflächen je AGS.

### Bebauungsdichte

`analyse_Bebauungsdichte.py` bildet die Vereinigung aus **ATKIS-Siedlungsfläche** und
**ATKIS-Verkehrsfläche**, löst sie auf und verschneidet sie mit jeder Gemeinde. Der
Wert ist der Anteil an der Gemeindegesamtfläche:

```
bebauungsdichte = (Siedlungs- + Verkehrsfläche) / Gesamtfläche der Gemeinde × 100
```

Die Gesamtfläche ist die Fläche des Gemeindepolygons selbst. Gemeinden mit
Gesamtfläche 0 werden auf `NaN` gesetzt.

### Naturschutzflächenanteil

`analyse_Naturschutzflaechenanteil.py` vereinigt **sieben Schutzgebietskategorien**
(Naturschutzgebiet, Nationalpark, flächiger Landschaftsbestandteil, flächiges
Naturdenkmal, FFH-Gebiet, Vogelschutzgebiet, Landschaftsschutzgebiet), löst sie zu
einer überschneidungsfreien Fläche auf und setzt sie zur Gesamtfläche ins Verhältnis:

```
naturschutzflaechenanteil = geschützte Fläche / Gesamtfläche der Gemeinde × 100
```

### Ø Netzwerkdistanz Grundversorgung

`analyse_Grundversorgung.py` misst die mittlere **Straßennetz-Distanz** (nicht
Luftlinie) vom Wohnstandort zur nächsten Einrichtung der Grundversorgung. Jedes
**Gebäude** steht dabei stellvertretend für einen Wohnstandort.

1. Das OSM-Straßennetz wird als Graph geladen; nur die größte stark
   zusammenhängende Komponente wird verwendet.
2. Für jede der vier Kategorien – **Supermarkt, Hausarzt, Apotheke, Grundschule** –
   werden die POI auf ihre nächsten Netzknoten gelegt. Ein `multi_source_dijkstra`
   auf dem **umgekehrten Graphen** liefert dann von *jedem* Knoten die Distanz zum
   nächstgelegenen POI dieser Kategorie (Kantengewicht = Länge in Metern).
3. Jedes Gebäude wird auf seinen nächsten Netzknoten gelegt und per Verschneidung
   einer Gemeinde zugeordnet.
4. Je Gebäude wird über die **vier Kategorien gemittelt**; Gebäude ohne erreichbare
   Kategorie fallen heraus.
5. Der Gemeindewert ist der **Mittelwert über alle Gebäude** der Gemeinde (in Metern).

### ÖPNV-Erschließungsgrad

`analyse_oepnv_erschliessungsgrad.py` legt um jede **Haltestelle** einen Puffer von
**600 m** (Einzugsbereich), vereinigt diese Puffer und verschneidet sie mit der
aufgelösten Siedlungsfläche. Der Indikator ist der so erschlossene Anteil:

```
oepnv_erschliessungsgrad = Siedlungsfläche im 600-m-Einzugsbereich / gesamte Siedlungsfläche × 100
```

!!! note "Randgemeinden"
    Die Haltestellen werden mit 1000-m-Puffer über die Kreisgrenze hinaus geladen und
    bewusst **nicht** auf den Landkreis zugeschnitten – sonst würden Randgemeinden
    durch Haltestellen jenseits der Grenze künstlich schlechter dastehen.

### EE-Ausbaugrad

`analyse_ee_ausbaugrad.py` summiert die **Nettonennleistung** aller im MaStR als
*„In Betrieb“* geführten EE-Anlagen (Solar, Wind, Biomasse, Wasser) je Gemeinde und
normiert sie auf die Einwohnerzahl:

```
ee_ausbaugrad = installierte EE-Leistung [kW] / Einwohner
```

Gemeinden ohne Anlagen erhalten 0 kW; eine Einwohnerzahl ≤ 0 gilt als Fehler.

### Ausschöpfung PV-Dachpotenzial

`analyse_pv_dachauschoepfung.py` setzt die installierte **Dach-PV-Leistung** ins
Verhältnis zum theoretischen Dachpotenzial. Im Zähler werden aus dem MaStR nur
**Gebäudesolaranlagen** gezählt (Freiflächen-, Balkon- und sonstige Anlagen sind
ausgeschlossen); der Nenner stammt aus dem **Energie-Atlas Bayern**:

```
pv_dach_ausschoepfung = installierte Dach-PV [kW] / Dachpotenzial [kW] × 100
```

Zur Plausibilisierung vergleicht das Skript das Ergebnis mit dem im Energie-Atlas
hinterlegten Ausbaugrad (Korrelation, mittlere Abweichung); der eigene Zähler ist
dabei in der Regel aktueller.

## Darstellung

Die Stufe `plot` erzeugt aus dem GeoPackage:

- eine **Übersichtskarte** der Gemeinden,
- ein **Panel** mit je einer Choroplethenkarte pro Indikator (Quantilklassen),
- eine **Ergebnistabelle** inklusive Landkreis-Median.

Die Ausgaben liegen als PNG (300 dpi) unter `outputs/maps/` bzw. `outputs/tables/`.
