#!/usr/bin/env python3
"""Build a public, non-contacted prospect queue from the x402 discovery feed."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100&offset=0"
EXCLUDED_HOST_PARTS = ("coingecko", "bitrefill", "zapper", "browserbase")


def fetch_items(timeout: int = 20) -> List[Dict[str, Any]]:
    request = Request(SOURCE_URL, headers={"User-Agent": "AutonomousRevenueOperator/0.3"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed public HTTPS endpoint
        payload = json.load(response)
    return list(payload.get("items", []))


def load_items(input_path: Optional[Path]) -> List[Dict[str, Any]]:
    if input_path is None:
        return fetch_items()
    with input_path.open(encoding="utf-8") as source:
        payload = json.load(source)
    return list(payload.get("items", []))


def build_queue(items: List[Dict[str, Any]], limit: int = 25) -> Dict[str, Any]:
    candidates = []
    seen_hosts = set()
    sorted_items = sorted(
        items,
        key=lambda item: (
            int(item.get("quality", {}).get("l30DaysUniquePayers", 0)),
            -int(item.get("quality", {}).get("l30DaysTotalCalls", 0)),
        ),
    )
    for item in sorted_items:
        resource = str(item.get("resource", ""))
        host = urlparse(resource).netloc.lower()
        if not host or host in seen_hosts or any(part in host for part in EXCLUDED_HOST_PARTS):
            continue
        payers = int(item.get("quality", {}).get("l30DaysUniquePayers", 0))
        calls = int(item.get("quality", {}).get("l30DaysTotalCalls", 0))
        if payers > 50 or calls <= 0:
            continue
        name = str(item.get("serviceName") or host)
        has_name = bool(item.get("serviceName"))
        has_bazaar = bool(item.get("extensions", {}).get("bazaar"))
        if not has_name:
            audit_hook = "Check missing service name plus schema, failure handling, and discovery metadata."
        elif not has_bazaar:
            audit_hook = "Check Bazaar extension completeness, input/output schema, and failure handling."
        else:
            audit_hook = "Run a 25-case launch gate across schema, failures, latency, and discoverability."
        candidates.append(
            {
                "prospect_id": "public-x402-{0:02d}".format(len(candidates) + 1),
                "name": name,
                "public_host": host,
                "public_resource": resource,
                "observed_30d_calls": calls,
                "observed_30d_unique_payers": payers,
                "audit_hook": audit_hook,
                "qualification_note": (
                    "Public counters identify a possible QA conversation, not a defect or purchase intent."
                ),
                "contact_status": "not_contacted",
                "external_action_performed": False,
            }
        )
        seen_hosts.add(host)
        if len(candidates) == limit:
            break

    return {
        "schema_name": "public_prospect_queue",
        "schema_version": "0.3",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_url": SOURCE_URL,
        "purpose": "Public research queue for the Agent Launch QA Sprint.",
        "privacy": "Contains public service metadata only; no personal contact details.",
        "outreach_status": "No messages, emails, posts, or proposals sent.",
        "prospects": candidates,
    }


def render_markdown(queue: Dict[str, Any]) -> str:
    lines = [
        "# Public Prospect Queue",
        "",
        "These are public endpoint operators that may be relevant to the Agent Launch QA Sprint. They are not qualified leads, and low public counters do not prove a defect.",
        "",
        "No messages, emails, posts, or proposals have been sent.",
        "",
        "| # | Public service | Calls | Payers | Public-safe audit hook |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for index, prospect in enumerate(queue["prospects"], start=1):
        lines.append(
            "| {0} | [{1}]({2}) | {3} | {4} | {5} |".format(
                index,
                prospect["name"],
                prospect["public_resource"],
                prospect["observed_30d_calls"],
                prospect["observed_30d_unique_payers"],
                prospect["audit_hook"],
            )
        )
    lines.extend(
        [
            "",
            "Before any outreach, verify a public contact path, the target's current status, and the channel's automation rules. Never request credentials, private URLs, or customer data in a public message.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        help="Use a previously fetched Bazaar JSON response instead of making a network request.",
    )
    args = parser.parse_args()
    queue = build_queue(load_items(args.input))
    if len(queue["prospects"]) < 25:
        raise SystemExit("Public feed produced fewer than 25 eligible prospect records.")
    (ROOT / "data" / "prospect_queue.json").write_text(
        json.dumps(queue, indent=2) + "\n", encoding="utf-8"
    )
    offer_dir = ROOT / "offers" / "agent-launch-qa-sprint"
    offer_dir.mkdir(parents=True, exist_ok=True)
    (offer_dir / "PROSPECTS.md").write_text(render_markdown(queue), encoding="utf-8")
    print("Wrote 25 public prospect records; no outreach performed.")


if __name__ == "__main__":
    main()
