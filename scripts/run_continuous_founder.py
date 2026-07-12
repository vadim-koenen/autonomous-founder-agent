#!/usr/bin/env python3
"""Run one bounded M4 discovery, decision, and execution cycle."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from founder_agent.discovery import JsonFetcher, scan_sources  # noqa: E402
from founder_agent.execution import (  # noqa: E402
    IssueTransport,
    append_execution_log,
    execute_bounded_action,
    respond_to_inbound_interest,
)
from founder_agent.operator import (  # noqa: E402
    merge_discovery_into_scan,
    run_operating_cycle,
    write_cycle_outputs,
)
from founder_agent.runtime_budget import BudgetTracker, RuntimeBudget  # noqa: E402
from founder_agent.synthesis import ModelCallable, synthesize_opportunities  # noqa: E402


def _load_json(path: Path, default: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
    if not path.exists() and default is not None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _latest_scan(root: Path) -> Path:
    scans = sorted((root / "data").glob("opportunity_scan_*.json"))
    if not scans:
        raise RuntimeError("No base opportunity scan exists in data/.")
    return scans[-1]


def _model_is_temporarily_unavailable(
    model: str,
    access_state: Mapping[str, Any],
    observed_at: datetime,
) -> bool:
    record = access_state.get("models", {}).get(model, {})
    if not isinstance(record, Mapping) or record.get("status") != "unavailable":
        return False
    try:
        retry_after = datetime.fromisoformat(
            str(record.get("retry_after", "")).replace("Z", "+00:00")
        )
    except ValueError:
        return False
    if retry_after.tzinfo is None:
        retry_after = retry_after.replace(tzinfo=timezone.utc)
    return observed_at < retry_after


def _select_model(
    snapshot: Mapping[str, Any],
    budget_config: Mapping[str, Any],
    access_state: Optional[Mapping[str, Any]] = None,
    observed_at: Optional[datetime] = None,
) -> str:
    now = observed_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    model_access = access_state or {}
    available = set()
    for source in snapshot.get("sources", []):
        if source.get("source_id") != "github_models_catalog" or source.get("status") not in {"ok", "stale"}:
            continue
        available.update(str(item.get("id")) for item in source.get("items", []) if item.get("id"))
    for model in budget_config.get("model_preference", []):
        if model in available and not _model_is_temporarily_unavailable(
            str(model), model_access, now
        ):
            return str(model)
    return str(budget_config["model"])


def _update_model_access_state(
    access_state: Mapping[str, Any],
    synthesis: Mapping[str, Any],
    observed_at: datetime,
) -> Dict[str, Any]:
    models = {
        str(model): dict(record)
        for model, record in access_state.get("models", {}).items()
        if isinstance(record, Mapping)
    }
    state: Dict[str, Any] = {
        "schema_name": "autonomous_founder_model_access_state",
        "schema_version": "0.4",
        "updated_at": observed_at.isoformat(),
        "models": models,
    }
    model = str(synthesis.get("model", ""))
    if not model:
        return state
    error = str(synthesis.get("model_error", ""))
    record: Dict[str, Any] = {
        "last_checked_at": observed_at.isoformat(),
        "last_error": error[:300],
    }
    if synthesis.get("synthesis_mode") == "github_models":
        record.update({"status": "available", "retry_after": ""})
    elif "unavailable model" in error.lower():
        record.update(
            {
                "status": "unavailable",
                "retry_after": (observed_at + timedelta(days=7)).isoformat(),
            }
        )
    else:
        record.update({"status": "transient_error", "retry_after": ""})
    models[model] = record
    return state


def _markdown_text(value: Any) -> str:
    return (
        str(value or "")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "'")
    )


def render_discovery_markdown(
    snapshot: Mapping[str, Any],
    synthesis: Mapping[str, Any],
    execution_records: list[Mapping[str, Any]],
    budget: Mapping[str, Any],
) -> str:
    summary = snapshot.get("run_summary", {})
    lines = [
        "# Autonomous Founder - Latest Discovery",
        "",
        "Observed: {0}".format(_markdown_text(snapshot.get("observed_at"))),
        "",
        "## Cycle Truth",
        "",
        "- Sources attempted: {0}".format(summary.get("sources_attempted", 0)),
        "- Sources healthy: {0}".format(summary.get("sources_ok", 0)),
        "- Sources stale: {0}".format(summary.get("sources_stale", 0)),
        "- Sources failed: {0}".format(summary.get("sources_failed", 0)),
        "- Synthesis mode: {0}".format(_markdown_text(synthesis.get("synthesis_mode"))),
        "- New opportunity hypotheses: {0}".format(len(synthesis.get("new_opportunity_ids", []))),
        "- New channel candidates: {0}".format(len(synthesis.get("new_channel_ids", []))),
        "- Verified revenue effect: none unless separately present in the transaction ledger",
        "",
        "## Rotating Sources",
        "",
        "| Source | Signal | Status | Observation |",
        "| --- | --- | --- | --- |",
    ]
    for source in snapshot.get("sources", []):
        lines.append(
            "| {0} | {1} | {2} | {3} |".format(
                _markdown_text(source.get("name")),
                _markdown_text(source.get("signal_type")),
                _markdown_text(source.get("status")),
                _markdown_text(source.get("summary")),
            )
        )
    lines.extend(["", "## Newly Synthesized Opportunities", ""])
    new_ids = set(synthesis.get("new_opportunity_ids", []))
    new_opportunities = [
        item for item in synthesis.get("opportunities", []) if item.get("opportunity_id") in new_ids
    ]
    if new_opportunities:
        lines.extend(
            [
                "- **{0}**: {1} Buyer: {2}.".format(
                    _markdown_text(item.get("name")),
                    _markdown_text(item.get("offer")),
                    _markdown_text(item.get("intended_buyer")),
                )
                for item in new_opportunities
            ]
        )
    else:
        lines.append("- No new hypothesis passed validation in this cycle; prior candidates remain eligible.")
    lines.extend(["", "## Executed Scope", ""])
    for record in execution_records:
        lines.append(
            "- {0}: {1}. {2}".format(
                _markdown_text(record.get("action_type")),
                _markdown_text(record.get("status")),
                _markdown_text(record.get("reason")),
            )
        )
    lines.extend(["", "## Budget", ""])
    for resource, used in budget.get("used", {}).items():
        lines.append(
            "- {0}: {1} used / {2} allowed".format(
                _markdown_text(resource), used, budget.get("limits", {}).get(resource, 0)
            )
        )
    lines.extend(
        [
            "",
            "Public source text and model output are untrusted inputs. Typed validation, evidence references, channel access, capability grants, and per-cycle budgets govern execution.",
            "",
        ]
    )
    return "\n".join(lines)


def _update_manifest(
    root: Path,
    state: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    synthesis: Mapping[str, Any],
) -> None:
    path = root / "AGENT_MANIFEST.json"
    manifest = dict(_load_json(path))
    checkout = _load_json(root / "site" / "checkout-config.json", {})
    checkout_url = str(checkout.get("checkout_url", ""))
    parsed_checkout = urlparse(checkout_url)
    checkout_active = (
        checkout.get("status") == "active"
        and checkout.get("experiment_id") == "opp-agent-launch-qa"
        and checkout.get("configured_by_human") is True
        and checkout.get("provider") in {"stripe", "contra", "lemon_squeezy"}
        and parsed_checkout.scheme == "https"
        and bool(parsed_checkout.hostname)
    )
    names = {
        item.get("opportunity_id"): item.get("name")
        for item in state.get("ranked_opportunities", [])
    }
    manifest["schema_version"] = "0.4"
    manifest["operator"] = {
        "status": "continuous_discovery_and_bounded_execution_active",
        "cycle_schedule": "17 */6 * * * UTC",
        "model": synthesis.get("model"),
        "last_synthesis_mode": synthesis.get("synthesis_mode"),
        "last_discovery_run_id": snapshot.get("run_id"),
        "state_url": "https://vadim-koenen.github.io/autonomous-founder-agent/data/operator_state.json",
        "discovery_snapshot_url": "https://vadim-koenen.github.io/autonomous-founder-agent/data/discovery_snapshot.json",
        "opportunity_pool_url": "https://vadim-koenen.github.io/autonomous-founder-agent/data/discovered_opportunities.json",
        "execution_log_url": "https://vadim-koenen.github.io/autonomous-founder-agent/data/execution_log.json",
        "channel_registry_url": "https://vadim-koenen.github.io/autonomous-founder-agent/data/channel_registry.json",
        "capability_policy_url": "https://vadim-koenen.github.io/autonomous-founder-agent/config/capability_grants.json",
        "decision_policy": "Continuously rotate current public sources, validate model-proposed opportunities against evidence, rerank incumbents and challengers, and execute only through connected capabilities within per-cycle budgets.",
    }
    manifest["current_portfolio"] = [
        {
            "role": item.get("role"),
            "opportunity_id": item.get("opportunity_id"),
            "name": names.get(item.get("opportunity_id"), item.get("offer")),
            "status": item.get("current_status"),
            "buyer": item.get("intended_buyer"),
            "offer": item.get("offer"),
            "price": item.get("price"),
            "discovery": item.get("acquisition_channel"),
            "payment_rail": item.get("payment_rail"),
            "payment_status": (
                "active_public_checkout"
                if checkout_active and item.get("opportunity_id") == "opp-agent-launch-qa"
                else "active_only_when_a_public_configured_rail_exists"
            ),
        }
        for item in state.get("current_portfolio", [])
    ]
    manifest["revenue"].update(
        {
            "verified_transactions": state["revenue"]["verified_transactions"],
            "gross_revenue": state["revenue"]["gross_revenue"],
            "net_revenue": state["revenue"]["net_revenue"],
            "physical_form_fund": state["revenue"]["physical_form_fund"],
            "owner_funds_spent": state["owner_funds_spent"],
        }
    )
    currently_enabled = [
        "connected GitHub publishing",
        "up to three replies to qualified inbound project issues per cycle",
    ]
    enable_when_connected = [
        "compliant outbound messaging",
        "marketplace writes",
        "agent-native receipts",
        "verified-revenue reinvestment",
        "collectible minting when selected",
    ]
    if checkout_active:
        currently_enabled.append("human Stripe Payment Link for the full preflight audit")
    else:
        enable_when_connected.append("human checkout")
    manifest["capability_policy"] = {
        "rule": "Missing capabilities constrain execution, never the strategy search.",
        "currently_enabled": currently_enabled,
        "enable_when_connected": enable_when_connected,
    }
    payment_policy = dict(manifest.get("payment_policy", {}))
    payment_policy["active_rails"] = ["stripe_payment_link"] if checkout_active else []
    payment_policy["human_checkout_config_status"] = (
        "active_human_configured_public_stripe_payment_link"
        if checkout_active
        else "pending_human_checkout"
    )
    manifest["payment_policy"] = payment_policy
    manifest["safety"] = {
        "no_private_keys": True,
        "no_api_secrets_in_public_state": True,
        "no_unverified_revenue": True,
        "no_broker_or_trading_api": True,
        "no_strategy_category_lock": True,
        "external_execution_requires_capability_grant": True,
        "human_checkout_connected": checkout_active,
        "owner_funded_spend_enabled": False,
        "wallet_capability_connected": False,
        "marketplace_write_capability_connected": False,
        "nft_mint_capability_connected": False,
    }
    manifest["last_updated"] = state.get("as_of")
    _write_json(path, manifest)


def run_continuous_cycle(
    root: Path = ROOT,
    *,
    run_date: Optional[date] = None,
    observed_at: Optional[datetime] = None,
    github_token: Optional[str] = None,
    fetch_json: Optional[JsonFetcher] = None,
    model_callable: Optional[ModelCallable] = None,
    issue_transport: Optional[IssueTransport] = None,
) -> Dict[str, Any]:
    started_at = time.monotonic()
    now = observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cycle_date = run_date or now.date()
    budget_config = _load_json(root / "config" / "operator_budget.json")
    tracker = BudgetTracker(RuntimeBudget.from_mapping(budget_config))

    previous_snapshot = _load_json(root / "data" / "discovery_snapshot.json", {})
    source_registry = _load_json(root / "data" / "discovery_sources.json")
    scan_kwargs: Dict[str, Any] = {
        "github_token": github_token,
        "observed_at": now,
    }
    if fetch_json is not None:
        scan_kwargs["fetch_json"] = fetch_json
    snapshot = scan_sources(source_registry, previous_snapshot, tracker, **scan_kwargs)

    base_scan = _load_json(_latest_scan(root))
    platform_extensions = _load_json(
        root / "data" / "platform_opportunity_extensions.json", {}
    )
    base_scan = merge_discovery_into_scan(base_scan, platform_extensions)
    product_extensions = _load_json(
        root / "data" / "product_opportunity_extensions.json", {}
    )
    base_scan = merge_discovery_into_scan(base_scan, product_extensions)
    channel_registry = _load_json(root / "data" / "channel_registry.json")
    previous_pool = _load_json(root / "data" / "discovered_opportunities.json", {})
    model_access_path = root / "data" / "model_access_state.json"
    model_access = _load_json(model_access_path, {})
    model_access = _update_model_access_state(model_access, previous_pool, now)
    selected_model = _select_model(snapshot, budget_config, model_access, now)
    synthesis = synthesize_opportunities(
        snapshot,
        base_scan,
        channel_registry,
        previous_pool,
        tracker,
        model=selected_model,
        github_token=github_token,
        model_callable=model_callable,
        observed_at=now,
    )
    model_access = _update_model_access_state(model_access, synthesis, now)
    _write_json(root / "data" / "discovery_snapshot.json", snapshot)
    _write_json(root / "data" / "discovered_opportunities.json", synthesis)
    _write_json(model_access_path, model_access)

    merged_scan = merge_discovery_into_scan(base_scan, synthesis)
    ledger = _load_json(root / "data" / "revenue_ledger.json")
    state_path = root / "data" / "operator_state.json"
    previous_state = _load_json(state_path, {})
    result = run_operating_cycle(
        merged_scan,
        channel_registry,
        ledger,
        previous_state=previous_state,
        as_of=cycle_date,
        replacement_margin=0.35,
        cycle_id="m4-cycle-{0}".format(now.strftime("%Y%m%dT%H%M%SZ")),
    )
    state = write_cycle_outputs(
        result,
        merged_scan,
        ledger,
        root / "data",
        root / "docs",
        previous_state=previous_state,
    )

    previous_log = _load_json(root / "data" / "execution_log.json", {})
    capability_config = _load_json(root / "config" / "capability_grants.json")
    reply_kwargs: Dict[str, Any] = {
        "github_token": github_token,
        "observed_at": now,
    }
    if issue_transport is not None:
        reply_kwargs["transport"] = issue_transport
    inbound_record = respond_to_inbound_interest(capability_config, tracker, **reply_kwargs)
    eligible_ids = {
        item.get("opportunity_id") for item in state.get("current_portfolio", [])
    } | {
        item.get("opportunity_id") for item in state.get("ranked_opportunities", [])[:3]
    }
    publication_record = execute_bounded_action(
        root,
        synthesis,
        snapshot,
        channel_registry,
        tracker,
        eligible_opportunity_ids=sorted(item for item in eligible_ids if item),
        previous_log=previous_log,
        observed_at=now,
    )
    execution_log = append_execution_log(previous_log, inbound_record)
    execution_log = append_execution_log(execution_log, publication_record)
    _write_json(root / "data" / "execution_log.json", execution_log)

    tracker.consume("runtime_minutes", (time.monotonic() - started_at) / 60)

    runtime_state = {
        "schema_name": "autonomous_founder_runtime_state",
        "schema_version": "0.4",
        "cycle_id": result.cycle_id,
        "observed_at": now.isoformat(),
        "model": synthesis.get("model"),
        "synthesis_mode": synthesis.get("synthesis_mode"),
        "discovery": snapshot.get("run_summary", {}),
        "new_opportunity_count": len(synthesis.get("new_opportunity_ids", [])),
        "candidate_channel_count": len(synthesis.get("new_channel_ids", [])),
        "executions": [inbound_record, publication_record],
        "budget": tracker.snapshot(),
        "verified_revenue": state.get("revenue", {}),
        "claims": {
            "unverified_attention_counts_as_revenue": False,
            "candidate_channel_counts_as_connected": False,
            "model_output_counts_as_market_evidence": False,
        },
    }
    _write_json(root / "data" / "runtime_budget_state.json", runtime_state)
    (root / "docs" / "LATEST_DISCOVERY.md").write_text(
        render_discovery_markdown(
            snapshot,
            synthesis,
            [inbound_record, publication_record],
            runtime_state["budget"],
        ),
        encoding="utf-8",
    )
    _update_manifest(root, state, snapshot, synthesis)
    return runtime_state


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--observed-at", type=_parse_datetime, default=None)
    parser.add_argument("--offline", action="store_true", help="Disable network and model execution.")
    parser.add_argument("--model-response", type=Path, default=None, help="Use a saved model response fixture.")
    args = parser.parse_args()

    token = None if args.offline else os.environ.get("GITHUB_TOKEN")
    fetcher: Optional[JsonFetcher] = None
    if args.offline:
        def offline_fetcher(source: Mapping[str, Any], github_token: Optional[str]) -> Any:
            del source, github_token
            raise RuntimeError("offline mode")
        fetcher = offline_fetcher

    model_callable: Optional[ModelCallable] = None
    if args.model_response:
        saved_response = args.model_response.read_text(encoding="utf-8")

        def fixture_model(prompt: str, model: str) -> str:
            del prompt, model
            return saved_response

        model_callable = fixture_model

    state = run_continuous_cycle(
        ROOT,
        run_date=args.as_of,
        observed_at=args.observed_at,
        github_token=token,
        fetch_json=fetcher,
        model_callable=model_callable,
    )
    print("Completed {0}".format(state["cycle_id"]))
    print("Synthesis: {0}".format(state["synthesis_mode"]))
    print("New opportunities: {0}".format(state["new_opportunity_count"]))
    print("Verified net revenue: ${0:.2f}".format(state["verified_revenue"]["net_revenue"]))


if __name__ == "__main__":
    main()
