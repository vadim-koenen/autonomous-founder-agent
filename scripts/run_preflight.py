#!/usr/bin/env python3
"""Generate one public-metadata MCP/agent preflight report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from founder_agent.preflight import analyze_preflight  # noqa: E402
from founder_agent.preflight_github import preflight_github_repository  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Sanitized preflight input JSON.")
    source.add_argument("--repo-url", help="Public github.com owner/repository URL.")
    parser.add_argument("--output", type=Path, help="Optional report JSON path.")
    args = parser.parse_args()

    if args.input:
        input_path = args.input if args.input.is_absolute() else ROOT / args.input
        report = analyze_preflight(json.loads(input_path.read_text(encoding="utf-8")))
    else:
        report = preflight_github_repository(
            args.repo_url,
            github_token=os.environ.get("GITHUB_TOKEN"),
        )

    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output_path = args.output if args.output.is_absolute() else ROOT / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
