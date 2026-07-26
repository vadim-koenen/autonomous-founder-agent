"""Outbound policy checks and suppression handling."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlsplit


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GENERIC_LOCAL_PARTS = {
    "admin",
    "contact",
    "hello",
    "info",
    "marketing",
    "sales",
    "support",
    "team",
}


def _normalized_country(value: object) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "us": "united states",
        "usa": "united states",
        "u.s.": "united states",
        "united states of america": "united states",
    }
    return aliases.get(normalized, normalized)


def _https_public_url(value: object) -> bool:
    try:
        parts = urlsplit(str(value or ""))
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.netloc) and parts.hostname not in {
        "localhost",
        "127.0.0.1",
    }


def evaluate_policy(
    prospect: Mapping[str, Any],
    policy: Mapping[str, Any],
    suppression_reason: Optional[str] = None,
) -> Dict[str, List[str]]:
    blockers: List[str] = []
    warnings: List[str] = []
    email = str(prospect.get("email") or "").strip().lower()
    local, _, domain = email.partition("@")

    if suppression_reason:
        blockers.append("suppressed:{0}".format(suppression_reason))
    if not EMAIL_PATTERN.match(email):
        blockers.append("valid_business_email_required")
    if local in GENERIC_LOCAL_PARTS:
        blockers.append("role_based_email_blocked")
    if domain in {str(item).lower() for item in policy.get("blocked_email_domains", [])}:
        blockers.append("free_or_generic_email_domain_blocked")
    if policy.get("require_verified_work_email", True) and str(
        prospect.get("email_status") or ""
    ).lower() not in {"verified", "valid"}:
        blockers.append("verified_work_email_required")

    allowed = {_normalized_country(item) for item in policy.get("allowed_countries", [])}
    if _normalized_country(prospect.get("country")) not in allowed:
        blockers.append("jurisdiction_not_enabled")
    if policy.get("require_source_url", True) and not _https_public_url(
        prospect.get("source_url")
    ):
        blockers.append("public_https_source_required")
    evidence = str(prospect.get("evidence_note") or "").strip()
    if policy.get("require_evidence_note", True) and len(evidence) < int(
        policy.get("min_evidence_length", 20)
    ):
        blockers.append("specific_evidence_required")
    if not str(prospect.get("company_domain") or "").strip():
        blockers.append("company_domain_required")
    if not str(prospect.get("first_name") or "").strip():
        warnings.append("first_name_missing")

    return {"blockers": sorted(set(blockers)), "warnings": sorted(set(warnings))}
