"""Truth-bounded channel drafts for human review."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from .attribution import assert_public_attribution, build_attributed_url


def _compact_evidence(value: object, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip()


def _link(config: Mapping[str, Any], segment: Mapping[str, Any], content: str) -> str:
    campaign = config["campaign"]
    url = build_attributed_url(
        campaign["site_url"],
        segment["landing_path"],
        source="apollo",
        medium="email",
        campaign=campaign["campaign_id"],
        content=content,
        term=segment["segment_id"],
    )
    assert_public_attribution(url)
    return url


def email_sequence(
    prospect: Mapping[str, Any], segment: Mapping[str, Any], config: Mapping[str, Any]
) -> List[Dict[str, Any]]:
    first_name = str(prospect.get("first_name") or "there").strip()
    company = str(prospect.get("company") or "your team").strip()
    evidence = _compact_evidence(prospect.get("evidence_note"))
    landing_1 = _link(config, segment, "{0}_step_1".format(segment["segment_id"]))
    landing_2 = _link(config, segment, "{0}_step_2".format(segment["segment_id"]))
    landing_3 = _link(config, segment, "{0}_step_3".format(segment["segment_id"]))

    return [
        {
            "step_index": 1,
            "wait_business_days": 0,
            "subject": "{0}: a revenue-systems question".format(company),
            "body": (
                "Hi {first},\n\n"
                "I found this while researching {company}: {evidence}\n\n"
                "{pain} I help B2B teams diagnose that handoff before anyone commits "
                "to a rebuild. Here is the relevant systems-review lane: {url}\n\n"
                "If this is active for your team, would a short diagnostic conversation "
                "be useful?\n\nVadim"
            ).format(
                first=first_name,
                company=company,
                evidence=evidence,
                pain=segment["pain"],
                url=landing_1,
            ),
            "attributed_url": landing_1,
        },
        {
            "step_index": 2,
            "wait_business_days": 4,
            "subject": "A no-rebuild way to test this",
            "body": (
                "Hi {first},\n\n"
                "One practical follow-up: I usually start by tracing the signal, owner, "
                "routing rule, and downstream field before recommending new tooling. "
                "That exposes whether the problem is orchestration, data, or governance.\n\n"
                "{offer}: {url}\n\n"
                "Worth sending a short checklist tailored to {company}?\n\nVadim"
            ).format(
                first=first_name,
                offer=segment["offer"],
                url=landing_2,
                company=company,
            ),
            "attributed_url": landing_2,
        },
        {
            "step_index": 3,
            "wait_business_days": 7,
            "subject": "Close the loop?",
            "body": (
                "Hi {first},\n\n"
                "I will close the loop after this. If {pain_lower} becomes a priority, "
                "the diagnostic scope is here: {url}\n\n"
                "No need to reply if it is not relevant. You can also use the unsubscribe "
                "link below to opt out.\n\nVadim"
            ).format(
                first=first_name,
                pain_lower=str(segment["pain"]).strip().rstrip(".").lower(),
                url=landing_3,
            ),
            "attributed_url": landing_3,
        },
    ]


def linkedin_manual_task(
    prospect: Mapping[str, Any], segment: Mapping[str, Any], config: Mapping[str, Any]
) -> Dict[str, Any]:
    campaign = config["campaign"]
    url = build_attributed_url(
        campaign["site_url"],
        segment["landing_path"],
        source="linkedin",
        medium="organic_manual",
        campaign=campaign["campaign_id"],
        content="{0}_research_task".format(segment["segment_id"]),
        term=segment["segment_id"],
    )
    assert_public_attribution(url)
    return {
        "step_index": 1,
        "wait_business_days": 0,
        "subject": "Manual LinkedIn research task",
        "body": (
            "Owner review required. Verify the supplied public evidence, follow the person "
            "or company only if relevant, and engage with a substantive public post before "
            "considering any direct message. Do not automate connection requests, comments, "
            "or messages. Relevant resource: {0}"
        ).format(url),
        "attributed_url": url,
    }
