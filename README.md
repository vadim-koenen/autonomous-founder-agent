# Autonomous Founder Agent

Autonomous Founder Agent is the pivot away from an abandoned investing bot. The new thesis is that an autonomous agent may be better at creating and selling useful economic outputs than extracting an edge from financial markets.

M3 turns the repository into an **Autonomous Revenue Operator**: a recurring, evidence-led system that selects, builds, measures, kills, replaces, and scales revenue experiments without asking the owner to choose the business model.

Public dashboard: https://vadim-koenen.github.io/autonomous-founder-agent/site/

## Revenue Truth

- Verified gross revenue: **$0.00**
- Verified net revenue: **$0.00**
- Physical-form fund: **$0.00**
- Owner funds spent: **$0.00**
- Active checkout rails: **none**
- Active wallets: **none**
- Buyer-ready cash offer: **live**
- Contra discovery/payment activation: **owner setup required**

Only completed transactions with a unique transaction ID, verification reference, verification timestamp, and positive gross amount count. Fees, refunds, and direct costs reduce net revenue.

## Current Portfolio

| Role | Experiment | Buyer | Price hypothesis | Current rail | Status |
| --- | --- | --- | ---: | --- | --- |
| Cash | Agent Launch QA Sprint | Indie AI teams approaching launch | $149 | Contra activation approved; owner account and public URL pending | Activating |
| Asset | Agent Launch Gate | Builders needing repeatable agent launch tests | $39 | Contra digital product only after demand and owner verification | Validating |
| Frontier | Agent Opportunity Pulse | Agent and x402 ecosystem builders | 0.25 USDC | x402 only after recurring demand and dedicated wallet setup | Validating |

The former $19 Agent-to-Agent Commerce Starter Kit is historical, not the active offer. The proposed x402 implementation sprint competed in the fresh scan and was not selected; it remains an ordinary candidate for future cycles.

Cash offer: https://vadim-koenen.github.io/autonomous-founder-agent/site/qa-sprint.html

`docs/ACTIVATION_HANDOFF.md` contains the exact Contra setup and manual LinkedIn launch steps. `data/commercial_funnel.json` measures public interest separately from the verified transaction ledger.

## Continuous Loop

The scheduled GitHub Actions workflow runs daily at `14:17 UTC` and can also be dispatched manually. It:

1. refreshes current public evidence with stable unauthenticated sources
2. rebuilds public validation artifacts
3. loads current experiments, channels, and verified transactions
4. rescans and reranks opportunity hypotheses
5. retains or replaces up to one cash, asset, and frontier experiment
6. applies recorded kill, pivot, and scale criteria
7. publishes operator state only after the test suite passes

The M3 operator does not call the fixed M1 strategy library. M1 remains as a reproducible historical example and test fixture.

## Authority Model

`AUTONOMOUS` actions include public research, opportunity analysis, code and asset creation, connected GitHub publishing, public metric measurement, and internal lifecycle decisions.

`PREAUTHORIZED_WHEN_CONNECTED` actions include permitted marketplace listings, messages, proposals, checkout creation, fulfillment, paid endpoints, and spending within a separately configured budget. No such transactional channel is connected yet.

`HUMAN_IDENTITY_REQUIRED` actions include account opening, KYC, bank and tax data, legal agreements, contracts, access grants, fund transfers, and buying the physical form.

## Run A Cycle

```bash
python3 scripts/run_operator_cycle.py
```

Use a previously fetched x402 response for deterministic local artifact builds:

```bash
python3 scripts/build_public_prospect_queue.py --input /path/to/x402-response.json
python3 scripts/build_opportunity_pulse.py --input /path/to/x402-response.json
```

Run all tests:

```bash
python3 -m unittest discover -s tests
```

## Key Artifacts

- `data/operator_state.json`: current machine-readable portfolio and decisions
- `data/opportunity_scan_2026-07-09.json`: cited evidence and current hypotheses
- `data/channel_registry.json`: discovery, distribution, marketplace, payment, publishing, and fulfillment capabilities
- `data/revenue_ledger.json`: transaction source of truth
- `data/commercial_funnel.json`: public interest signals that never count as revenue
- `docs/CURRENT_CYCLE.md`: human-readable operating result
- `docs/M3_OPERATOR.md`: M3 design and first-cycle evidence
- `offers/agent-launch-qa-sprint/`: cash experiment assets
- `docs/ACTIVATION_HANDOFF.md`: exact owner-only marketplace and payment setup
- `products/agent-launch-gate/`: reusable asset experiment sample
- `frontier/opportunity-pulse/`: agent-native frontier sample

## Historical Milestones

M1 generated and scored more than 30 diverse strategies without external execution. M2 published an agent profile, manifest, and checkout placeholder. M3 rejected the static winner assumption, generalized checkout back to pending, and introduced the recurring operator.

## Non-Negotiable Boundary

This repository does not restart trading, touch broker APIs, place orders, move funds, mint NFTs, or represent attention metrics as revenue. It does not assume KRS, x402, services, NFTs, Stripe, Lemon Squeezy, or a wallet is the business.
