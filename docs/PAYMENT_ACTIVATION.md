# Payment Activation

No checkout or wallet is active. On 2026-07-10, the owner explicitly approved clearing the cash experiment's discovery and payment bottleneck. Contra activation is now the required human setup for the selected QA service; wallets remain unnecessary.

Never put API keys, webhook secrets, private keys, seed phrases, bank data, tax data, account credentials, or buyer personal data in this repository.

## Cash Experiment: Agent Launch QA Sprint

Trigger: owner activation approval, recorded on 2026-07-10.

Minimal owner setup:

1. Open or connect a Contra independent account, or use the marketplace where the buyer originated.
2. Complete that provider's identity, legal, tax, bank, and payout steps.
3. Publish the exact fixed-scope service from `offers/agent-launch-qa-sprint/LISTING.md`.
4. Set the founding price to `$149` and preserve the scope boundaries.
5. Create a fixed-scope project or public guest-checkout link preserving the published scope.
6. Provide only the public service and checkout URLs to the operator.

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

## Frontier Experiment: Agent Opportunity Pulse

Trigger: at least three explicit endpoint requests plus one recurring use case.

Minimal owner setup:

1. Create a dedicated project receiving wallet separate from personal wallets.
2. Keep the recovery phrase and private key offline and outside Codex, source code, logs, screenshots, issues, and repository settings.
3. Approve a scoped receiving-only policy and the exact network.
4. Provide access through a supported secret store or approved wallet integration, never a pasted private key.
5. Run testnet validation before any paid mainnet endpoint.

The proposed price is `0.25 USDC` per snapshot. No wallet setup is currently required because the demand trigger has not been met.

## Public Checkout Configuration

Only after a selected experiment passes its gate, update `site/checkout-config.json` with its ID and public URL:

```json
{
  "status": "active",
  "experiment_id": "opp-selected-experiment",
  "provider": "approved_provider_id",
  "checkout_url": "https://public-checkout.example",
  "configured_by_human": true,
  "notes": "Public URL only; no credentials."
}
```

The dashboard has no generic Buy button. An offer-specific action may be added only when its configuration and fulfillment path are valid.

## Roblox Candidate Activation

Roblox is scored but is not currently selected for activation.

For the Launch Lens plugin, wait for five qualified creator requests. Then the owner creates or verifies the Roblox account, completes government-ID and Stripe Creator Store seller onboarding, and publishes the tested original plugin. Creator Store checkout is the rail; do not create a separate wallet.

For a Roblox experience, wait until the local core loop is playable. Then the owner creates the experience and a narrowly scoped Open Cloud API key for place publishing. DevEx identity and tax setup are unnecessary until the experience reaches the platform's earned-Robux threshold. No ad spend is authorized before organic retention and co-play gates pass.

## Revenue Recording

Provider dashboards or signed settlement records remain the verification source. Add a public-safe transaction to `data/revenue_ledger.json` only after confirming completion. Record gross, processor and platform fees, refunds, direct costs, a non-secret verification reference, and verification time. Do not record buyer identity.
