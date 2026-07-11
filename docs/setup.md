# Installation

## Voraussetzungen

- **Python 3.12** (getestet mit 3.12.10; `pandas~=3.0` erfordert eine aktuelle Version)
- Empfohlen: eine virtuelle Umgebung
- Internetzugang für die Download-Stufe (WFS-Dienste, BKG, MaStR-Bulk-Download)

## Umgebung einrichten

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # PowerShell (Windows)
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
```

!!! note "Warum eine virtuelle Umgebung?"
    Die Abhängigkeiten sind eng gepinnt (u. a. `pandas~=3.0.3`). Eine virtuelle
    Umgebung hält diese Versionen vom übrigen System fern und macht die Umgebung
    exakt aus `requirements.txt` reproduzierbar.

## Nur die Dokumentation bauen

Für die MkDocs-Dokumentation genügen zwei Pakete (bereits in `requirements.txt`
enthalten):

```powershell
pip install mkdocs mkdocs-material
mkdocs serve      # lokale Vorschau unter http://127.0.0.1:8000
```

Die veröffentlichte Fassung wird bei jedem Push auf `main` automatisch über
GitHub Actions gebaut und auf GitHub Pages bereitgestellt.
