# MCP / Agent Preflight Activation Handoff

Current commercial product:

- Free route: public GitHub metadata preflight
- Human offer: authorized live protocol audit, report, and one repair for `$149`
- Agent offer: `$0.25` basic or `$1` expanded public-evidence report per call through x402; neither machine tier executes target code
- Free demo: `site/preflight.html`
- Product truth: `products/mcp-agent-preflight/product.json`

## Required Now

Nothing further is required from the owner to keep the free tool, active Stripe checkout, and continuous operator running. The free route does not use the checkout, wallet, private repository, or target credential.

## Human Full-Audit Checkout

The owner-provided `$149` Stripe Payment Link is active on `site/qa-sprint.html`. It preserves the published 48-hour audit, report, one-repair, and rerun scope.

Stripe account access, identity, tax, bank, payout, refund, and dispute controls remain human-owned. The repository stores no Stripe API key or webhook secret.

Never provide credentials, tokens, tax records, bank details, private keys, seed phrases, or recovery codes.

Active `site/checkout-config.json` contract:

```json
{
  "status": "active",
  "experiment_id": "opp-agent-launch-qa",
  "provider": "stripe",
  "checkout_url": "https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00",
  "configured_by_human": true,
  "notes": "Public checkout URL only; no credentials."
}
```

## x402 Activation Gate

Do not connect a wallet merely because the API contract exists. Activate the paid route after all of these are true:

- at least three qualified recurring-use requests
- at least one request names a repeated agent workflow
- the deterministic route is deployed on an approved runtime host
- the owner approves a dedicated receiving wallet separate from personal funds

At activation:

1. Create a dedicated Base-compatible USDC receiving wallet or approved server-wallet integration.
2. Keep signing material in the provider's supported secret store. Never commit or paste a private key into this repository.
3. Provide the public receiving address through an approved configuration path.
4. Configure the paid route from `products/mcp-agent-preflight/openapi.json`.
5. Complete a clearly labeled test settlement. A self-funded test never counts as revenue.
6. Confirm Bazaar discovery only after the facilitator records a successful settlement.

## Revenue Verification

After a real customer payment, add a public-safe transaction to `data/revenue_ledger.json` with a unique transaction ID, non-secret verification reference, verification timestamp, gross amount, fees, refunds, and direct costs. Never include buyer identity.
