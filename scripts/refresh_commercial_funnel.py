#!/usr/bin/env python3
"""Refresh public inquiry metrics without treating attention as revenue."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "commercial_funnel.json"
ISSUES_URL = (
    "https://api.github.com/repos/vadim-koenen/autonomous-founder-agent/issues"
    "?state=all&labels=revenue-experiment&per_page=100"
)


def load_issues(path: Path | None) -> list[dict[str, Any]]:
    if path is not None:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        request = Request(
            ISSUES_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "autonomous-founder-agent-funnel/0.1",
            },
        )
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)

    if not isinstance(payload, list):
        raise ValueError("GitHub issues response must be a list")
    return [item for item in payload if isinstance(item, dict)]


def _label_names(issue: dict[str, Any]) -> set[str]:
    labels: Iterable[Any] = issue.get("labels", [])
    return {
        str(item.get("name", "")).strip()
        for item in labels
        if isinstance(item, dict) and item.get("name")
    }


def build_funnel(issues: list[dict[str, Any]], *, as_of: date) -> dict[str, Any]:
    interest_issues = [
        issue
        for issue in issues
        if "pull_request" not in issue and "revenue-experiment" in _label_names(issue)
    ]
    qa_issues = [
        issue
        for issue in interest_issues
        if "qa sprint" in (str(issue.get("title", "")) + " " + str(issue.get("body", ""))).lower()
    ]

    return {
        "schema_name": "autonomous_revenue_operator_commercial_funnel",
        "schema_version": "0.1",
        "as_of": as_of.isoformat(),
        "source": {
            "channel": "github_issues",
            "url": "https://github.com/vadim-koenen/autonomous-founder-agent/issues",
            "filter": "label:revenue-experiment",
        },
        "metrics": {
            "public_interest_issues": len(interest_issues),
            "open_interest_issues": sum(issue.get("state") == "open" for issue in interest_issues),
            "qa_sprint_interest_issues": len(qa_issues),
        },
        "revenue_effect": "none",
        "notes": [
            "Interest issues are public demand signals, not customers or revenue.",
            "Only the verified transaction ledger can increase revenue.",
            "No issue body, username, email address, or buyer personal information is stored here.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional saved GitHub issues response.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else ROOT / args.output
    input_path = args.input
    if input_path is not None and not input_path.is_absolute():
        input_path = ROOT / input_path

    try:
        issues = load_issues(input_path)
    except Exception as exc:
        if output.exists() and input_path is None:
            print(f"Commercial funnel refresh skipped: {exc}", file=sys.stderr)
            return
        raise

    output.write_text(
        json.dumps(build_funnel(issues, as_of=args.as_of), indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
