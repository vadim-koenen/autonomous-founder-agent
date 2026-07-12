# MCP / Agent Preflight Activation Handoff

Current commercial product:

- Free route: public GitHub metadata preflight
- Human offer: authorized live protocol audit, report, and one repair for `$149`
- Agent offer: `$0.25` basic or `$1` expanded public-evidence report per call through x402; neither machine tier executes target code
- Free demo: `site/preflight.html`
- Product truth: `products/mcp-agent-preflight/product.json`

## Required Now

Nothing is required from the owner to keep the free tool and continuous operator running. The free route does not use a wallet, checkout, private repository, or target credential.

## Human Full-Audit Checkout

Activate only when the owner is ready to accept the `$149` service:

1. Select one human rail. Contra remains the current marketplace hypothesis; Stripe is acceptable for direct buyers but adds no discovery.
2. Create or sign in using the owner's real identity.
3. Review current terms and complete required identity, tax, bank, and payout setup directly with the provider.
4. Publish the MCP / Agent Preflight Full Audit using the scope on `site/qa-sprint.html`.
5. Create a fixed-price public checkout preserving the `$149`, 48-hour, one-repair scope.
6. Return only the public service and checkout URLs to the repository.

Never provide credentials, tokens, tax records, bank details, private keys, seed phrases, or recovery codes.

After setup, update `site/checkout-config.json`:

```json
{
  "status": "active",
  "experiment_id": "opp-agent-launch-qa",
  "provider": "contra",
  "checkout_url": "https://public-checkout.example",
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
