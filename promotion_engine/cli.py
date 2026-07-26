"""Command-line interface for the promotion engine."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .apollo import ApolloClient
from .config import load_config
from .engine import PromotionEngine
from .store import PromotionStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = PROJECT_ROOT / ".promotion-private"
DEFAULT_DB = PRIVATE_ROOT / "promotion.sqlite3"


def _private_output(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    private = PRIVATE_ROOT.resolve()
    if private != resolved and private not in resolved.parents:
        raise ValueError("PII-bearing outputs must remain under {0}".format(PRIVATE_ROOT))
    return resolved


def _private_database(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    project = PROJECT_ROOT.resolve()
    private = PRIVATE_ROOT.resolve()
    if project in resolved.parents and private not in resolved.parents:
        raise ValueError("promotion databases inside the repository must use {0}".format(PRIVATE_ROOT))
    return resolved


def _engine(db_path: Path, config_path: Path) -> PromotionEngine:
    store = PromotionStore(_private_database(db_path))
    return PromotionEngine(
        load_config(config_path),
        store,
        ledger_path=PROJECT_ROOT / "data/revenue_ledger.json",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed multichannel promotion operator for vadimkoenen.com"
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "config/promotion_engine.json"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")

    import_cmd = commands.add_parser("import-apollo")
    import_cmd.add_argument("--csv", type=Path, required=True)
    commands.add_parser("qualify")

    draft_cmd = commands.add_parser("draft")
    draft_cmd.add_argument(
        "--channel", choices=("apollo_email", "linkedin_manual_task"), required=True
    )

    approve_cmd = commands.add_parser("approve")
    approve_group = approve_cmd.add_mutually_exclusive_group(required=True)
    approve_group.add_argument("--draft-id")
    approve_group.add_argument("--all", action="store_true")
    approve_cmd.add_argument("--reviewer", required=True)

    review_cmd = commands.add_parser("review-queue")
    review_cmd.add_argument("--out", type=Path)

    export_cmd = commands.add_parser("export-apollo")
    export_cmd.add_argument("--out", type=Path)

    suppress_cmd = commands.add_parser("suppress")
    suppress_cmd.add_argument("--email", required=True)
    suppress_cmd.add_argument(
        "--reason",
        choices=("unsubscribed", "bounced", "do_not_contact", "customer", "active_opportunity"),
        required=True,
    )
    suppress_cmd.add_argument("--evidence", required=True)

    event_cmd = commands.add_parser("record-event")
    event_cmd.add_argument("--prospect-id", required=True)
    event_cmd.add_argument(
        "--event",
        choices=(
            "sent",
            "delivered",
            "bounced",
            "unsubscribed",
            "replied",
            "meeting_booked",
            "systems_review_requested",
            "checkout_opened",
            "customer_verified",
        ),
        required=True,
    )
    event_cmd.add_argument("--channel", required=True)
    event_cmd.add_argument("--evidence", required=True)
    event_cmd.add_argument("--occurred-at", required=True)

    commands.add_parser("report")
    commands.add_parser("apollo-health")
    search_cmd = commands.add_parser("apollo-search")
    search_cmd.add_argument("--filters-json", type=Path, required=True)
    search_cmd.add_argument("--out", type=Path, required=True)
    enrich_cmd = commands.add_parser("apollo-enrich")
    enrich_cmd.add_argument("--filters-json", type=Path, required=True)
    enrich_cmd.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"apollo-health", "apollo-search", "apollo-enrich"}:
        client = ApolloClient(grants_path=PROJECT_ROOT / "config/capability_grants.json")
        if args.command == "apollo-health":
            result = client.health()
            print(json.dumps({"ok": bool(result), "credential_present": True}, indent=2))
            return 0
        filters = json.loads(args.filters_json.read_text(encoding="utf-8"))
        result = (
            client.search_people(filters)
            if args.command == "apollo-search"
            else client.enrich_person(filters)
        )
        output = _private_output(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        count = len(result.get("people", result.get("contacts", [])))
        print(json.dumps({"records": count, "private_output": output.name}, indent=2))
        return 0

    engine = _engine(args.db, args.config)
    try:
        result: Dict[str, Any]
        if args.command == "init":
            result = {"initialized": True, "database": Path(args.db).name}
        elif args.command == "import-apollo":
            result = engine.import_apollo_csv(args.csv)
        elif args.command == "qualify":
            result = engine.qualify()
        elif args.command == "draft":
            result = engine.create_drafts(args.channel)
        elif args.command == "approve":
            result = {
                "approved": engine.approve(
                    args.reviewer, draft_id=args.draft_id, approve_all=args.all
                )
            }
        elif args.command == "review-queue":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output = _private_output(
                args.out or PRIVATE_ROOT / "exports" / "review_queue_{0}.csv".format(stamp)
            )
            result = engine.export_review_queue(output)
        elif args.command == "export-apollo":
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            output = _private_output(
                args.out or PRIVATE_ROOT / "exports" / "apollo_reviewed_{0}.csv".format(stamp)
            )
            result = engine.export_apollo(output)
            result["private_output"] = output.name
        elif args.command == "suppress":
            engine.suppress(args.email, args.reason, args.evidence)
            result = {"suppressed": 1, "reason": args.reason}
        elif args.command == "record-event":
            result = {
                "event_id": engine.record_event(
                    args.prospect_id,
                    args.event,
                    args.channel,
                    args.evidence,
                    args.occurred_at,
                )
            }
        elif args.command == "report":
            result = engine.report()
        else:
            raise ValueError("unsupported command")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        engine.store.close()


if __name__ == "__main__":
    raise SystemExit(main())
