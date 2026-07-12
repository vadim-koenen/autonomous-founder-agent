# Payment Activation

The owner-provided public Stripe Payment Link is active for the `$149` full audit. No Stripe API key, webhook secret, or account-management credential is stored. The functional free MCP / Agent Preflight still requires no payment, while x402 remains behind its separate recurring-use gate, runtime host, and dedicated receiving wallet.

Never put API keys, webhook secrets, private keys, seed phrases, bank data, tax data, account credentials, or buyer personal data in this repository.

## Cash Experiment: MCP / Agent Preflight Full Audit

Status: active on 2026-07-12 through the public Stripe Payment Link in `site/checkout-config.json`.

Configured boundary:

1. Buyers may open the public `$149` Stripe Payment Link from `site/qa-sprint.html`.
2. Stripe identity, legal, tax, bank, payout, refund, and account controls remain human-owned.
3. The repository stores only the public checkout URL.
4. Fulfillment remains the published 48-hour audit scope, prioritized report, one repair patch, and rerun.

Marketplace-originated buyers remain on the marketplace's required payment rail.
See `docs/ACTIVATION_HANDOFF.md` for the field-by-field setup.

## Asset Experiment: Agent Launch Gate

Trigger: at least three qualified interest signals for the free sample.

Minimal owner setup:

1. Connect and verify a provider that permits the product and intended fulfillment.
2. Complete identity, legal, tax, bank, and payout steps in that provider.
3. Create the exact product only after the full licensed package is ready.
4. Set the founding price to `$39` one-time.
5. Provide only the public checkout URL.

Contra is the current proposed fit. Stripe may be reconsidered if direct demand warrants it. Lemon Squeezy is not assumed and must pass product-policy review first.

## Frontier Experiment: MCP / Agent Preflight Metered API

Trigger: at least three qualified recurring-use requests, including one repeated agent workflow, plus an approved runtime host.

Minimal owner setup:

1. Create a dedicated project receiving wallet separate from personal wallets.
2. Keep the recovery phrase and private key offline and outside Codex, source code, logs, screenshots, issues, and repository settings.
3. Approve a scoped receiving policy and Base USDC only after reviewing current x402 requirements.
4. Provide the public receiving address through approved configuration; signing material remains in a supported secret store.
5. Deploy the route defined by `products/mcp-agent-preflight/openapi.json` and complete a labeled test settlement.

The proposed prices are `0.25 USDC` for a basic report and `1 USDC` for an expanded public-evidence report. Neither machine tier executes target code. No wallet setup is currently required because the demand trigger has not been met. A self-funded test does not count as revenue.

## Public Checkout Configuration

The active configuration is:

```json
{
  "status": "active",
  "experiment_id": "opp-agent-launch-qa",
  "provider": "stripe",
  "checkout_url": "https://buy.stripe.com/fZu00j2vSgJge0P08N3cc00",
  "configured_by_human": true,
  "notes": "Public Stripe Payment Link only; no credentials."
}
```

The dashboard has no generic Buy button. An offer-specific action may be added only when its configuration and fulfillment path are valid.

## Roblox Candidate Activation

Roblox is scored but is not currently selected for activation.

For the Launch Lens plugin, wait for five qualified creator requests. Then the owner creates or verifies the Roblox account, completes government-ID and Stripe Creator Store seller onboarding, and publishes the tested original plugin. Creator Store checkout is the rail; do not create a separate wallet.

For a Roblox experience, wait until the local core loop is playable. Then the owner creates the experience and a narrowly scoped Open Cloud API key for place publishing. DevEx identity and tax setup are unnecessary until the experience reaches the platform's earned-Robux threshold. No ad spend is authorized before organic retention and co-play gates pass.

## Revenue Recording

Provider dashboards or signed settlement records remain the verification source. Add a public-safe transaction to `data/revenue_ledger.json` only after confirming completion. Record gross, processor and platform fees, refunds, direct costs, a non-secret verification reference, and verification time. Do not record buyer identity.
