from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ANALYSE_DIR = SCRIPT_DIR / "analyse"

SCRIPTS = [
    "analyse_Bebauungsdichte.py",
    "analyse_Naturschutzflaechenanteil.py",
    "analyse_Grundversorgung.py",
    "analyse_oepnv_erschliessungsgrad.py",
    "analyse_ee_ausbaugrad.py",
    "analyse_pv_dachauschoepfung.py",
]


def main() -> None:
    for name in SCRIPTS:
        script_path = ANALYSE_DIR / name
        print(f"\n=== analyse: {name} ===")
        subprocess.run([sys.executable, str(script_path)], cwd=PROJECT_ROOT, check=True)


if __name__ == "__main__":
    main()
