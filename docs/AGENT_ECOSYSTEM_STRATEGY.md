# Agent Ecosystem Strategy

M2 uses a dual-channel strategy. Lemon Squeezy or Stripe can collect human-approved payments, but they are not the strategy. The strategy is to test whether an autonomous founder agent can package a sellable product for both human-commerce and agent-native-commerce discovery.

## Channel Map

| Channel | Role | M2 Status | Why It Matters | Current Risk |
| --- | --- | --- | --- | --- |
| Lemon Squeezy / Stripe | Human checkout rails | Pending public checkout URL | Fastest path to normal payment, receipts, payouts, refunds, and dashboard revenue reporting | Requires user setup, KYC/tax/payout details, and product approval |
| Coinbase AgentKit / Wallet MCP | Agent-native wallet tooling candidate | Not active | Gives agents a wallet/tooling pattern for onchain interactions if agent-native payments become useful | Wallets introduce key custody, transaction, and compliance risk |
| x402 | Agent-native payment protocol candidate | Not active | Offers a web-native way for agents/services to request payment for resources | Ecosystem adoption and operational safety are still developing |
| Moltbook/OpenClaw-style networks | Discovery channels | Research/discovery candidate | Agent directories and open agent networks can help machines discover capabilities/products | Discoverability may not equal purchase intent |
| NFT marketplaces | Optional marketplace channel | Deferred | Could create collectible/supporter artifacts for the physical-form fund narrative | Wallet friction, marketplace risk, rights/compliance, and speculative framing |

## Human Checkout Rails

Human checkout is the fastest route to first revenue because buyers already understand card checkout and digital downloads.

Use these rails for:

- $19 starter-kit purchase
- payment dashboard reporting
- refund handling
- payout setup
- basic conversion tracking

Stripe Payment Links and Lemon Squeezy are acceptable because they can expose a public checkout URL without putting API keys in this repo.

M2 rule: only a public checkout URL may be added to `site/checkout-config.json`. No secret keys, webhook secrets, private API tokens, bank data, or tax details belong in the repository.

## Agent-Native Payment Rails

Agent-native commerce is the broader experiment. The question is whether a buyer agent can discover this product, parse the manifest, understand the offer, and route a human-approved payment through the appropriate rail.

Candidate rails:

- Coinbase AgentKit / Wallet MCP: useful for agent wallet tooling and onchain capability exploration.
- x402: useful for HTTP-native paid resource flows where clients can respond to payment requirements.

M2 does not activate either rail. It only prepares machine-readable product metadata and keeps the agent-native payment section explicit in `AGENT_MANIFEST.json`.

Activation would require:

- a dedicated project wallet
- explicit custody rules
- no seed phrase or private key in code
- transaction limits
- testnet trial first
- human approval before any mainnet transaction
- legal/compliance review for the exact payment flow

## Discovery Networks

Moltbook/OpenClaw-style networks are treated as discovery channels, not payment processors. The useful pattern is to publish machine-readable identity, product metadata, and capability descriptions so other agents can index or route to the offer.

M2 discovery assets:

- `AGENT_PROFILE.md`
- `AGENT_MANIFEST.json`
- `starter-kit/free-sample/product-card.sample.json`
- public GitHub repository
- GitHub Pages landing page

Future discovery work should focus on:

- submitting public metadata to relevant agent directories
- creating an agent-readable product-card endpoint
- adding a short capability card
- measuring referral traffic and conversion source

## NFT Marketplaces

NFTs are not the default strategy. They remain an optional channel if they serve a concrete purpose, such as:

- supporter receipt for the physical-form fund
- access token for future updates
- collectible artifact documenting the autonomous founder experiment

NFTs should not be used merely because they are attention-grabbing. They should only proceed if they beat the current strategy under the rubric and pass wallet/compliance gates.

## Current M2 Recommendation

1. Keep GitHub Pages live for public discovery.
2. Add a human checkout URL when the user creates a Lemon Squeezy or Stripe product.
3. Keep agent-native payment rails as documented candidates until there is a safe testnet plan.
4. Defer NFT marketplace activation until the agent has evidence that collectibles would improve revenue more than a normal digital product checkout.

## Public References Checked

- Stripe Payment Links documentation: https://docs.stripe.com/payment-links
- Lemon Squeezy product/help documentation: https://docs.lemonsqueezy.com/
- Coinbase Developer Platform documentation: https://docs.cdp.coinbase.com/
- x402 documentation: https://x402.org/
- Moltbook: https://moltbook.com/
- OpenClaw repository: https://github.com/FSSELab/OpenClaw
