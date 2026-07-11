from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DOWNLOAD_DIR = SCRIPT_DIR / "download"

# gemeinden_basis first: scripts/download/common.py's load_aoi() reads its output
# (data/raw/gemeinden_regen.gpkg) to clip the other downloads to the study area.
SCRIPTS = [
    "download_gemeinden_basis.py",
    "download_Bebauungsdichte.py",
    "download_Grundversorgung.py",
    "download_Haltestellen.py",
    "download_Schutzgebiete.py",
    "download_mastr.py",
]


def main() -> None:
    for name in SCRIPTS:
        script_path = DOWNLOAD_DIR / name
        print(f"\n=== download: {name} ===")
        subprocess.run([sys.executable, str(script_path)], cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
