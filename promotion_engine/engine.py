"""Promotion workflow orchestration with explicit review and export boundaries."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from founder_agent.revenue import summarize_ledger

from .attribution import assert_public_attribution
from .config import APOLLO_ACTIVATION_GATES
from .messages import email_sequence, linkedin_manual_task
from .policy import evaluate_policy
from .scoring import best_segment
from .store import PromotionStore, SUPPRESSION_SCOPE_REASONS


CSV_ALIASES = {
    "first name": "first_name",
    "last name": "last_name",
    "email status": "email_status",
    "job title": "title",
    "company name": "company",
    "company domain": "company_domain",
    "# employees": "company_size",
    "employee count": "company_size",
    "person id": "apollo_person_id",
    "contact id": "apollo_contact_id",
}


class PromotionEngine:
    def __init__(
        self,
        config: Mapping[str, Any],
        store: PromotionStore,
        ledger_path: Path,
        grants_path: Optional[Path] = None,
    ):
        self.config = config
        self.store = store
        self.ledger_path = Path(ledger_path)
        self.grants_path = Path(grants_path) if grants_path is not None else None
        self.campaign = config["campaign"]
        self.segments = {item["segment_id"]: item for item in config["segments"]}
        self.active_segments = [
            self.segments[segment_id]
            for segment_id in self.campaign["active_segment_ids"]
        ]

    def import_apollo_csv(self, path: Path) -> Dict[str, int]:
        imported = 0
        rejected = 0
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV header is required")
            for row in reader:
                normalized: Dict[str, Any] = {}
                for raw_key, value in row.items():
                    key = str(raw_key or "").strip().lower()
                    key = CSV_ALIASES.get(key, key.replace(" ", "_"))
                    normalized[key] = value
                if not str(normalized.get("email") or "").strip():
                    rejected += 1
                    continue
                self.store.upsert_prospect(normalized)
                imported += 1
        return {"imported": imported, "rejected": rejected}

    def import_suppressions_csv(
        self, path: Path, source: str, scope: str
    ) -> Dict[str, int]:
        records = []
        with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"email", "reason", "evidence_reference"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(
                    "suppression CSV requires email, reason, and evidence_reference"
                )
            records.extend(reader)
        return {
            "imported": self.store.import_suppressions(
                records,
                snapshot_source=source,
                snapshot_scope=scope,
            ),
            "scope": scope,
        }

    def qualify(self) -> Dict[str, int]:
        campaign_id = self.campaign["campaign_id"]
        threshold = int(self.campaign["score_threshold"])
        company_cap = int(self.config["policy"].get("max_prospects_per_company", 1))
        staged: List[Dict[str, Any]] = []
        for prospect in self.store.list_prospects():
            segment, score, details = best_segment(prospect, self.active_segments)
            policy_result = evaluate_policy(
                prospect,
                self.config["policy"],
                self.store.suppression_reason(str(prospect["email"])),
            )
            blockers = list(policy_result["blockers"])
            if (
                self.config["policy"].get("require_segment_title_match", True)
                and int(details.get("title_fit", 0)) == 0
            ):
                blockers.append("target_role_evidence_required")
            if (
                self.config["policy"].get("require_segment_seniority_match", True)
                and int(details.get("seniority_fit", 0)) == 0
            ):
                blockers.append("target_seniority_required")
            if self.config["policy"].get("require_segment_technology_match", True):
                technologies = prospect.get("technologies", [])
                if not isinstance(technologies, list):
                    technologies = [technologies]
                technology_text = " ".join(str(item) for item in technologies).lower()
                required_groups = segment.get("required_technology_groups", [])
                if any(
                    not any(str(term).lower() in technology_text for term in group)
                    for group in required_groups
                ):
                    blockers.append("target_technology_evidence_required")
            if (
                self.config["policy"].get("require_segment_company_size_match", True)
                and int(details.get("company_size_fit", 0)) == 0
            ):
                blockers.append("target_company_size_required")
            if (
                self.config["policy"].get("require_segment_industry_match", True)
                and int(details.get("industry_fit", 0)) == 0
            ):
                blockers.append("target_industry_required")
            staged.append(
                {
                    "prospect": prospect,
                    "segment": segment,
                    "score": score,
                    "details": details,
                    "blockers": blockers,
                    "warnings": policy_result["warnings"],
                }
            )

        staged.sort(
            key=lambda item: (
                -int(item["score"]),
                str(item["prospect"].get("company_domain") or ""),
                str(item["prospect"]["prospect_id"]),
            )
        )
        company_counts: Dict[str, int] = {}
        counts = {"qualified": 0, "review_required": 0, "suppressed": 0}
        for item in staged:
            prospect = item["prospect"]
            blockers = item["blockers"]
            suppressed = any(str(blocker).startswith("suppressed:") for blocker in blockers)
            domain = str(prospect.get("company_domain") or "").lower()
            if not suppressed and not blockers and int(item["score"]) >= threshold:
                if company_counts.get(domain, 0) >= company_cap:
                    blockers.append("company_campaign_cap_reached")
                else:
                    company_counts[domain] = company_counts.get(domain, 0) + 1

            if suppressed:
                status = "suppressed"
            elif blockers or int(item["score"]) < threshold:
                if int(item["score"]) < threshold:
                    blockers.append("score_below_review_threshold")
                status = "review_required"
            else:
                status = "qualified"
            counts[status] += 1
            self.store.save_score(
                prospect["prospect_id"],
                campaign_id,
                item["segment"]["segment_id"],
                int(item["score"]),
                item["details"],
                blockers,
                item["warnings"],
                status,
            )
        return counts

    def create_drafts(self, channel: str) -> Dict[str, int]:
        if channel not in {"apollo_email", "linkedin_manual_task"}:
            raise ValueError("unsupported channel")
        created = 0
        prospects = self.store.qualified_prospects(self.campaign["campaign_id"])
        for prospect in prospects:
            segment = self.segments[prospect["segment_id"]]
            drafts = (
                email_sequence(prospect, segment, self.config)
                if channel == "apollo_email"
                else [linkedin_manual_task(prospect, segment, self.config)]
            )
            for draft in drafts:
                assert_public_attribution(str(draft["attributed_url"]))
                self.store.save_draft(
                    prospect["prospect_id"],
                    self.campaign["campaign_id"],
                    segment["segment_id"],
                    channel,
                    draft,
                )
                created += 1
        return {"qualified_prospects": len(prospects), "drafts_considered": created}

    def approve(
        self,
        reviewer: str,
        draft_id: Optional[str] = None,
        prospect_id: Optional[str] = None,
        approve_all: bool = False,
        channel: Optional[str] = None,
    ) -> int:
        allowed = {
            str(item).strip().casefold()
            for item in self.config["policy"].get("allowed_approvers", [])
        }
        if reviewer.strip().casefold() not in allowed:
            raise ValueError("reviewer is not in policy.allowed_approvers")
        if (approve_all or prospect_id) and channel not in {
            "apollo_email",
            "linkedin_manual_task",
        }:
            raise ValueError(
                "channel is required when approving a prospect or campaign batch"
            )
        return self.store.approve_drafts(
            reviewer=reviewer,
            draft_id=draft_id,
            prospect_id=prospect_id,
            campaign_id=(
                self.campaign["campaign_id"]
                if approve_all or prospect_id
                else None
            ),
            channel=channel,
        )

    def export_apollo(self, output_path: Path) -> Dict[str, Any]:
        # Re-run policy and refresh draft content before trusting stored approval.
        # Unchanged drafts retain approval; changed copy returns to draft status.
        self.qualify()
        self.create_drafts("apollo_email")
        self.store.invalidate_disallowed_approvals(
            self.campaign["campaign_id"],
            "apollo_email",
            self.config["policy"].get("allowed_approvers", []),
        )
        approved = self.store.approved_drafts(
            self.campaign["campaign_id"], channel="apollo_email"
        )
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for draft in approved:
            grouped.setdefault(str(draft["prospect_id"]), []).append(draft)
        drafts = [
            draft
            for group in grouped.values()
            if {int(item["step_index"]) for item in group} == {1, 2, 3}
            for draft in group
        ]
        incomplete = sum(
            1
            for group in grouped.values()
            if {int(item["step_index"]) for item in group} != {1, 2, 3}
        )
        if not drafts:
            raise ValueError("no complete, approved, unsuppressed email sequences to export")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "email",
            "first_name",
            "last_name",
            "company",
            "title",
            "company_domain",
            "apollo_contact_id",
            "segment_id",
            "step_index",
            "wait_business_days",
            "subject",
            "body",
            "attributed_url",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for draft in drafts:
                writer.writerow({key: draft.get(key, "") for key in fields})
        export_id = self.store.mark_exported(
            [draft["draft_id"] for draft in drafts],
            self.campaign["campaign_id"],
            "apollo_email",
            output_path.name,
        )
        return {
            "export_id": export_id,
            "records": len(drafts),
            "incomplete_prospects_excluded": incomplete,
            "sent": 0,
        }

    def export_review_queue(self, output_path: Path) -> Dict[str, Any]:
        drafts = self.store.review_drafts(self.campaign["campaign_id"])
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "draft_id",
            "prospect_id",
            "channel",
            "step_index",
            "status",
            "score",
            "first_name",
            "last_name",
            "email",
            "title",
            "company",
            "company_domain",
            "source_url",
            "evidence_note",
            "segment_id",
            "subject",
            "body",
            "attributed_url",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for draft in drafts:
                writer.writerow({key: draft.get(key, "") for key in fields})
        return {"records": len(drafts), "private_output": output_path.name}

    def suppress(self, email: str, reason: str, evidence_reference: str) -> None:
        self.store.suppress(email, reason, evidence_reference)

    def activation_preflight(self) -> Dict[str, Any]:
        email_config = self.config["channels"]["apollo_email"]
        blockers = []
        gates = email_config.get("activation_gates")
        if not isinstance(gates, dict) or set(gates) != set(APOLLO_ACTIVATION_GATES):
            blockers.append("activation_gate_configuration_invalid")
            gates = {}
        for gate in APOLLO_ACTIVATION_GATES:
            if gates.get(gate) is not True:
                blockers.append("activation_gate_failed:{0}".format(gate))
        if email_config.get("send_enabled") is not True:
            blockers.append("engine_sending_disabled")
        if email_config.get("sequence_activation_implemented") is not True:
            blockers.append("sequence_activation_not_implemented")

        configured_daily_limit = email_config.get(
            "default_daily_send_limit_after_activation"
        )
        if type(configured_daily_limit) is not int or configured_daily_limit <= 0:
            blockers.append("daily_send_limit_invalid")
            configured_daily_limit = None

        capability = {
            "enabled": False,
            "max_per_cycle": 0,
            "source": str(self.grants_path) if self.grants_path is not None else "",
        }
        if self.grants_path is None:
            blockers.append("commercial_email_capability_grant_unconfigured")
        else:
            try:
                grant_payload = json.loads(
                    self.grants_path.read_text(encoding="utf-8")
                )
                grants = grant_payload.get("grants", [])
                if not isinstance(grants, list):
                    raise TypeError("grants must be a list")
                matching_grants = [
                    item
                    for item in grants
                    if isinstance(item, dict)
                    and item.get("capability_id") == "commercial_email_or_dm"
                ]
            except (OSError, ValueError, TypeError, AttributeError):
                matching_grants = []
                blockers.append("commercial_email_capability_grant_unreadable")
            if len(matching_grants) != 1:
                if "commercial_email_capability_grant_unreadable" not in blockers:
                    blockers.append(
                        "commercial_email_capability_grant_missing"
                        if not matching_grants
                        else "commercial_email_capability_grant_ambiguous"
                    )
            else:
                grant = matching_grants[0]
                capability["enabled"] = grant.get("enabled") is True
                ceiling = grant.get("max_per_cycle")
                if type(ceiling) is int and ceiling > 0:
                    capability["max_per_cycle"] = ceiling
                else:
                    blockers.append(
                        "commercial_email_capability_ceiling_not_positive"
                    )
                if grant.get("enabled") is not True:
                    blockers.append("commercial_email_capability_disabled")

        required_scopes = self.config["policy"].get(
            "required_suppression_snapshot_scopes", []
        )
        if (
            not isinstance(required_scopes, list)
            or any(not isinstance(scope, str) for scope in required_scopes)
            or len(required_scopes) != len(set(required_scopes))
            or set(required_scopes) != set(SUPPRESSION_SCOPE_REASONS)
        ):
            blockers.append("suppression_snapshot_scope_configuration_invalid")
            required_scopes = list(SUPPRESSION_SCOPE_REASONS)
        try:
            maximum = float(
                self.config["policy"].get(
                    "suppression_snapshot_max_age_hours",
                    0,
                )
            )
        except (TypeError, ValueError):
            maximum = 0
        if maximum <= 0:
            blockers.append("suppression_snapshot_max_age_invalid")
        snapshots: Dict[str, Any] = {}
        ages = []
        for scope in required_scopes:
            snapshot = self.store.get_metadata(
                "suppression_snapshot:{0}".format(scope)
            )
            if snapshot is None:
                blockers.append("suppression_snapshot_missing:{0}".format(scope))
                snapshots[scope] = None
                continue
            try:
                updated_at = datetime.fromisoformat(str(snapshot["updated_at"]))
                age_hours = (
                    datetime.now(timezone.utc) - updated_at.astimezone(timezone.utc)
                ).total_seconds() / 3600
            except (TypeError, ValueError):
                blockers.append(
                    "suppression_snapshot_timestamp_invalid:{0}".format(scope)
                )
                snapshots[scope] = {
                    "metadata": snapshot,
                    "age_hours": None,
                }
                continue
            ages.append(age_hours)
            if age_hours < 0 or age_hours > maximum:
                blockers.append("suppression_snapshot_stale:{0}".format(scope))
            snapshots[scope] = {
                "metadata": snapshot,
                "age_hours": round(age_hours, 2),
            }

        effective_daily_limit = None
        if configured_daily_limit is not None and capability["max_per_cycle"] > 0:
            effective_daily_limit = min(
                configured_daily_limit,
                int(capability["max_per_cycle"]),
            )

        return {
            "ready": not blockers,
            "blockers": sorted(blockers),
            "commercial_email_capability": capability,
            "suppression_snapshots": snapshots,
            "suppression_snapshot_age_hours": (
                round(max(ages), 2) if ages else None
            ),
            "daily_limit_after_activation": configured_daily_limit,
            "effective_daily_limit_after_activation": effective_daily_limit,
        }

    def record_event(
        self,
        prospect_id: str,
        event_type: str,
        channel: str,
        evidence_reference: str,
        occurred_at: str,
    ) -> str:
        event_id = self.store.record_event(
            prospect_id,
            self.campaign["campaign_id"],
            event_type,
            channel,
            evidence_reference,
            occurred_at,
        )
        if event_type in {"unsubscribed", "bounced"}:
            prospect = self.store.get_prospect(prospect_id)
            self.store.suppress(
                str(prospect["email"]),
                event_type,
                evidence_reference,
                source_scope="apollo_delivery_event",
            )
        return event_id

    def report(self) -> Dict[str, Any]:
        ledger = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        revenue = summarize_ledger(ledger)
        return {
            "campaign_id": self.campaign["campaign_id"],
            "counts": self.store.aggregate_counts(self.campaign["campaign_id"]),
            "verified_revenue": {
                "source": str(self.ledger_path),
                "transactions": revenue.verified_transactions,
                "gross_usd": revenue.gross_revenue,
                "net_usd": revenue.net_revenue,
            },
            "interpretation": (
                "Prospects, drafts, exports, clicks, replies, and meetings are funnel signals. "
                "Only ledger-verified completed transactions count as revenue."
            ),
        }
