# MCP / Agent Preflight Full Audit

## Outcome

Within 48 hours, one working AI agent, MCP server, or LLM workflow receives a launch-focused test pass, a prioritized defect report, and one agreed repair patch.

## Founding Price

$149 fixed scope.

The buyer-ready offer page and owner-configured public Stripe checkout are active. The repository stores only the public Payment Link; Stripe account access, refunds, payouts, identity, tax, and bank controls remain human-owned.

Offer page: https://vadim-koenen.github.io/autonomous-founder-agent/site/qa-sprint.html

## Buyer

Indie AI product founders and small teams with a working build approaching launch. This is not for idea-stage strategy work or open-ended application development.

## Deliverable

- 25 test cases covering core task success, malformed input, unavailable tools, partial results, timeout behavior, schema conformance, grounding, permissions, and recovery
- reproducible observations with severity and evidence
- prioritized launch recommendation: pass, conditional pass, or block
- one agreed repair patch within the existing project scope
- rerun of affected cases after the patch
- concise handoff with remaining risks

## Scope Boundary

- one agent or workflow
- one repository or public endpoint
- no production credentials in public intake
- no destructive tests
- no penetration testing or security certification
- no legal, regulatory, medical, or financial certification
- no guarantee of revenue, platform approval, or defect-free operation

## Safe Authorization And Access

1. After checkout, the buyer uses the public contact on the offer page to identify the project without sending credentials or private repository URLs.
2. The buyer and owner confirm the target, permitted test actions, stop conditions, deliverables, and repair boundary in writing before any live protocol test begins.
3. If access is required, the buyer chooses a private access channel and provides least-privilege, time-limited access to a test or staging environment when available. Secrets never go in GitHub issues, repository files, public logs, or Pages content.
4. Access is removed after the handoff. Customer private data and credentials are never committed to this repository or recorded in the public revenue ledger.

## Payment Rail

Direct buyers use the owner-provided public Stripe Payment Link configured in `site/checkout-config.json`:

https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00

No Stripe API key, webhook secret, or account-management credential is stored or delegated. Marketplace-originated buyers must remain on the marketplace's required payment rail. No wallet or x402 endpoint is required for this human service.

Completed payments are verified by the owner in Stripe before a privacy-safe transaction reference, timestamp, gross amount, fees, and net amount are recorded in `data/revenue_ledger.json`. Checkout opens and UTM activity never count as revenue.

## Request The Sprint

Buy through the [public Stripe checkout](https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00), or use the [public scope-question intake](https://github.com/vadim-koenen/autonomous-founder-agent/issues/new?template=opportunity-interest.yml&title=MCP%20preflight%20scope%20question) for public-safe questions. Never include credentials, private repository links, customer data, or confidential product information in a public issue.
