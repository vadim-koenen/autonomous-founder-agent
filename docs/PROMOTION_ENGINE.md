# vadimkoenen.com Multichannel Promotion Engine

## Outcome

This subsystem turns Apollo exports and public research into a reviewable,
measurable promotion queue for `vadimkoenen.com`. It does not send email,
activate sequences, automate LinkedIn, or treat funnel activity as revenue.

The 30-day target is 12 qualified prospects, three systems-review requests, one
ledger-verified customer, and at least $100 in verified revenue at $0 owner
spend. These are targets, not forecasts.

The active pilot lane is `marketo_repair`. The other configured lanes remain
available for later experiments but are excluded from qualification until the
campaign configuration explicitly activates them.

## Architecture

1. **Discover** — Prepare an Apollo People Search or import an owner-exported
   CSV. API search is disabled until a scoped key and capability grant exist.
2. **Qualify** — Deterministically score title, seniority, stack, company size,
   industry, evidence quality, and email verification. A score is a review
   priority, never a conversion probability.
3. **Policy gate** — Require a U.S. business prospect, verified work email,
   public HTTPS source, specific evidence, and one person per company. Block
   suppression matches, free/role inboxes, existing CRM contacts, customers,
   and active opportunities.
4. **Draft** — Create a three-touch Apollo email sequence or an owner-reviewed
   manual LinkedIn research task. Personalization uses only the supplied
   evidence note.
5. **Approve** — A named human reviewer approves each draft or the campaign
   batch. Unapproved records cannot be exported.
6. **Export** — Write PII-bearing review files only under
   `.promotion-private/`. Exporting marks drafts `exported`; it never marks them
   sent.
7. **Measure** — Import evidence-backed delivery, reply, meeting, request, and
   checkout events. Only completed transactions in `data/revenue_ledger.json`
   count as revenue.

## Quick Start

```bash
python3 -m promotion_engine.cli init
python3 -m promotion_engine.cli import-suppressions \
  --csv .promotion-private/hubspot-contact-suppressions.csv \
  --scope crm_contacts \
  --source "HubSpot contact snapshot YYYY-MM-DD"
python3 -m promotion_engine.cli import-suppressions \
  --csv .promotion-private/hubspot-commercial-suppressions.csv \
  --scope crm_commercial_relationships \
  --source "HubSpot customer and opportunity snapshot YYYY-MM-DD"
python3 -m promotion_engine.cli import-suppressions \
  --csv .promotion-private/apollo-delivery-suppressions.csv \
  --scope apollo_delivery_suppressions \
  --source "Apollo unsubscribe, bounce, and DNC snapshot YYYY-MM-DD"
python3 -m promotion_engine.cli import-apollo --csv .promotion-private/apollo.csv
python3 -m promotion_engine.cli qualify
python3 -m promotion_engine.cli draft --channel apollo_email
python3 -m promotion_engine.cli draft --channel linkedin_manual_task
python3 -m promotion_engine.cli review-queue
python3 -m promotion_engine.cli report
```

Open the private review-queue CSV and verify the source, evidence, recipient,
subject, body, CTA, and suppression status before approval. Then:

```bash
python3 -m promotion_engine.cli approve --draft-id DRAFT_ID --reviewer "Vadim Koenen"
# Or approve one prospect's reviewed three-touch sequence:
python3 -m promotion_engine.cli approve --prospect-id PROSPECT_ID \
  --channel apollo_email --reviewer "Vadim Koenen"
# Or approve only one reviewed channel batch:
python3 -m promotion_engine.cli approve --all --channel apollo_email \
  --reviewer "Vadim Koenen"
python3 -m promotion_engine.cli export-apollo
python3 -m promotion_engine.cli activation-preflight
```

The generated CSV is an approved worksheet containing contact fields and
sequence copy. Build the corresponding Apollo sequence as **inactive**, verify
mailbox and compliance settings, and keep contacts paused. No command in this
repository activates or sends a sequence.

## Apollo API Boundary

Use `APOLLO_API_KEY` only as an environment variable. Never place it in JSON,
CSV, shell history, source control, or screenshots.

```bash
APOLLO_API_KEY=... python3 -m promotion_engine.cli apollo-health
```

People Search and enrichment additionally require the
`apollo_read_and_enrich` capability to be enabled. Enrichment also requires
`APOLLO_ENRICHMENT_ENABLED=true` because it may consume credits. Contact
creation requires both an enabled `apollo_contact_sync` grant and
`APOLLO_WRITE_ENABLED=true`; it always requests Apollo deduplication. Paused
sequence enrollment requires a separate grant and environment flag. Sequence
activation is deliberately not implemented.

Apollo search/enrichment filter JSON and result files must both remain under
`.promotion-private/`. The CLI validates and prepares those paths before making
an API request so an unsafe destination cannot consume an enrichment credit.

## CSV Fields

The importer accepts common Apollo labels and normalized snake-case fields:

`first_name`, `last_name`, `email`, `email_status`, `title`, `seniority`,
`company`, `company_domain`, `company_size`, `country`, `industry`,
`technologies`, `source_url`, `evidence_note`, `apollo_person_id`, and
`apollo_contact_id`.

Add `source_url` and `evidence_note` during research if the Apollo export does
not contain them. Records without them remain `review_required`.
Apollo and suppression CSVs must remain under `.promotion-private/`; the CLI
rejects tracked repository paths. Re-importing a prospect invalidates its score,
drafts, and approvals. Export also re-runs qualification and refreshes draft
copy, returning changed copy to review. Export revalidates the stored reviewer
against the current approver allowlist and returns revoked approvals to draft.

## Suppression and Event Evidence

```bash
python3 -m promotion_engine.cli suppress \
  --email person@example.com \
  --reason do_not_contact \
  --evidence "Apollo DNC export 2026-07-26"

python3 -m promotion_engine.cli record-event \
  --prospect-id INTERNAL_ID \
  --event replied \
  --channel apollo_email \
  --evidence "Apollo activity ID or private export reference" \
  --occurred-at 2026-07-26T15:00:00Z
```

Unsubscribe and bounce events automatically add a hashed suppression entry.
Do not use URL query parameters for prospect IDs or emails.

Bulk suppression snapshots use the columns `email`, `reason`, and
`evidence_reference`. A successful import records snapshot freshness for
`activation-preflight`. Header-only files are valid when an authoritative source
has zero records. The three required scopes are CRM contacts, CRM
customer/opportunity relationships, and Apollo delivery suppressions. Legacy
unscoped metadata does not satisfy the preflight.

Every suppression observation is retained in immutable history. The effective
suppression applies precedence so a later CRM-contact snapshot cannot downgrade
an unsubscribe or DNC record. Imports never remove prior opt-outs.

## Activation Checklist

Email sending remains blocked until all of these are verified:

- A dedicated sending domain and mailbox are authenticated and warmed.
- Legal sender name and a valid physical postal address are present.
- Apollo unsubscribe links render in every step and reply-based opt-outs are
  processed.
- Apollo rules stop a sequence on reply, unsubscribe, and bounce.
- Existing customers, active opportunities, DNC records, and suppressions sync
  before every enrollment.
- Existing CRM contacts are suppressed separately from DNC records so the
  evidence trail remains accurate and duplicate outreach cannot occur.
- A fresh bulk suppression snapshot is present (24 hours maximum by default).
- All three suppression scopes are fresh; one partial source cannot clear
  preflight.
- The sequence is reviewed inactive, contacts enter paused, and daily/hourly
  limits are deliberately configured.
- The central `commercial_email_or_dm` capability grant is enabled with a
  positive per-cycle ceiling. The effective daily limit is the lower of that
  ceiling and the campaign limit.
- The owner confirms API plan entitlements and a per-cycle enrichment ceiling.

LinkedIn remains owner-reviewed and manual: no automated posts, comments,
connection requests, or direct messages.

The exact mailbox, authentication, compliance, and rate-limit procedure is in
`campaigns/vadimkoenen-visibility-2026/SENDER_ACTIVATION.md`.
