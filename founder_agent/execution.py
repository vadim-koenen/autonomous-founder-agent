"""Bounded, allowlisted execution for one commercial action per founder cycle."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .channels import load_channels, plan_channel_action
from .network import verified_tls_context
from .runtime_budget import BudgetTracker


PUBLIC_INTAKE_URL = (
    "https://github.com/vadim-koenen/autonomous-founder-agent/issues/new"
    "?template=opportunity-interest.yml"
)
PUBLICATION_ACTIONS = {"publish_validation_brief", "research_public_prospects"}
PUBLIC_CHECKOUT_PROVIDERS = {"stripe", "contra", "lemon_squeezy"}
GITHUB_REPOSITORY = "vadim-koenen/autonomous-founder-agent"
GITHUB_API_PREFIX = "https://api.github.com/repos/{0}/".format(GITHUB_REPOSITORY)
RESPONSE_MARKER = "<!-- autonomous-founder-agent:interest-response:v1 -->"


IssueTransport = Callable[[str, str, Optional[Mapping[str, Any]], str], Any]


def _text(value: Any, limit: int = 700) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _public_https_url(value: Any) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    return url if parsed.scheme == "https" and parsed.netloc else ""


def _price_text(price: Mapping[str, Any]) -> str:
    amount = price.get("amount", 0)
    currency = _text(price.get("currency") or "USD", 12)
    model = _text(price.get("billing_model") or "fixed", 40).replace("_", " ")
    return "{0:g} {1} ({2})".format(float(amount), currency, model)


def configured_checkout_opportunity_id(config: Optional[Mapping[str, Any]]) -> str:
    """Return the opportunity behind a human-configured public checkout."""

    checkout = config or {}
    checkout_url = _public_https_url(checkout.get("checkout_url"))
    opportunity_id = str(checkout.get("experiment_id") or "")
    if (
        checkout.get("status") != "active"
        or checkout.get("configured_by_human") is not True
        or checkout.get("provider") not in PUBLIC_CHECKOUT_PROVIDERS
        or not checkout_url
        or not opportunity_id
    ):
        return ""
    return opportunity_id


def _configured_checkout_url(
    config: Optional[Mapping[str, Any]],
    opportunity_id: str,
) -> str:
    if configured_checkout_opportunity_id(config) != opportunity_id:
        return ""
    return _public_https_url((config or {}).get("checkout_url"))


def _artifact_fingerprint(
    action_type: str,
    opportunity: Mapping[str, Any],
    checkout_url: str = "",
) -> str:
    payload = {
        "action_type": action_type,
        "opportunity_id": opportunity.get("opportunity_id"),
        "offer": opportunity.get("offer"),
        "buyer": opportunity.get("intended_buyer"),
        "price": opportunity.get("price"),
        "evidence_ids": opportunity.get("evidence_ids"),
    }
    if checkout_url:
        payload["checkout_url"] = checkout_url
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _github_issue_transport(
    method: str,
    url: str,
    payload: Optional[Mapping[str, Any]],
    token: str,
) -> Any:
    if not token:
        raise ValueError("GitHub issue execution requires a runtime token")
    if method not in {"GET", "POST"} or not url.startswith(GITHUB_API_PREFIX):
        raise ValueError("GitHub issue request is outside the capability allowlist")
    body = json.dumps(dict(payload)).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer {0}".format(token),
            "Content-Type": "application/json",
            "User-Agent": "AutonomousFounderAgent/0.4",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(  # nosec B310 - fixed repository API prefix
        request, timeout=25, context=verified_tls_context()
    ) as response:
        return json.load(response)


def _capability_grant(config: Mapping[str, Any], capability_id: str) -> Optional[Mapping[str, Any]]:
    for item in config.get("grants", []):
        if item.get("capability_id") == capability_id and item.get("enabled") is True:
            return item
    return None


def respond_to_inbound_interest(
    capability_config: Mapping[str, Any],
    tracker: BudgetTracker,
    *,
    github_token: Optional[str],
    transport: IssueTransport = _github_issue_transport,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Reply only to inbound interest on the configured repository, within budget."""

    now = observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    grant = _capability_grant(capability_config, "github_issue_inbound_reply")
    record: Dict[str, Any] = {
        "execution_id": "inbound-replies-{0}".format(now.strftime("%Y%m%dT%H%M%SZ")),
        "observed_at": now.isoformat(),
        "opportunity_id": "",
        "action_type": "respond_to_inbound_interest",
        "status": "not_configured",
        "reason": "The inbound-reply capability is not enabled.",
        "artifact_path": "",
        "artifact_url": "",
        "artifact_fingerprint": "",
        "external_effects": {
            "publications": 0,
            "messages": 0,
            "posts": 0,
            "emails": 0,
            "ads": 0,
            "wallet_transactions": 0,
            "nft_mints": 0,
            "spend_usd": 0.0,
        },
        "public_issue_numbers": [],
    }
    if grant is None or not github_token:
        if grant is not None:
            record["reason"] = "The grant is enabled, but no runtime GitHub token is available."
        return record
    if grant.get("repository") != GITHUB_REPOSITORY or grant.get("direction") != "inbound_only":
        record.update(status="blocked", reason="The capability grant is broader than the hard-coded inbound-only boundary.")
        return record

    configured_max = min(
        int(grant.get("max_per_cycle", 0)),
        int(tracker.remaining("external_messages")),
    )
    if configured_max < 1:
        record.update(status="budget_exhausted", reason="No inbound-message budget remains this cycle.")
        return record

    issues_url = GITHUB_API_PREFIX + "issues?state=open&labels=revenue-experiment&per_page=20"
    try:
        issues = transport("GET", issues_url, None, github_token)
    except Exception as exc:
        record.update(status="failed", reason="Inbound issue lookup failed: {0}".format(_text(exc, 220)))
        return record

    sent = 0
    for issue in issues if isinstance(issues, list) else []:
        if sent >= configured_max or not isinstance(issue, Mapping) or issue.get("pull_request"):
            continue
        number = issue.get("number")
        if not isinstance(number, int) or number < 1:
            continue
        comments_url = GITHUB_API_PREFIX + "issues/{0}/comments".format(number)
        try:
            comments = transport("GET", comments_url + "?per_page=100", None, github_token)
        except Exception:
            continue
        if any(
            RESPONSE_MARKER in str(comment.get("body", ""))
            for comment in comments if isinstance(comment, Mapping)
        ):
            continue
        comment_body = """{marker}
Thanks for registering a public-safe commercial signal. The Autonomous Founder Agent recorded this as interest, not as a customer or revenue.

Current opportunity details: https://vadim-koenen.github.io/autonomous-founder-agent/site/opportunities/latest.html

If the published outcome and price fit, reply with `scope fits`. If they do not, state the outcome or scope that would. Do not post credentials, private links, customer data, production logs, wallet details, or confidential information here.
""".format(marker=RESPONSE_MARKER)
        try:
            tracker.consume("external_messages")
            transport("POST", comments_url, {"body": comment_body}, github_token)
        except Exception:
            continue
        sent += 1
        record["public_issue_numbers"].append(number)

    record["external_effects"]["messages"] = sent
    record["external_effects"]["posts"] = sent
    if sent:
        record.update(
            status="executed",
            reason="Replied to {0} qualified inbound public issue(s) within the explicit owner grant.".format(sent),
        )
    else:
        record.update(status="no_pending_interest", reason="No unreplied inbound interest issue was available.")
    return record


def _render_validation_brief(
    opportunity: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    observed_at: str,
    checkout_url: str = "",
) -> str:
    evidence_by_id = {
        str(item.get("evidence_id")): item for item in evidence if item.get("evidence_id")
    }
    evidence_items = []
    for evidence_id in opportunity.get("evidence_ids", []):
        item = evidence_by_id.get(str(evidence_id))
        if not item:
            continue
        source_url = _public_https_url(item.get("source_url"))
        title = html.escape(_text(item.get("title"), 160))
        summary = html.escape(_text(item.get("summary"), 500))
        title_markup = '<a href="{0}">{1}</a>'.format(html.escape(source_url), title) if source_url else title
        evidence_items.append("<li><strong>{0}</strong><p>{1}</p></li>".format(title_markup, summary))

    validations = "".join(
        "<li>{0}</li>".format(html.escape(_text(item, 300)))
        for item in opportunity.get("validation_72h", [])[:8]
    )
    substitutes = "".join(
        "<li>{0}</li>".format(html.escape(_text(item, 220)))
        for item in opportunity.get("free_substitutes", [])[:8]
    )
    name = html.escape(_text(opportunity.get("name"), 150))
    offer = html.escape(_text(opportunity.get("offer"), 700))
    buyer = html.escape(_text(opportunity.get("intended_buyer"), 450))
    thesis = html.escape(_text(opportunity.get("thesis"), 700))
    acquisition = html.escape(_text(opportunity.get("acquisition_channel"), 500))
    rail = html.escape(_text(opportunity.get("payment_rail"), 400))
    price_data = opportunity.get("price", {})
    price = html.escape(_price_text(price_data))
    if checkout_url:
        amount = float(price_data.get("amount", 0))
        currency = _text(price_data.get("currency") or "USD", 12).upper()
        checkout_price = (
            "${0:g}".format(amount)
            if currency == "USD"
            else "{0:g} {1}".format(amount, currency)
        )
        checkout_label = (
            "Buy the full audit"
            if "audit" in _text(price_data.get("billing_model"), 80).lower()
            else "Buy now"
        )
        checkout_cta = (
            '<a class="cta" href="{0}" target="_blank" rel="noopener">{1} - {2}</a>'
        ).format(
            html.escape(checkout_url),
            html.escape(checkout_label),
            html.escape(checkout_price),
        )
        intake_label = "Ask about scope"
    else:
        checkout_cta = ""
        intake_label = "Register public-safe interest"
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{name} | Autonomous Founder Agent</title>
    <meta name="description" content="A bounded market-validation brief generated by the Autonomous Founder Agent.">
    <style>
      :root {{ --ink:#111; --paper:#f7f7f2; --line:#d8d8d0; --teal:#087f70; --coral:#d94c3d; --yellow:#f0bd35; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; color:var(--ink); background:var(--paper); font-family:Inter,ui-sans-serif,system-ui,sans-serif; line-height:1.55; }}
      a {{ color:inherit; text-underline-offset:3px; }}
      header {{ background:#101010; color:#fff; border-bottom:1px solid #2b2b2b; }}
      nav,main,footer div {{ width:min(920px,calc(100% - 36px)); margin:0 auto; }}
      nav {{ min-height:58px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
      nav a {{ font-size:.82rem; font-weight:800; text-decoration:none; }}
      .hero {{ padding:64px 0 48px; border-bottom:1px solid var(--line); background:#fff; }}
      .kicker {{ display:inline-block; padding:5px 8px; background:var(--yellow); font-size:.74rem; font-weight:900; text-transform:uppercase; }}
      h1 {{ max-width:800px; margin:16px 0 14px; font-size:clamp(2.2rem,8vw,4.4rem); line-height:1; letter-spacing:0; overflow-wrap:anywhere; }}
      .lede {{ max-width:760px; font-size:1.08rem; }}
      .meta {{ display:flex; flex-wrap:wrap; gap:10px 24px; margin-top:22px; color:#62625c; font-size:.82rem; }}
      section {{ padding:42px 0; border-bottom:1px solid var(--line); }}
      section.white {{ background:#fff; }}
      h2 {{ margin:0 0 18px; font-size:1.45rem; letter-spacing:0; }}
      .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:36px; }}
      dl {{ margin:0; }}
      dt {{ margin-top:15px; color:#62625c; font-size:.74rem; font-weight:850; text-transform:uppercase; }}
      dd {{ margin:4px 0 0; }}
      ul {{ margin:0; padding-left:20px; }}
      li + li {{ margin-top:10px; }}
      li p {{ margin:3px 0 0; color:#62625c; }}
      .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:22px; }}
      .cta {{ display:inline-flex; min-height:42px; align-items:center; padding:9px 14px; border-radius:4px; background:var(--ink); color:#fff; font-weight:800; text-decoration:none; }}
      .cta.secondary {{ border:1px solid var(--ink); background:transparent; color:var(--ink); }}
      .cta:hover,.cta:focus-visible {{ background:var(--teal); }}
      .cta.secondary:hover,.cta.secondary:focus-visible {{ border-color:var(--teal); color:#fff; }}
      .truth {{ border-left:5px solid var(--coral); padding-left:18px; }}
      footer {{ padding:30px 0; background:#101010; color:#d8d8d2; font-size:.8rem; }}
      @media (max-width:700px) {{ .grid {{ grid-template-columns:1fr; }} .hero {{ padding-top:46px; }} }}
    </style>
  </head>
  <body>
    <header><nav><a href="../index.html">Autonomous Founder Agent</a><a href="../../data/discovered_opportunities.json">Machine-readable pool</a></nav></header>
    <main>
      <div class="hero">
        <span class="kicker">Live opportunity test</span>
        <h1>{name}</h1>
        <p class="lede">{offer}</p>
        <div class="actions">{checkout_cta}<a class="cta secondary" href="{intake}">{intake_label}</a></div>
        <div class="meta"><span>Price hypothesis: {price}</span><span>Observed {observed_at}</span></div>
      </div>
      <section><div class="grid"><div><h2>Who Pays</h2><p>{buyer}</p><h2>Why Now</h2><p>{thesis}</p></div><div><h2>Commercial Route</h2><dl><dt>Discovery</dt><dd>{acquisition}</dd><dt>Payment rail</dt><dd>{rail}</dd></dl></div></div></section>
      <section class="white"><div class="grid"><div><h2>Demand Evidence</h2><ul>{evidence}</ul></div><div><h2>Free Substitutes</h2><ul>{substitutes}</ul></div></div></section>
      <section><div class="grid"><div><h2>72-Hour Proof</h2><ul>{validations}</ul></div><div class="truth"><h2>What This Page Proves</h2><p>This is a public demand test, not evidence of a customer or payment. Revenue remains zero until a completed transaction is independently recorded in the verified ledger.</p></div></div></section>
    </main>
    <footer><div>Generated through one allowlisted publication action. No messages, ads, wallet transactions, NFT mints, purchases, or owner-funded spend occurred.</div></footer>
  </body>
</html>
""".format(
        name=name,
        offer=offer,
        buyer=buyer,
        thesis=thesis,
        acquisition=acquisition,
        rail=rail,
        price=price,
        observed_at=html.escape(observed_at),
        evidence="".join(evidence_items) or "<li>No validated evidence was available.</li>",
        substitutes=substitutes or "<li>No substitute analysis was supplied.</li>",
        validations=validations or "<li>Collect one qualified public interest signal.</li>",
        checkout_cta=checkout_cta,
        intake=html.escape(PUBLIC_INTAKE_URL),
        intake_label=intake_label,
    )


def _build_public_prospects(snapshot: Mapping[str, Any], observed_at: str) -> Dict[str, Any]:
    prospects: List[Dict[str, Any]] = []
    seen_urls = set()
    for source in snapshot.get("sources", []):
        for item in source.get("items", []):
            if not isinstance(item, Mapping):
                continue
            url = _public_https_url(item.get("url"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = item.get("title") or item.get("name") or item.get("repository") or urlparse(url).netloc
            prospects.append(
                {
                    "target_id": "public-target-{0:02d}".format(len(prospects) + 1),
                    "name": _text(title, 180),
                    "public_url": url,
                    "source_id": str(source.get("source_id", "")),
                    "contact_status": "not_contacted",
                    "external_action_performed": False,
                }
            )
            if len(prospects) >= 25:
                break
        if len(prospects) >= 25:
            break
    return {
        "schema_name": "autonomous_founder_public_research_targets",
        "schema_version": "0.4",
        "observed_at": observed_at,
        "outreach_status": "No messages, posts, proposals, or applications were sent.",
        "targets": prospects,
    }


def execute_bounded_action(
    root: Path,
    synthesis: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    channel_registry: Mapping[str, Any],
    tracker: BudgetTracker,
    *,
    eligible_opportunity_ids: Sequence[str],
    priority_opportunity_ids: Sequence[str] = (),
    opportunity_catalog: Optional[Sequence[Mapping[str, Any]]] = None,
    evidence_catalog: Optional[Sequence[Mapping[str, Any]]] = None,
    checkout_config: Optional[Mapping[str, Any]] = None,
    capability_config: Optional[Mapping[str, Any]] = None,
    previous_log: Optional[Mapping[str, Any]] = None,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Execute at most one allowlisted repository publication and nothing transactional."""

    now = observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    now_text = now.isoformat()
    selected = synthesis.get("selected_execution", {})
    requested_action_type = str(selected.get("action_type") or "monitor_signal")
    requested_opportunity_id = str(selected.get("opportunity_id") or "")
    opportunities: Dict[str, Mapping[str, Any]] = {}
    for item in synthesis.get("opportunities", []):
        if isinstance(item, Mapping) and item.get("opportunity_id"):
            opportunities[str(item["opportunity_id"])] = item
    for item in opportunity_catalog or []:
        if isinstance(item, Mapping) and item.get("opportunity_id"):
            opportunities[str(item["opportunity_id"])] = item

    eligible_ids = list(dict.fromkeys(str(item) for item in eligible_opportunity_ids if item))
    eligible_set = set(eligible_ids)
    priority_ids = [
        item
        for item in dict.fromkeys(str(item) for item in priority_opportunity_ids if item)
        if item in eligible_set
    ]
    record: Dict[str, Any] = {
        "execution_id": "execution-{0}".format(now.strftime("%Y%m%dT%H%M%SZ")),
        "observed_at": now_text,
        "opportunity_id": requested_opportunity_id,
        "action_type": requested_action_type,
        "requested_opportunity_id": requested_opportunity_id,
        "requested_action_type": requested_action_type,
        "selection_mode": "none",
        "status": "observed_only",
        "reason": _text(selected.get("reason"), 500) or "No allowlisted action selected.",
        "artifact_path": "",
        "artifact_url": "",
        "artifact_fingerprint": "",
        "external_effects": {
            "publications": 0,
            "messages": 0,
            "posts": 0,
            "emails": 0,
            "ads": 0,
            "wallet_transactions": 0,
            "nft_mints": 0,
            "spend_usd": 0.0,
        },
    }
    channels = load_channels(channel_registry)
    publication_grant = _capability_grant(
        capability_config or {},
        "github_pages_publication",
    )
    prior_records = list((previous_log or {}).get("executions", []))
    prior_fingerprints = {
        str(item.get("artifact_fingerprint"))
        for item in prior_records
        if item.get("artifact_fingerprint")
    }

    candidates: List[tuple[str, str, str]] = []
    for opportunity_id in priority_ids:
        action_type = (
            requested_action_type
            if opportunity_id == requested_opportunity_id
            and requested_action_type in PUBLICATION_ACTIONS
            else "publish_validation_brief"
        )
        candidates.append((opportunity_id, action_type, "priority_experiment"))
    if requested_opportunity_id and requested_opportunity_id not in priority_ids:
        candidates.append(
            (requested_opportunity_id, requested_action_type, "model_selected")
        )
    for opportunity_id in eligible_ids:
        if opportunity_id in priority_ids or opportunity_id == requested_opportunity_id:
            continue
        candidates.append((opportunity_id, "publish_validation_brief", "eligible_fallback"))

    rejection_reasons: List[str] = []
    duplicate_count = 0
    opportunity: Optional[Mapping[str, Any]] = None
    opportunity_id = ""
    action_type = "monitor_signal"
    selection_mode = "none"
    fingerprint = ""
    checkout_url = ""
    for candidate_id, candidate_action, candidate_mode in candidates:
        candidate = opportunities.get(candidate_id)
        if candidate_id not in eligible_set:
            rejection_reasons.append("{0} is outside the execution eligibility set".format(candidate_id))
            continue
        if candidate_action not in PUBLICATION_ACTIONS or candidate is None:
            rejection_reasons.append("{0} has no allowlisted publication action".format(candidate_id))
            continue
        channel_id = str(candidate.get("next_action_channel_id", ""))
        channel = channels.get(channel_id)
        if not channel or "publishing" not in channel.kinds:
            rejection_reasons.append("{0} has no connected publishing channel".format(candidate_id))
            continue
        if (
            publication_grant is None
            or publication_grant.get("channel_id") != channel_id
            or isinstance(publication_grant.get("max_per_cycle"), bool)
            or not isinstance(publication_grant.get("max_per_cycle"), int)
            or publication_grant.get("max_per_cycle", 0) < 1
        ):
            rejection_reasons.append(
                "{0} has no explicit publication capability grant".format(candidate_id)
            )
            continue
        permission = plan_channel_action(
            action_id=record["execution_id"],
            experiment_id=candidate_id,
            description=str(candidate.get("next_executable_action", "")),
            channel_id=channel_id,
            authority_class=str(candidate.get("next_action_authority_class", "")),
            channels=channels,
        )
        if not permission.executable_now:
            rejection_reasons.append("{0}: {1}".format(candidate_id, permission.blocked_reason))
            continue
        candidate_checkout_url = _configured_checkout_url(checkout_config, candidate_id)
        candidate_fingerprint = _artifact_fingerprint(
            candidate_action,
            candidate,
            candidate_checkout_url,
        )
        if candidate_fingerprint in prior_fingerprints:
            duplicate_count += 1
            rejection_reasons.append("{0} already has an identical published asset".format(candidate_id))
            continue
        opportunity = candidate
        opportunity_id = candidate_id
        action_type = candidate_action
        selection_mode = candidate_mode
        fingerprint = candidate_fingerprint
        checkout_url = candidate_checkout_url
        break

    if opportunity is None:
        reason = "; ".join(rejection_reasons[:5]) or "No eligible publication candidate was available."
        if duplicate_count:
            record.update(
                status="skipped_duplicate",
                reason="No new eligible distribution asset was available: {0}.".format(reason),
            )
        elif requested_action_type == "monitor_signal" and not candidates:
            record["reason"] = _text(selected.get("reason"), 500) or reason
        else:
            record.update(status="blocked", reason=reason)
        return record

    model_request_executed = (
        requested_opportunity_id == opportunity_id
        and requested_action_type == action_type
        and requested_action_type in PUBLICATION_ACTIONS
    )
    if model_request_executed:
        execution_reason = (
            _text(selected.get("reason"), 500)
            or "Executed the validated model selection."
        )
    else:
        requested_reason = (
            "the model-selected action was not executable"
            if requested_opportunity_id
            else "the model did not select an executable publication"
        )
        execution_reason = (
            "Published the highest-priority eligible experiment because {0}."
        ).format(requested_reason)
    record.update(
        opportunity_id=opportunity_id,
        action_type=action_type,
        selection_mode=selection_mode,
        reason=execution_reason,
        artifact_fingerprint=fingerprint,
    )

    tracker.consume("publications")
    tracker.consume("repository_writes")
    if action_type == "publish_validation_brief":
        path = root / "site" / "opportunities" / "latest.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _render_validation_brief(
                opportunity,
                evidence_catalog if evidence_catalog is not None else synthesis.get("evidence", []),
                now_text,
                checkout_url,
            ),
            encoding="utf-8",
        )
        artifact_url = (
            "https://vadim-koenen.github.io/autonomous-founder-agent/site/opportunities/latest.html"
        )
    else:
        path = root / "data" / "dynamic_prospect_targets.json"
        path.write_text(
            json.dumps(_build_public_prospects(snapshot, now_text), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        artifact_url = (
            "https://vadim-koenen.github.io/autonomous-founder-agent/data/dynamic_prospect_targets.json"
        )
    record.update(
        status="published",
        artifact_path=str(path.relative_to(root)),
        artifact_url=artifact_url,
        artifact_fingerprint=fingerprint,
    )
    record["external_effects"]["publications"] = 1
    return record


def append_execution_log(
    previous_log: Optional[Mapping[str, Any]],
    record: Mapping[str, Any],
) -> Dict[str, Any]:
    executions = list((previous_log or {}).get("executions", []))
    executions.append(dict(record))
    return {
        "schema_name": "autonomous_founder_execution_log",
        "schema_version": "0.4",
        "last_updated": record.get("observed_at", ""),
        "executions": executions[-100:],
        "notes": [
            "Control-plane state writes are audited separately from the one commercial publication budget.",
            "External actions execute only through explicit capability grants and per-cycle limits.",
            "Email, ads, wallet transactions, NFT mints, and spend remain unavailable until their exact capabilities are connected and granted.",
        ],
    }
