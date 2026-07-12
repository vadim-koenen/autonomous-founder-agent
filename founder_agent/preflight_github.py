"""Allowlisted GitHub metadata adapter for the public preflight engine."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Optional
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .network import verified_tls_context
from .preflight import PreflightInputError, analyze_preflight


JsonTransport = Callable[[str, Optional[str]], Any]
REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def parse_github_repository_url(repository_url: str) -> tuple[str, str]:
    parsed = urlparse(str(repository_url or "").strip())
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise PreflightInputError("repository URL must use public HTTPS github.com")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise PreflightInputError("repository URL must contain exactly owner/repository")
    owner, repository = parts
    repository = repository.removesuffix(".git")
    if not REPOSITORY_PART.fullmatch(owner) or not REPOSITORY_PART.fullmatch(repository):
        raise PreflightInputError("repository owner or name contains unsupported characters")
    return owner, repository


def _fetch_json(url: str, github_token: Optional[str]) -> Any:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise PreflightInputError("GitHub adapter attempted a non-allowlisted request")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AutonomousFounderPreflight/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if github_token:
        headers["Authorization"] = "Bearer {0}".format(github_token)
    request = Request(url, headers=headers)
    with urlopen(  # nosec B310 - host is fixed and validated above
        request, timeout=20, context=verified_tls_context()
    ) as response:
        return json.load(response)


def snapshot_github_repository(
    repository_url: str,
    *,
    github_token: Optional[str] = None,
    transport: Optional[JsonTransport] = None,
) -> Dict[str, Any]:
    owner, repository = parse_github_repository_url(repository_url)
    fetch = transport or _fetch_json
    base = "https://api.github.com/repos/{0}/{1}".format(owner, repository)
    metadata = fetch(base, github_token)
    contents = fetch(base + "/contents", github_token)
    if not isinstance(metadata, Mapping) or not isinstance(contents, list):
        raise PreflightInputError("GitHub returned an unsupported repository response")
    files = [
        str(item.get("path", ""))
        for item in contents
        if isinstance(item, Mapping) and item.get("type") == "file" and item.get("path")
    ]
    license_data = metadata.get("license", {}) if isinstance(metadata.get("license"), Mapping) else {}
    return {
        "observed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": {
            "url": "https://github.com/{0}/{1}".format(owner, repository),
            "description": str(metadata.get("description") or ""),
            "archived": bool(metadata.get("archived", False)),
            "fork": bool(metadata.get("fork", False)),
            "pushed_at": str(metadata.get("pushed_at") or ""),
            "default_branch": str(metadata.get("default_branch") or ""),
            "license_spdx": str(license_data.get("spdx_id") or ""),
            "open_issues_count": int(metadata.get("open_issues_count", 0) or 0),
            "stargazers_count": int(metadata.get("stargazers_count", 0) or 0),
        },
        "registry": {},
        "files": files,
    }


def preflight_github_repository(
    repository_url: str,
    *,
    github_token: Optional[str] = None,
    transport: Optional[JsonTransport] = None,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    snapshot = snapshot_github_repository(
        repository_url,
        github_token=github_token,
        transport=transport,
    )
    return analyze_preflight(snapshot, observed_at=observed_at)
