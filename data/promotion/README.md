# Promotion Data Boundary

This directory contains public-safe documentation only.

Prospect names, emails, Apollo identifiers, evidence notes, drafts tied to a
person, suppressions, and exports belong in `.promotion-private/`. That directory
is ignored by Git. Never copy its contents into `data/`, logs, issues, commits,
analytics URLs, or public dashboards.

The public revenue source of truth remains `data/revenue_ledger.json`. Promotion
events are funnel signals and do not modify or replace that ledger.
