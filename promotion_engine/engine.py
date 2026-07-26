"""Promotion workflow orchestration with explicit review and export boundaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from founder_agent.revenue import summarize_ledger

from .attribution import assert_public_attribution
from .messages import email_sequence, linkedin_manual_task
from .policy import evaluate_policy
from .scoring import best_segment
from .store import PromotionStore


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
    def __init__(self, config: Mapping[str, Any], store: PromotionStore, ledger_path: Path):
        self.config = config
        self.store = store
        self.ledger_path = Path(ledger_path)
        self.campaign = config["campaign"]
        self.segments = {item["segment_id"]: item for item in config["segments"]}

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

    def qualify(self) -> Dict[str, int]:
        campaign_id = self.campaign["campaign_id"]
        threshold = int(self.campaign["score_threshold"])
        company_cap = int(self.config["policy"].get("max_prospects_per_company", 1))
        staged: List[Dict[str, Any]] = []
        for prospect in self.store.list_prospects():
            segment, score, details = best_segment(prospect, self.config["segments"])
            policy_result = evaluate_policy(
                prospect,
                self.config["policy"],
                self.store.suppression_reason(str(prospect["email"])),
            )
            staged.append(
                {
                    "prospect": prospect,
                    "segment": segment,
                    "score": score,
                    "details": details,
                    "blockers": list(policy_result["blockers"]),
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
        self, reviewer: str, draft_id: Optional[str] = None, approve_all: bool = False
    ) -> int:
        return self.store.approve_drafts(
            reviewer=reviewer,
            draft_id=draft_id,
            campaign_id=self.campaign["campaign_id"] if approve_all else None,
        )

    def export_apollo(self, output_path: Path) -> Dict[str, Any]:
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
            self.store.suppress(str(prospect["email"]), event_type, evidence_reference)
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
