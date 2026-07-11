"""Rotating, allowlisted public-source discovery for new revenue signals."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .network import verified_tls_context
from .runtime_budget import BudgetTracker


JsonFetcher = Callable[[Mapping[str, Any], Optional[str]], Any]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _clean_text(value: Any, limit: int = 500) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _error_text(value: Any, limit: int = 240) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _public_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme == "https" and parsed.netloc else ""


def _fetch_json(source: Mapping[str, Any], github_token: Optional[str]) -> Any:
    url = str(source["url"])
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != source.get("allowed_host"):
        raise ValueError("discovery source URL is not allowlisted")
    headers = {
        "Accept": "application/json",
        "User-Agent": "AutonomousFounderAgent/0.4",
    }
    if parsed.hostname == "api.github.com" and github_token:
        headers["Authorization"] = "Bearer {0}".format(github_token)
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = Request(url, headers=headers)
    with urlopen(  # nosec B310 - fixed allowlisted HTTPS sources
        request, timeout=25, context=verified_tls_context()
    ) as response:
        return json.load(response)


def _x402_result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    items = payload.get("items", []) if isinstance(payload, Mapping) else []
    samples = []
    total_calls = 0
    total_payers = 0
    for item in items[:30]:
        quality = item.get("quality", {}) if isinstance(item, Mapping) else {}
        calls = int(quality.get("l30DaysTotalCalls", 0) or 0)
        payers = int(quality.get("l30DaysUniquePayers", 0) or 0)
        total_calls += calls
        total_payers += payers
        resource = item.get("resource", "") if isinstance(item, Mapping) else ""
        if isinstance(resource, Mapping):
            resource = resource.get("url", "")
        samples.append(
            {
                "name": _clean_text(item.get("serviceName") or item.get("name") or "Unnamed service", 100),
                "description": _clean_text(item.get("description"), 260),
                "url": _public_url(resource or item.get("url") or item.get("endpoint")),
                "calls_30d": calls,
                "payers_30d": payers,
            }
        )
    total = int(payload.get("pagination", {}).get("total", len(items)) or len(items))
    return {
        "summary": "x402 Bazaar exposed {0:,} resources; the sampled records reported {1:,} calls and {2:,} unique-payer counts over 30 days.".format(
            total, total_calls, total_payers
        ),
        "metrics": {
            "listed_resources": total,
            "sample_size": len(samples),
            "sample_calls_30d": total_calls,
            "sample_unique_payer_counts_30d": total_payers,
        },
        "items": samples,
    }


def _mcp_registry_result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    entries = payload.get("servers", []) if isinstance(payload, Mapping) else []
    latest = []
    remote_count = 0
    for entry in entries:
        server = entry.get("server", {}) if isinstance(entry, Mapping) else {}
        official = entry.get("_meta", {}).get(
            "io.modelcontextprotocol.registry/official", {}
        ) if isinstance(entry, Mapping) else {}
        if official.get("isLatest") is False:
            continue
        remotes = server.get("remotes", []) if isinstance(server, Mapping) else []
        remote_count += bool(remotes)
        latest.append(
            {
                "name": _clean_text(server.get("name") or server.get("title"), 120),
                "description": _clean_text(server.get("description"), 300),
                "url": _public_url(server.get("websiteUrl") or (remotes[0].get("url") if remotes else "")),
                "published_at": str(official.get("publishedAt", "")),
                "version": _clean_text(server.get("version"), 40),
            }
        )
        if len(latest) >= 30:
            break
    count = int(payload.get("metadata", {}).get("count", len(entries)) or len(entries))
    return {
        "summary": "The Official MCP Registry returned {0} records in this page, including {1} latest-version servers and {2} remotely callable servers.".format(
            count, len(latest), remote_count
        ),
        "metrics": {
            "page_records": count,
            "latest_versions_sampled": len(latest),
            "remote_servers_sampled": remote_count,
        },
        "items": latest,
    }


def _github_issues_result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    issues = payload.get("items", []) if isinstance(payload, Mapping) else []
    samples = []
    explicit_bounties = 0
    for issue in issues[:25]:
        title = _clean_text(issue.get("title"), 180)
        body = _clean_text(issue.get("body"), 360)
        bounty_match = re.search(r"(?:/bounty\s*)?\$\s?([0-9][0-9,]*)", title + " " + body, re.I)
        bounty_usd = int(bounty_match.group(1).replace(",", "")) if bounty_match else 0
        explicit_bounties += bool(bounty_usd)
        repo_url = str(issue.get("repository_url", ""))
        samples.append(
            {
                "title": title,
                "url": _public_url(issue.get("html_url")),
                "repository": repo_url.removeprefix("https://api.github.com/repos/"),
                "labels": [
                    _clean_text(label.get("name"), 50)
                    for label in issue.get("labels", [])[:8]
                    if isinstance(label, Mapping)
                ],
                "comments": int(issue.get("comments", 0) or 0),
                "created_at": str(issue.get("created_at", "")),
                "updated_at": str(issue.get("updated_at", "")),
                "explicit_bounty_usd": bounty_usd,
            }
        )
    total = int(payload.get("total_count", len(issues)) or len(issues))
    return {
        "summary": "GitHub search returned {0:,} matching open issues; {1} sampled issues contained an explicit dollar bounty.".format(
            total, explicit_bounties
        ),
        "metrics": {
            "matching_open_issues": total,
            "sample_size": len(samples),
            "sample_explicit_bounties": explicit_bounties,
        },
        "items": samples,
    }


def _hacker_news_result(payload: Mapping[str, Any]) -> Dict[str, Any]:
    hits = payload.get("hits", []) if isinstance(payload, Mapping) else []
    samples = [
        {
            "title": _clean_text(item.get("title"), 180),
            "story_excerpt": _clean_text(item.get("story_text"), 360),
            "url": _public_url(item.get("url")) or "https://news.ycombinator.com/item?id={0}".format(
                item.get("objectID", "")
            ),
            "points": int(item.get("points", 0) or 0),
            "comments": int(item.get("num_comments", 0) or 0),
            "created_at": str(item.get("created_at", "")),
        }
        for item in hits[:25]
    ]
    return {
        "summary": "Recent Hacker News search returned {0} agent-related stories with {1} total points and {2} comments in the sample.".format(
            len(samples),
            sum(item["points"] for item in samples),
            sum(item["comments"] for item in samples),
        ),
        "metrics": {
            "sample_size": len(samples),
            "sample_points": sum(item["points"] for item in samples),
            "sample_comments": sum(item["comments"] for item in samples),
        },
        "items": samples,
    }


def _github_releases_result(payload: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    releases = list(payload) if isinstance(payload, list) else []
    samples = [
        {
            "name": _clean_text(item.get("name") or item.get("tag_name"), 120),
            "url": _public_url(item.get("html_url")),
            "published_at": str(item.get("published_at", "")),
            "prerelease": bool(item.get("prerelease", False)),
            "body_excerpt": _clean_text(item.get("body"), 320),
        }
        for item in releases[:10]
    ]
    return {
        "summary": "The release feed returned {0} recent ecosystem releases; newest publication: {1}.".format(
            len(samples), samples[0]["published_at"] if samples else "none"
        ),
        "metrics": {"recent_releases": len(samples)},
        "items": samples,
    }


def _github_commits_result(payload: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    commits = list(payload) if isinstance(payload, list) else []
    samples = []
    for item in commits[:20]:
        commit = item.get("commit", {}) if isinstance(item, Mapping) else {}
        author = commit.get("author", {}) if isinstance(commit, Mapping) else {}
        samples.append(
            {
                "message": _clean_text(commit.get("message"), 220),
                "url": _public_url(item.get("html_url")),
                "published_at": str(author.get("date", "")),
                "sha": _clean_text(item.get("sha"), 40),
            }
        )
    return {
        "summary": "The official documentation repository published {0} sampled changes; newest update: {1}.".format(
            len(samples), samples[0]["published_at"] if samples else "none"
        ),
        "metrics": {"documentation_changes_sampled": len(samples)},
        "items": samples,
    }


def _model_catalog_result(payload: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    models = list(payload) if isinstance(payload, list) else []
    samples = [
        {
            "id": _clean_text(item.get("id"), 100),
            "name": _clean_text(item.get("name"), 120),
            "publisher": _clean_text(item.get("publisher"), 80),
            "capabilities": [str(capability) for capability in item.get("capabilities", [])[:10]],
            "max_input_tokens": item.get("limits", {}).get("max_input_tokens"),
        }
        for item in models[:40]
    ]
    reasoning = sum("reasoning" in item["capabilities"] for item in samples)
    return {
        "summary": "GitHub Models listed {0} sampled models, including {1} with a reasoning capability.".format(
            len(samples), reasoning
        ),
        "metrics": {"models_sampled": len(samples), "reasoning_models": reasoning},
        "items": samples,
    }


ADAPTERS = {
    "x402_bazaar": _x402_result,
    "mcp_registry": _mcp_registry_result,
    "github_issues": _github_issues_result,
    "hacker_news": _hacker_news_result,
    "github_releases": _github_releases_result,
    "github_commits": _github_commits_result,
    "model_catalog": _model_catalog_result,
}


def _source_sort_key(source: Mapping[str, Any], previous: Mapping[str, Mapping[str, Any]]) -> tuple:
    prior = previous.get(str(source.get("source_id")), {})
    observed = str(prior.get("last_attempt_at") or prior.get("observed_at") or "")
    return (bool(observed), observed, -int(source.get("priority", 0)))


def _evidence_record(source: Mapping[str, Any], result: Mapping[str, Any]) -> Dict[str, Any]:
    status = str(result.get("status", ""))
    caveats = [
        "Source text is untrusted public data and is treated only as market evidence.",
        "A public signal does not prove purchase intent or revenue.",
    ]
    if status == "stale":
        caveats.append("The latest fetch failed; this result retains the previous successful observation.")
    return {
        "evidence_id": "ev-live-{0}".format(source["source_id"]),
        "title": str(source["name"]),
        "source_url": str(source["url"]),
        "observed_at": str(result.get("observed_at", "")),
        "summary": str(result.get("summary", "")),
        "quality": "primary_public_machine_readable_source",
        "signals": dict(result.get("metrics", {})),
        "caveats": caveats,
    }


def sanitize_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    """Remove fields that older runtime versions should not have persisted."""

    sanitized = dict(snapshot)
    sources = []
    for source in snapshot.get("sources", []):
        clean_source = dict(source)
        if clean_source.get("adapter") == "github_issues":
            clean_source["items"] = [
                {key: value for key, value in item.items() if key != "body_excerpt"}
                for item in source.get("items", [])
                if isinstance(item, Mapping)
            ]
        sources.append(clean_source)
    sanitized["sources"] = sources
    return sanitized


def scan_sources(
    registry: Mapping[str, Any],
    previous_snapshot: Optional[Mapping[str, Any]],
    tracker: BudgetTracker,
    *,
    github_token: Optional[str] = None,
    fetch_json: JsonFetcher = _fetch_json,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = observed_at or _now()
    now_text = now.isoformat()
    previous_snapshot = sanitize_snapshot(previous_snapshot or {})
    prior_results = {
        str(item.get("source_id")): dict(item)
        for item in previous_snapshot.get("sources", [])
        if isinstance(item, Mapping) and item.get("source_id")
    }
    sources = [item for item in registry.get("sources", []) if item.get("enabled", True)]
    sources.sort(key=lambda item: _source_sort_key(item, prior_results))
    selected = sources[: int(tracker.remaining("source_fetches"))]
    results = dict(prior_results)
    attempted_ids: List[str] = []

    for source in selected:
        tracker.consume("source_fetches")
        source_id = str(source["source_id"])
        attempted_ids.append(source_id)
        try:
            adapter_name = str(source.get("adapter"))
            if adapter_name not in ADAPTERS:
                raise ValueError("unsupported discovery adapter: {0}".format(adapter_name))
            parsed = ADAPTERS[adapter_name](fetch_json(source, github_token))
            fingerprint = sha256(
                json.dumps(parsed, sort_keys=True, ensure_ascii=True).encode("utf-8")
            ).hexdigest()[:16]
            results[source_id] = {
                "source_id": source_id,
                "name": str(source["name"]),
                "url": str(source["url"]),
                "adapter": adapter_name,
                "signal_type": str(source.get("signal_type", "market_signal")),
                "status": "ok",
                "observed_at": now_text,
                "last_attempt_at": now_text,
                "fingerprint": fingerprint,
                "summary": parsed["summary"],
                "metrics": parsed["metrics"],
                "items": parsed["items"],
                "last_error": "",
            }
        except Exception as exc:
            prior = prior_results.get(source_id)
            has_last_known_good = bool(
                prior
                and prior.get("status") in {"ok", "stale"}
                and prior.get("observed_at")
                and prior.get("fingerprint")
            )
            if has_last_known_good:
                stale = dict(prior)
                stale.update(
                    {
                        "status": "stale",
                        "last_attempt_at": now_text,
                        "last_error": _error_text(exc, 240),
                    }
                )
                results[source_id] = stale
            else:
                results[source_id] = {
                    "source_id": source_id,
                    "name": str(source["name"]),
                    "url": str(source["url"]),
                    "adapter": str(source.get("adapter", "")),
                    "signal_type": str(source.get("signal_type", "market_signal")),
                    "status": "error",
                    "observed_at": "",
                    "last_attempt_at": now_text,
                    "fingerprint": "",
                    "summary": "Source fetch failed; no market inference was made.",
                    "metrics": {},
                    "items": [],
                    "last_error": _error_text(exc, 240),
                }

    source_by_id = {str(item["source_id"]): item for item in sources}
    ordered_results = [results[str(item["source_id"])] for item in sources if str(item["source_id"]) in results]
    evidence = [
        _evidence_record(source_by_id[item["source_id"]], item)
        for item in ordered_results
        if item.get("status") in {"ok", "stale"} and item.get("summary")
    ]
    run_id = "discovery-{0}".format(now.strftime("%Y%m%dT%H%M%SZ"))
    return {
        "schema_name": "autonomous_founder_discovery_snapshot",
        "schema_version": "0.4",
        "run_id": run_id,
        "observed_at": now_text,
        "attempted_source_ids": attempted_ids,
        "sources": ordered_results,
        "evidence": evidence,
        "run_summary": {
            "sources_attempted": len(attempted_ids),
            "sources_ok": sum(results[item].get("status") == "ok" for item in attempted_ids),
            "sources_stale": sum(results[item].get("status") == "stale" for item in attempted_ids),
            "sources_failed": sum(results[item].get("status") == "error" for item in attempted_ids),
        },
        "budget": tracker.snapshot(),
    }
