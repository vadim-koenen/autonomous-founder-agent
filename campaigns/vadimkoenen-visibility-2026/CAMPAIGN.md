# Marketo–Salesforce Trust Repair — 30-Day Campaign

## Campaign overview

Create qualified visibility for `vadimkoenen.com` by diagnosing the
Marketo-to-Salesforce handoff before recommending a rebuild.

Primary objective: produce one ledger-verified customer and at least $100 in
verified revenue within 30 days.

Secondary objectives:

- Research 30 companies and qualify 12 evidence-backed prospects.
- Produce at least five meaningful replies and three systems-review requests.
- Learn which observable system trigger and diagnostic asset create useful
  conversations before expanding to another segment.

Budget: $0. Paid media, sponsorships, and new outreach vendors are deferred.

## Target audience

Primary audience: directors, heads, and VPs in Marketing Operations or Revenue
Operations at U.S. B2B software, security, and technology organizations with
roughly 200–5,000 employees.

Required evidence:

- Internal use of both Marketo and Salesforce, supported by a current public
  source.
- A business-relevant trigger such as lifecycle ownership, sync health,
  attribution, scoring, routing, migration, or systems hiring.
- One verified work email and no CRM, customer, opportunity, bounce,
  unsubscribe, or DNC suppression match.

Audience pain: the systems appear operational, but lifecycle, routing, and
attribution decisions cannot be trusted across the MAP-to-CRM boundary.

Buying stage: problem-aware and evaluating whether the issue needs repair,
governance, or a larger rebuild.

ABM activation and lifecycle-governance segments are deliberately deferred
until this lane produces evidence that justifies expansion.

## Message hierarchy

Core message: diagnose the Marketo-to-Salesforce handoff before spending on a
rebuild.

Supporting messages:

1. Lifecycle and routing defects usually cross system ownership boundaries.
2. A bounded review can trace the signal, owner, rule, field, and downstream
   consequence before new tooling is proposed.
3. The work is evidence-led: public relevance is verified before outreach, and
   the engagement begins with a concrete diagnostic.
4. The next step is a short systems review, not a vague transformation pitch.

Primary proof path: `/case-studies/6sense-marketo-mitel/`.
Primary landing path: `/marketo-consultant/`.
Primary value bridge: `/revenue-systems-trust-score/`.

## Channel strategy

| Channel | Why it fits | Format and cadence | Effort | Operating boundary |
| --- | --- | --- | --- | --- |
| Apollo | Finds the narrow buying role and verified work contact | Public research first; enrich only final candidates; at most one person per company | Medium | No sequence activation or send until preflight passes |
| vadimkoenen.com | Holds proof, diagnostic value, and the conversion path | One landing lane, one proof page, one systems-review CTA | Low | Preserve allowlisted UTMs; never place PII in URLs |
| LinkedIn | Builds ambient credibility with the same operators | Two useful posts and roughly nine substantive manual comments weekly | Medium | No automated posts, scraping, connection requests, comments, or DMs |
| Partner/referral | Borrows trust from adjacent consultants and former colleagues | Two individualized introduction requests weekly | Medium | No bulk requests; record only qualified introductions |
| Search/editorial | Compounds the objections found in research and replies | Improve one high-intent page or diagnostic asset weekly | Medium | No thin programmatic page factory |
| HubSpot | Provides CRM and suppression truth | Read before each cohort; record opted-in inbound and opportunities | Low | Cold provider-sourced leads are not HubSpot marketing-email recipients |

No additional email vendor, Sales Navigator, cold calling, SMS, paid media,
newsletter, or automated LinkedIn tooling is needed for the first test.

## Operating phases

### Phase 0 — activation gate

- Preserve campaign attribution through `/contact/` and Calendly.
- Import a current CRM suppression snapshot.
- Verify the exact outbound mailbox at message level: SPF, aligned DKIM, and
  DMARC.
- Configure truthful sender identity, physical postal address, unsubscribe,
  reply, bounce, and stop-on-response rules.
- Create the Apollo sequence inactive with contacts paused.

Safe send volume remains zero until every gate passes.

### Phase 1 — five-recipient pilot

- Research 10–15 companies and enrich no more than five final candidates.
- Review the evidence, recipient, subject, body, CTA, and suppression status.
- Send at most five first touches in one weekday, no more than two per hour and
  at least ten minutes apart.
- Use replies and systems-review requests as decision signals; ignore opens.

### Phase 2 — controlled continuation

Continue toward 25 first touches at five per weekday only when authentication
holds, complaints remain zero, and hard bounces remain at or below 2%.

Increase to ten per weekday only after five healthy business days. Pause after
25 delivered first touches if fewer than two meaningful replies arrive; change
targeting or message rather than volume. The absolute 30-day first-touch ceiling
is 50.

## Content and assets

Must-have:

- Marketo consultant landing page with end-to-end campaign attribution.
- Case-study proof path and Revenue Systems Trust Score value bridge.
- Three-touch email sequence with inactive/paused Apollo setup.
- Eight LinkedIn post briefs and a manual-comment queue.
- Partner/referral request brief.
- Private suppression snapshot, review queue, event evidence, and revenue
  ledger.

The week-by-week production and distribution schedule is in
`CONTENT_CALENDAR.md`.

## Success metrics

| Metric | 30-day target | Source of truth |
| --- | ---: | --- |
| Researched companies | 30 | Public research ledger |
| Qualified verified prospects | 12 | Private promotion database |
| First-touch emails | 25 initial; 50 absolute max | Apollo evidence events |
| Meaningful replies | 5 | Evidence-backed reply events |
| Systems-review requests | 3 | HubSpot plus promotion events |
| Verified customers | 1 | Revenue ledger |
| Verified gross revenue | At least $100 | Revenue ledger |
| Hard bounce rate | At or below 2% | Apollo delivery evidence |
| Spam complaints | 0 | Sender/Apollo evidence |

Reporting cadence: review every weekday during an active send phase and make one
target/message decision weekly. Traffic, clicks, meetings, and checkout opens
are funnel signals; only completed, verification-backed ledger transactions are
revenue.

## Risks and mitigations

- Weak internal-stack evidence: reject before enrichment; product integrations
  and generic content do not prove internal use.
- Sender reputation damage: keep volume at zero until authentication and
  compliance gates pass, then start at five reviewed messages per day.
- Duplicate or inappropriate outreach: import a fresh suppression snapshot and
  re-run policy immediately before export.
- Creepy personalization: use only public, business-relevant evidence and cap
  the evidence note.
- Channel-policy breach: keep LinkedIn activity manual and cold leads out of
  HubSpot Marketing Email.
- False success claims: reconcile revenue only to the ledger.

## Immediate next decisions

1. Keep the verified attribution path live and use its allowlisted UTMs for
   every campaign link.
2. Confirm or replace the outbound mailbox; the current partial Gmail setup is
   not sufficient for `vadim@vadimkoenen.net`.
3. Review the five qualified private records and 20 draft actions without
   approving or exporting them while the sender and Apollo delivery-suppression
   gates remain blocked.
4. Publish the prepared LinkedIn material and use the partner/referral
   templates only after an individual human relevance and voice review; keep
   all activity manual.
