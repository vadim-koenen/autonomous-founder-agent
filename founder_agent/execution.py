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


def _artifact_fingerprint(action_type: str, opportunity: Mapping[str, Any]) -> str:
    payload = {
        "action_type": action_type,
        "opportunity_id": opportunity.get("opportunity_id"),
        "offer": opportunity.get("offer"),
        "buyer": opportunity.get("intended_buyer"),
        "price": opportunity.get("price"),
        "evidence_ids": opportunity.get("evidence_ids"),
    }
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
    price = html.escape(_price_text(opportunity.get("price", {})))
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
      .cta {{ display:inline-flex; min-height:42px; align-items:center; margin-top:22px; padding:9px 14px; border-radius:4px; background:var(--ink); color:#fff; font-weight:800; text-decoration:none; }}
      .cta:hover,.cta:focus-visible {{ background:var(--teal); }}
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
        <a class="cta" href="{intake}">Register public-safe interest</a>
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
        intake=html.escape(PUBLIC_INTAKE_URL),
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
    previous_log: Optional[Mapping[str, Any]] = None,
    observed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Execute at most one allowlisted repository publication and nothing transactional."""

    now = observed_at or datetime.now(timezone.utc).replace(microsecond=0)
    now_text = now.isoformat()
    selected = synthesis.get("selected_execution", {})
    action_type = str(selected.get("action_type") or "monitor_signal")
    opportunity_id = str(selected.get("opportunity_id") or "")
    opportunities = {
        str(item.get("opportunity_id")): item
        for item in synthesis.get("opportunities", [])
        if isinstance(item, Mapping) and item.get("opportunity_id")
    }
    opportunity = opportunities.get(opportunity_id)
    record: Dict[str, Any] = {
        "execution_id": "execution-{0}".format(now.strftime("%Y%m%dT%H%M%SZ")),
        "observed_at": now_text,
        "opportunity_id": opportunity_id,
        "action_type": action_type,
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
    if action_type == "monitor_signal":
        return record
    if action_type not in PUBLICATION_ACTIONS or opportunity is None:
        record.update(status="blocked", reason="The requested action or opportunity did not pass the execution allowlist.")
        return record
    if opportunity_id not in set(eligible_opportunity_ids):
        record.update(status="blocked", reason="The selected opportunity was not in the current portfolio or top-three score set.")
        return record

    channels = load_channels(channel_registry)
    channel_id = str(opportunity.get("next_action_channel_id", ""))
    channel = channels.get(channel_id)
    if not channel or "publishing" not in channel.kinds:
        record.update(status="blocked", reason="The selected opportunity does not use a connected publishing channel.")
        return record
    permission = plan_channel_action(
        action_id=record["execution_id"],
        experiment_id=opportunity_id,
        description=str(opportunity.get("next_executable_action", "")),
        channel_id=channel_id,
        authority_class=str(opportunity.get("next_action_authority_class", "")),
        channels=channels,
    )
    if not permission.executable_now:
        record.update(status="blocked", reason=permission.blocked_reason)
        return record

    fingerprint = _artifact_fingerprint(action_type, opportunity)
    prior_records = list((previous_log or {}).get("executions", []))
    if any(item.get("artifact_fingerprint") == fingerprint for item in prior_records):
        record.update(
            status="skipped_duplicate",
            reason="An identical validation asset is already published; the cycle preserved its execution budget.",
            artifact_fingerprint=fingerprint,
        )
        return record

    tracker.consume("publications")
    tracker.consume("repository_writes")
    if action_type == "publish_validation_brief":
        path = root / "site" / "opportunities" / "latest.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _render_validation_brief(opportunity, synthesis.get("evidence", []), now_text),
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
