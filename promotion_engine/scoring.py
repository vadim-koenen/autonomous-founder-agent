"""Deterministic fit scoring. Scores are priorities, never probabilities."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Tuple


def _text(value: object) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value).lower()
    return str(value or "").lower()


def _matches_any(text: str, terms: Iterable[str]) -> bool:
    return any(str(term).lower() in text for term in terms)


def _company_size_matches(value: object, bounds: List[int]) -> bool:
    try:
        size = int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return False
    return bounds[0] <= size <= bounds[1]


def score_segment(prospect: Mapping[str, Any], segment: Mapping[str, Any]) -> Tuple[int, Dict[str, int]]:
    title = _text(prospect.get("title"))
    seniority = _text(prospect.get("seniority")) + " " + title
    technologies = _text(prospect.get("technologies"))
    industry = _text(prospect.get("industry"))
    details = {
        "title_fit": 25 if _matches_any(title, segment.get("title_keywords", [])) else 0,
        "seniority_fit": 15
        if _matches_any(seniority, segment.get("seniority_keywords", []))
        else 0,
        "technology_fit": 25
        if _matches_any(technologies, segment.get("technology_keywords", []))
        else 0,
        "company_size_fit": 15
        if _company_size_matches(prospect.get("company_size"), segment.get("company_size", [50, 5000]))
        else 0,
        "industry_fit": 10
        if not segment.get("industry_keywords")
        or _matches_any(industry, segment.get("industry_keywords", []))
        else 0,
        "evidence_present": 5 if len(_text(prospect.get("evidence_note")).strip()) >= 20 else 0,
        "verified_email": 5
        if _text(prospect.get("email_status")) in {"verified", "valid"}
        else 0,
    }
    return sum(details.values()), details


def best_segment(
    prospect: Mapping[str, Any], segments: Iterable[Mapping[str, Any]]
) -> Tuple[Mapping[str, Any], int, Dict[str, int]]:
    ranked = []
    for segment in segments:
        score, details = score_segment(prospect, segment)
        ranked.append((score, str(segment["segment_id"]), segment, details))
    if not ranked:
        raise ValueError("no segments configured")
    ranked.sort(key=lambda item: (-item[0], item[1]))
    score, _, segment, details = ranked[0]
    return segment, score, details
