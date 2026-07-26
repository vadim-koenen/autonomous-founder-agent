# vadimkoenen.com Multichannel Promotion Engine

## Outcome

This subsystem turns Apollo exports and public research into a reviewable,
measurable promotion queue for `vadimkoenen.com`. It does not send email,
activate sequences, automate LinkedIn, or treat funnel activity as revenue.

The 30-day target is 12 qualified prospects, three systems-review requests, one
ledger-verified customer, and at least $100 in verified revenue at $0 owner
spend. These are targets, not forecasts.

## Architecture

1. **Discover** — Prepare an Apollo People Search or import an owner-exported
   CSV. API search is disabled until a scoped key and capability grant exist.
2. **Qualify** — Deterministically score title, seniority, stack, company size,
   industry, evidence quality, and email verification. A score is a review
   priority, never a conversion probability.
3. **Policy gate** — Require a U.S. business prospect, verified work email,
   public HTTPS source, specific evidence, and one person per company. Block
   suppression matches, free/role inboxes, customers, and active opportunities.
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
python3 -m promotion_engine.cli export-apollo
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

## CSV Fields

The importer accepts common Apollo labels and normalized snake-case fields:

`first_name`, `last_name`, `email`, `email_status`, `title`, `seniority`,
`company`, `company_domain`, `company_size`, `country`, `industry`,
`technologies`, `source_url`, `evidence_note`, `apollo_person_id`, and
`apollo_contact_id`.

Add `source_url` and `evidence_note` during research if the Apollo export does
not contain them. Records without them remain `review_required`.

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

## Activation Checklist

Email sending remains blocked until all of these are verified:

- A dedicated sending domain and mailbox are authenticated and warmed.
- Legal sender name and a valid physical postal address are present.
- Apollo unsubscribe links render in every step and reply-based opt-outs are
  processed.
- Apollo rules stop a sequence on reply, unsubscribe, and bounce.
- Existing customers, active opportunities, DNC records, and suppressions sync
  before every enrollment.
- The sequence is reviewed inactive, contacts enter paused, and daily/hourly
  limits are deliberately configured.
- The owner confirms API plan entitlements and a per-cycle ceiling.

LinkedIn remains owner-reviewed and manual: no automated posts, comments,
connection requests, or direct messages.
