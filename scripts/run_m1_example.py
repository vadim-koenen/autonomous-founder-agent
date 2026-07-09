#!/usr/bin/env python3
"""Generate the M1 example run artifacts."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from founder_agent.m1 import run_m1_decision_system
from founder_agent.reporting import render_markdown_run, run_to_json


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    run = run_m1_decision_system(as_of=date(2026, 7, 9))
    (DATA_DIR / "example_run.json").write_text(run_to_json(run) + "\n", encoding="utf-8")
    (DATA_DIR / "example_run.md").write_text(render_markdown_run(run), encoding="utf-8")
    print(f"Wrote {DATA_DIR / 'example_run.json'}")
    print(f"Wrote {DATA_DIR / 'example_run.md'}")


if __name__ == "__main__":
    main()
