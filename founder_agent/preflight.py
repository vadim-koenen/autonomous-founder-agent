"""Deterministic public-metadata preflight reports for MCP and agent projects."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse


class PreflightInputError(ValueError):
    """Raised when a preflight target cannot be evaluated safely."""


CHECK_ACTIONS = {
    "repository_active": "Use an active, non-archived source repository.",
    "recent_maintenance": "Publish a maintenance update or document the support status.",
    "project_description": "Add a concrete public description of the server outcome.",
    "readme_present": "Add setup, transport, authentication, and usage documentation.",
    "license_declared": "Declare a license before asking external users to integrate.",
    "security_policy": "Publish a SECURITY.md with a private reporting path.",
    "version_declared": "Publish a pinned version in registry or package metadata.",
    "transport_declared": "Declare at least one remote transport or installable package.",
    "remote_https": "Use HTTPS for every remotely callable server URL.",
}


def _text(value: Any, limit: int = 300) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _public_https_url(value: Any, *, host: Optional[str] = None) -> str:
    text = _text(value, 500)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname:
        return ""
    if host and parsed.hostname.lower() != host:
        return ""
    return text


def _parse_timestamp(value: Any) -> Optional[datetime]:
    text = _text(value, 80)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _check(
    check_id: str,
    label: str,
    status: str,
    score: float,
    maximum: float,
    evidence: str,
) -> Dict[str, Any]:
    if status not in {"pass", "warn", "fail"}:
        raise ValueError("unsupported preflight check status")
    report = {
        "check_id": check_id,
        "label": label,
        "status": status,
        "score": round(float(score), 1),
        "max_score": round(float(maximum), 1),
        "evidence": _text(evidence, 400),
    }
    return report


def _has_file(files: List[str], name: str) -> bool:
    target = name.lower()
    return any(path.lower() == target or path.lower().endswith("/" + target) for path in files)


def _registry_transports(registry: Mapping[str, Any]) -> tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    remotes = [item for item in registry.get("remotes", []) if isinstance(item, Mapping)]
    packages = [item for item in registry.get("packages", []) if isinstance(item, Mapping)]
    return remotes, packages


def analyze_preflight(
    payload: Mapping[str, Any],
    *,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Score a sanitized snapshot without executing or importing target code."""

    if not isinstance(payload, Mapping):
        raise PreflightInputError("preflight payload must be an object")
    repository = payload.get("repository", {})
    registry = payload.get("registry", {})
    if not isinstance(repository, Mapping) or not isinstance(registry, Mapping):
        raise PreflightInputError("repository and registry must be objects")

    repository_url = _public_https_url(repository.get("url"), host="github.com")
    if not repository_url:
        raise PreflightInputError("only public HTTPS github.com repositories are supported")

    now = observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    files = sorted({_text(item, 240) for item in payload.get("files", []) if _text(item, 240)})
    remotes, packages = _registry_transports(registry)
    checks: List[Dict[str, Any]] = []

    archived = bool(repository.get("archived", False))
    checks.append(
        _check(
            "repository_active",
            "Active source repository",
            "fail" if archived else "pass",
            0 if archived else 15,
            15,
            "Repository is archived." if archived else "Repository is not archived.",
        )
    )

    pushed_at = _parse_timestamp(repository.get("pushed_at"))
    age_days = (now - pushed_at).days if pushed_at and pushed_at <= now else None
    age_label = "{0} {1}".format(age_days, "day" if age_days == 1 else "days") if age_days is not None else ""
    if age_days is None:
        checks.append(_check("recent_maintenance", "Recent maintenance", "warn", 5, 15, "No valid push timestamp was supplied."))
    elif age_days <= 90:
        checks.append(_check("recent_maintenance", "Recent maintenance", "pass", 15, 15, "Latest repository push was {0} ago.".format(age_label)))
    elif age_days <= 365:
        checks.append(_check("recent_maintenance", "Recent maintenance", "warn", 9, 15, "Latest repository push was {0} ago.".format(age_label)))
    else:
        checks.append(_check("recent_maintenance", "Recent maintenance", "fail", 2, 15, "Latest repository push was {0} ago.".format(age_label)))

    description = _text(repository.get("description") or registry.get("description"), 300)
    checks.append(
        _check(
            "project_description",
            "Outcome description",
            "pass" if len(description) >= 30 else "warn",
            8 if len(description) >= 30 else 3,
            8,
            description or "No public project description was supplied.",
        )
    )

    has_readme = any(path.lower().startswith("readme") for path in files)
    checks.append(_check("readme_present", "Public setup documentation", "pass" if has_readme else "fail", 10 if has_readme else 0, 10, "README found in repository root." if has_readme else "No root README was observed."))

    license_name = _text(
        repository.get("license_spdx")
        or (repository.get("license", {}).get("spdx_id") if isinstance(repository.get("license"), Mapping) else ""),
        80,
    )
    has_license = bool(license_name and license_name.upper() != "NOASSERTION") or _has_file(files, "LICENSE")
    checks.append(_check("license_declared", "License declared", "pass" if has_license else "fail", 10 if has_license else 0, 10, license_name or ("LICENSE file found." if has_license else "No declared license was observed.")))

    has_security = _has_file(files, "SECURITY.md")
    checks.append(_check("security_policy", "Security reporting policy", "pass" if has_security else "warn", 10 if has_security else 3, 10, "SECURITY.md found." if has_security else "No SECURITY.md was observed; this is not proof that no reporting path exists."))

    version = _text(registry.get("version"), 80)
    package_versions = [_text(item.get("version"), 80) for item in packages if _text(item.get("version"), 80)]
    declared_version = version or (package_versions[0] if package_versions else "")
    checks.append(_check("version_declared", "Pinned release version", "pass" if declared_version else "warn", 10 if declared_version else 3, 10, "Declared version: {0}.".format(declared_version) if declared_version else "No registry or package version was supplied."))

    has_transport = bool(remotes or packages)
    checks.append(_check("transport_declared", "Install or transport metadata", "pass" if has_transport else "warn", 12 if has_transport else 4, 12, "Observed {0} remote transport(s) and {1} package(s).".format(len(remotes), len(packages))))

    remote_urls = [_text(item.get("url"), 500) for item in remotes if _text(item.get("url"), 500)]
    secure_remotes = [item for item in remote_urls if _public_https_url(item)]
    if not remote_urls:
        checks.append(_check("remote_https", "Remote transport uses HTTPS", "warn", 5, 10, "No remote URL was supplied; local-package transport may still be valid."))
    elif len(secure_remotes) == len(remote_urls):
        checks.append(_check("remote_https", "Remote transport uses HTTPS", "pass", 10, 10, "All {0} observed remote URL(s) use HTTPS.".format(len(remote_urls))))
    else:
        checks.append(_check("remote_https", "Remote transport uses HTTPS", "fail", 0, 10, "One or more observed remote URLs do not use HTTPS."))

    score = round(sum(item["score"] for item in checks), 1)
    if score >= 82 and not any(item["status"] == "fail" for item in checks):
        verdict = "ready_for_live_protocol_test"
    elif score >= 60:
        verdict = "review_before_connection"
    else:
        verdict = "insufficient_public_assurance"

    canonical_input = json.dumps(
        {"repository": dict(repository), "registry": dict(registry), "files": files},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    report_id = "preflight-{0}".format(sha256(canonical_input.encode("utf-8")).hexdigest()[:16])
    next_actions = [
        CHECK_ACTIONS[item["check_id"]]
        for item in checks
        if item["status"] != "pass" and item["check_id"] in CHECK_ACTIONS
    ]
    report = {
        "schema_name": "mcp_agent_public_preflight_report",
        "schema_version": "0.1",
        "report_id": report_id,
        "observed_at": now.isoformat(),
        "scope": "public_metadata_only",
        "target": {
            "repository_url": repository_url,
            "registry_name": _text(registry.get("name"), 160),
            "declared_version": declared_version,
        },
        "score": score,
        "max_score": 100.0,
        "verdict": verdict,
        "checks": checks,
        "strengths": [item["label"] for item in checks if item["status"] == "pass"],
        "risk_flags": [item["check_id"] for item in checks if item["status"] != "pass"],
        "next_actions": next_actions,
        "execution_claims": {
            "target_code_executed": False,
            "target_credentials_used": False,
            "live_mcp_protocol_test_performed": False,
            "security_audit_completed": False,
        },
        "limitations": [
            "Public metadata can be stale, incomplete, or misleading.",
            "This report does not execute target code or prove that a server is safe.",
            "Authentication, tool schemas, latency, and protocol behavior require a separately authorized live test.",
        ],
    }
    sample_status = _text(payload.get("sample_status"), 100)
    if sample_status:
        report["sample_status"] = sample_status
    return report
