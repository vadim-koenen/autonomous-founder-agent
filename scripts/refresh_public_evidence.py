#!/usr/bin/env python3
"""Refresh structured public evidence that has a stable unauthenticated API."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
X402_URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100&offset=0"


def _latest_scan() -> Path:
    scans = sorted((ROOT / "data").glob("opportunity_scan_*.json"))
    if not scans:
        raise SystemExit("No opportunity scan found in data/.")
    return scans[-1]


def snapshot_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload.get("items", [])
    return {
        "listed_resources": int(payload.get("pagination", {}).get("total", len(items))),
        "sample_size": len(items),
        "sample_calls": sum(int(item.get("quality", {}).get("l30DaysTotalCalls", 0)) for item in items),
        "sample_unnamed": sum(1 for item in items if not item.get("serviceName")),
        "sample_low_payer_entries": sum(
            1 for item in items if int(item.get("quality", {}).get("l30DaysUniquePayers", 0)) <= 20
        ),
    }


def fetch_x402_snapshot(timeout: int = 20) -> Dict[str, Any]:
    request = Request(X402_URL, headers={"User-Agent": "AutonomousRevenueOperator/0.3"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed public HTTPS endpoint
        return snapshot_from_payload(json.load(response))


def load_snapshot(input_path: Optional[Path]) -> Dict[str, Any]:
    if input_path is None:
        return fetch_x402_snapshot()
    with input_path.open(encoding="utf-8") as source:
        return snapshot_from_payload(json.load(source))


def refresh(scan_path: Path, snapshot: Optional[Dict[str, Any]] = None) -> bool:
    scan = json.loads(scan_path.read_text(encoding="utf-8"))
    snapshot = snapshot or fetch_x402_snapshot()
    changed = False
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    for evidence in scan.get("evidence", []):
        if evidence.get("evidence_id") != "ev-x402-live-scan":
            continue
        if evidence.get("signals") != snapshot:
            changed = True
        evidence["signals"] = snapshot
        evidence["observed_at"] = observed_at
        evidence["summary"] = (
            "The public feed returned {listed_resources:,} resources. In the first {sample_size} returned "
            "entries, quality fields totaled {sample_calls:,} calls, {sample_unnamed} entries lacked service "
            "names, and {sample_low_payer_entries} reported 20 or fewer unique payers."
        ).format(**snapshot)
        break
    else:
        raise ValueError("ev-x402-live-scan is missing from the opportunity scan")

    scan["observed_at"] = observed_at
    scan_path.write_text(json.dumps(scan, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", type=Path, default=None)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Use a previously fetched Bazaar JSON response instead of making a network request.",
    )
    args = parser.parse_args()
    scan_path = args.scan or _latest_scan()
    if not scan_path.is_absolute():
        scan_path = ROOT / scan_path
    changed = refresh(scan_path, snapshot=load_snapshot(args.input))
    print("Refreshed public x402 evidence; metrics changed={0}".format(str(changed).lower()))


if __name__ == "__main__":
    main()
