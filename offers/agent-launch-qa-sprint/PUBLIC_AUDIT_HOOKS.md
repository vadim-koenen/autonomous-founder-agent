# Public Metadata Audit Hooks

These are tailored validation hooks based only on public x402 Bazaar metadata observed on 2026-07-09. They are not defect reports, endorsements, customer claims, or evidence that the operators want to buy anything.

No endpoint call, payment, contact, message, proposal, or transaction was performed.

## x402 Entity-ID Resolver

Public resource: https://entityresolver.xyz/resolve

Observed contract:

- GET input with a `q` query field
- JSON candidate output with confidence, entity kind, IDs, and sources
- public payment metadata for Base USDC

Launch-gate hook:

The public JSON Schema requires `type` and `method` at the input level, while `q` is required only inside the optional `queryParams` object. A safe test pass should determine whether an input with omitted `queryParams`, blank `q`, ambiguous ticker, Unicode entity name, and unsupported entity produces contract-consistent errors rather than an undocumented result shape.

Evidence needed before making a finding:

- schema validation result for each malformed input
- HTTP and x402 challenge behavior without sending payment
- documented error body shape
- repeatability across at least two ambiguous names

## makesPDF

Public resource: https://makespdf.com/api/v1/markdown

Observed contract:

- POST, PUT, or PATCH JSON body with Markdown and options
- binary output advertised as tagged accessible PDF
- public payment metadata for Base USDC

Launch-gate hook:

A safe test pass should compare the advertised binary output contract with response content type and failure bodies, then exercise empty Markdown, malformed options, unsupported page size, oversized input, Unicode, tables, images, and links. Accessibility and archival claims require artifact inspection; they must not be inferred from a successful HTTP response.

Evidence needed before making a finding:

- response content type and status for each case
- parseable PDF artifact after an authorized paid test
- PDF/UA and PDF/A validator output for an authorized artifact
- stable failure shape for invalid input

## Minifetch Technical SEO API

Public resource: https://minifetch.com/api/v1/x402/run/seo-page-audit

Observed contract:

- GET input with a required `url` inside query parameters
- structured pass, warning, and failure sections
- documented deterministic threshold reference
- public payment metadata for Base and Solana USDC

Launch-gate hook:

The public JSON Schema requires `type` and `method` at the input level, while `url` is required only inside the optional `queryParams` object. A safe test pass should check missing URL, malformed URL, redirect loop, blocked robots policy, timeout, non-HTML response, very large page, and partial upstream failure, then compare the result to the published threshold documentation.

Evidence needed before making a finding:

- schema result and HTTP behavior for malformed inputs
- explicit timeout and partial-result behavior
- stable status and error shape
- reproducible mapping from one documented threshold to the returned pass/warn/fail value

## Use Boundary

These hooks may be turned into actual findings only after the endpoint operator or an authorized buyer approves any paid calls and scope. Public counters and metadata alone do not prove a bug, purchase intent, or revenue.
