#!/usr/bin/env python3
"""Build a free x402 opportunity-pulse sample from public discovery data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources?limit=100&offset=0"

CATEGORY_TERMS = {
    "search_research": ("search", "research", "exa", "tavily", "web"),
    "market_finance_data": ("market", "crypto", "defi", "stock", "trading", "yield", "wallet"),
    "enrichment_identity": ("enrich", "contact", "identity", "resolve", "company", "person"),
    "media_content": ("image", "video", "media", "content", "meme", "pdf"),
    "storage_infrastructure": ("upload", "storage", "browser", "compute", "hosting"),
}


def fetch_payload(timeout: int = 20) -> Dict[str, Any]:
    request = Request(SOURCE_URL, headers={"User-Agent": "AutonomousRevenueOperator/0.3"})
    with urlopen(request, timeout=timeout) as response:  # nosec B310 - fixed public HTTPS endpoint
        return json.load(response)


def load_payload(input_path: Optional[Path]) -> Dict[str, Any]:
    if input_path is None:
        return fetch_payload()
    with input_path.open(encoding="utf-8") as source:
        return json.load(source)


def classify(item: Dict[str, Any]) -> str:
    text = " ".join(
        [
            str(item.get("serviceName", "")),
            str(item.get("description", "")),
            " ".join(str(tag) for tag in item.get("tags", [])),
            str(item.get("resource", "")),
        ]
    ).lower()
    for category, terms in CATEGORY_TERMS.items():
        if any(term in text for term in terms):
            return category
    return "general_utility"


def first_usdc_price(item: Dict[str, Any]) -> float:
    for payment in item.get("accepts", []):
        extra = payment.get("extra", {})
        if extra.get("name") == "USD Coin" and str(payment.get("amount", "")).isdigit():
            return int(payment["amount"]) / 1_000_000
    return 0.0


def build_pulse(payload: Dict[str, Any]) -> Dict[str, Any]:
    groups: Dict[str, Dict[str, Any]] = {}
    for item in payload.get("items", []):
        category = classify(item)
        group = groups.setdefault(
            category,
            {
                "category": category,
                "resource_count": 0,
                "observed_30d_calls": 0,
                "endpoint_payer_counts_summed": 0,
                "unnamed_resources": 0,
                "prices_usd": [],
            },
        )
        group["resource_count"] += 1
        group["observed_30d_calls"] += int(item.get("quality", {}).get("l30DaysTotalCalls", 0))
        group["endpoint_payer_counts_summed"] += int(
            item.get("quality", {}).get("l30DaysUniquePayers", 0)
        )
        group["unnamed_resources"] += int(not bool(item.get("serviceName")))
        price = first_usdc_price(item)
        if price > 0:
            group["prices_usd"].append(price)

    categories: List[Dict[str, Any]] = []
    for group in groups.values():
        prices = group.pop("prices_usd")
        group["median_listed_usdc_price"] = round(median(prices), 6) if prices else None
        group["listing_name_completeness_percent"] = round(
            ((group["resource_count"] - group["unnamed_resources"]) / group["resource_count"]) * 100,
            1,
        )
        categories.append(group)
    categories.sort(key=lambda item: item["observed_30d_calls"], reverse=True)

    return {
        "schema_name": "agent_opportunity_pulse_sample",
        "schema_version": "0.1-sample",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "free_sample_payment_inactive",
        "source": {
            "url": SOURCE_URL,
            "listed_resources": int(payload.get("pagination", {}).get("total", 0)),
            "sample_size": len(payload.get("items", [])),
        },
        "ranking_method": "Categories are ranked by summed public 30-day call counters in the returned sample.",
        "categories": categories,
        "caveats": [
            "The returned sample is not random and cannot be generalized to the entire ecosystem.",
            "Endpoint payer counts are summed and may include the same payer more than once.",
            "Public quality counters are not independently audited revenue.",
            "This sample is evidence for a validation experiment, not investment advice.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        help="Use a previously fetched Bazaar JSON response instead of making a network request.",
    )
    args = parser.parse_args()
    output = build_pulse(load_payload(args.input))
    destination = ROOT / "frontier" / "opportunity-pulse" / "sample.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print("Wrote frontier/opportunity-pulse/sample.json; payment remains inactive.")


if __name__ == "__main__":
    main()
