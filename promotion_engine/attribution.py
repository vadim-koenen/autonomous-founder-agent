"""Attribution helpers that never place personal identifiers in URLs."""

from __future__ import annotations

from typing import Dict
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


ALLOWED_UTM_FIELDS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
}


def build_attributed_url(
    site_url: str,
    path: str,
    source: str,
    medium: str,
    campaign: str,
    content: str,
    term: str = "",
) -> str:
    base = urljoin(site_url.rstrip("/") + "/", path.lstrip("/"))
    parts = urlsplit(base)
    query: Dict[str, str] = dict(parse_qsl(parts.query, keep_blank_values=False))
    query.update(
        {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": campaign,
            "utm_content": content,
        }
    )
    if term:
        query["utm_term"] = term
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def assert_public_attribution(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError("attributed URLs must be public HTTPS URLs")
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key not in ALLOWED_UTM_FIELDS:
            raise ValueError("unexpected attribution field: {0}".format(key))
        lowered = value.lower()
        if "@" in value or "prospect" in lowered or "contact_id" in lowered:
            raise ValueError("personal or internal identifiers are forbidden in attribution URLs")
