# Run the full pipeline:    python main.py
# Run a subset of stages:   python main.py --stages analyse
#                            python main.py --stages analyse,plot
# Valid stage names: download, ingest, analyse, plot (run in that order regardless of list order)
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

SCRIPTS_DIR = PROJECT_ROOT / "scripts"

STAGES = {
    "download": SCRIPTS_DIR / "01_download.py",
    "ingest": SCRIPTS_DIR / "02_ingest.py",
    "analyse": SCRIPTS_DIR / "03_analyse.py",
    "plot": SCRIPTS_DIR / "04_plot.py",
}


def run_stage(name: str) -> None:
    script_path = STAGES[name]
    if not script_path.exists():
        print(f"\n=== {name}: skipping ({script_path.name} not yet implemented) ===")
        return
    print(f"\n=== stage: {name} ===")
    subprocess.run([sys.executable, str(script_path)], cwd=PROJECT_ROOT, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the municipal-indicators pipeline.")
    parser.add_argument(
        "--stages",
        default=",".join(STAGES),
        help=f"Comma-separated subset of {{{','.join(STAGES)}}} to run (default: all, in order).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    requested = {s.strip() for s in args.stages.split(",") if s.strip()}
    unknown = requested - STAGES.keys()
    if unknown:
        raise SystemExit(f"Unknown stage(s): {', '.join(sorted(unknown))}. Valid: {', '.join(STAGES)}")
    for name in STAGES:
        if name in requested:
            run_stage(name)


if __name__ == "__main__":
    main()
