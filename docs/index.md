# Municipal-Indicators

Reproduzierbare Berechnung kommunaler Nachhaltigkeitsindikatoren für den
**Landkreis Regen** (Kreisschlüssel `09276`, Bayern).

Die Pipeline lädt offene Geo- und Fachdaten herunter, harmonisiert sie auf ein
gemeinsames Koordinatensystem (**EPSG:25832 / UTM 32N**) und berechnet je Gemeinde
sechs Indikatoren, aus denen Choroplethenkarten und Tabellen für den Bericht
erzeugt werden.

## Auf einen Blick

- **Untersuchungsgebiet:** Landkreis Regen, Bayern (AGS-Präfix `09276`)
- **Räumliche Ebene:** Gemeinde (AGS als gemeinsamer Join-Key)
- **Koordinatensystem:** EPSG:25832 (UTM 32N)
- **Ablauf:** `download → ingest → analyse → plot`

## Inhalt

- [Installation](setup.md) — Umgebung einrichten und Abhängigkeiten installieren
- [Pipeline](pipeline.md) — die vier Stufen ausführen
- [Indikatoren](indikatoren.md) — was berechnet wird
- [Datenquellen](daten.md) — automatische Downloads und der beigelegte Energie-Atlas-Export
