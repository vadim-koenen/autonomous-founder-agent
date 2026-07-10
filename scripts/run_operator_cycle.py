#!/usr/bin/env python3
"""Run one Autonomous Revenue Operator cycle from repository data."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from founder_agent.operator import run_cycle_from_files  # noqa: E402


def _latest_scan() -> Path:
    scans = sorted((ROOT / "data").glob("opportunity_scan_*.json"))
    if not scans:
        raise SystemExit("No opportunity scan found in data/.")
    return scans[-1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, default=None, help="Opportunity scan JSON path.")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None, help="Cycle date (YYYY-MM-DD).")
    args = parser.parse_args()

    scan_path = args.scan or _latest_scan()
    if not scan_path.is_absolute():
        scan_path = ROOT / scan_path
    state = run_cycle_from_files(ROOT, scan_path, as_of=args.as_of)

    print("Wrote data/operator_state.json and docs/CURRENT_CYCLE.md")
    for experiment in state["current_portfolio"]:
        print("{0}: {1} [{2}]".format(experiment["role"], experiment["offer"], experiment["current_status"]))
    print("Verified net revenue: ${0:.2f}".format(state["revenue"]["net_revenue"]))


if __name__ == "__main__":
    main()
