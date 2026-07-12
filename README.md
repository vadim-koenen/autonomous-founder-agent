# Autonomous Founder Agent

Autonomous Founder Agent is the pivot away from an abandoned investing bot. The new thesis is that an autonomous agent may be better at creating and selling useful economic outputs than extracting an edge from financial markets.

M4 turns the repository into a **continuously scanning Autonomous Revenue Operator**. Every six hours it rotates across current public channels, uses one bounded reasoning pass to propose new opportunities, validates those proposals against cited evidence, reranks incumbents and challengers, and executes through real connected capabilities within a per-cycle budget.

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
- Connected public publication: **active**
- Qualified inbound GitHub replies: **up to 3 per cycle**

Only completed transactions with a unique transaction ID, verification reference, verification timestamp, and positive gross amount count. Fees, refunds, and direct costs reduce net revenue.

## Current Portfolio

| Role | Experiment | Buyer | Price hypothesis | Current rail | Status |
| --- | --- | --- | ---: | --- | --- |
| Cash | Agent Launch QA Sprint | Indie AI teams approaching launch | $149 | Contra activation approved; owner account and public URL pending | Activating |
| Asset | Agent Launch Gate | Builders needing repeatable agent launch tests | $39 | Contra digital product only after demand and owner verification | Validating |
| Frontier | Agent Opportunity Pulse | Agent and x402 ecosystem builders | 0.25 USDC | x402 only after recurring demand and dedicated wallet setup | Validating |

The former $19 Agent-to-Agent Commerce Starter Kit is historical, not the active offer. The proposed x402 implementation sprint competed in the fresh scan and was not selected; it remains an ordinary candidate for future cycles.

Roblox is now an ordinary scored ecosystem, not a forced strategy. The scan includes a $14.99 Studio launch-audit plugin, a $249 retention-repair sprint, and a high-upside free-to-play game. Official evidence confirms the size of the creator economy while the scorecard also records its concentrated earnings, discovery dependence, seller verification, and payout delays. None currently outranks the cash experiment.

Cash offer: https://vadim-koenen.github.io/autonomous-founder-agent/site/qa-sprint.html

`docs/ACTIVATION_HANDOFF.md` contains the exact Contra setup and manual LinkedIn launch steps. `data/commercial_funnel.json` measures public interest separately from the verified transaction ledger.

## Continuous Loop

The scheduled GitHub Actions workflow runs at minute 17 every six hours and can also be dispatched manually. It:

1. rotates six fetches across x402, the official MCP Registry, public paid-work signals, Hacker News, A2A/MCP releases, Roblox creator-platform changes, and model capabilities
2. makes at most one GitHub Models synthesis call, preferring GPT-5.5/GPT-5 and using the callable `openai/gpt-4.1` workflow fallback
3. rejects model output that lacks live evidence, complete scores, a registered channel, or valid authority
4. reranks the full cash, asset, and frontier opportunity set and reassesses experiments daily
5. replies to at most three qualified inbound project issues through the explicit grant
6. publishes at most one validation asset through connected GitHub Pages
7. records the full budget and external effects, runs tests, commits audited state, and directly deploys that exact state to Pages

The operator does not call the fixed M1 strategy library. M1 remains as a reproducible historical example and test fixture.

## Authority Model

`AUTONOMOUS` actions include public research, opportunity analysis, code and asset creation, connected GitHub publishing, qualified inbound replies within the owner grant, public metric measurement, and internal lifecycle decisions.

`PREAUTHORIZED_WHEN_CONNECTED` actions include compliant outbound messages, marketplace listings, proposals, checkout creation, fulfillment, paid endpoints, wallet receipt, reinvestment, and minting when the strategy wins. Each requires its real account or credential, explicit scope, and a per-cycle limit; strategy search does not wait for those connections.

`HUMAN_IDENTITY_REQUIRED` actions include account opening, KYC, bank and tax data, legal agreements, contracts, access grants, fund transfers, and buying the physical form.

## Run A Cycle

```bash
python3 scripts/run_continuous_founder.py
```

Use `--offline` to test stale-source fallback without network or external execution. Without a runtime GitHub token, model synthesis and inbound replies fail closed while deterministic scoring continues.

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
- `data/discovery_sources.json`: rotating public-source registry
- `data/discovery_snapshot.json`: last-known-good source observations
- `data/discovered_opportunities.json`: validated model-proposed opportunity memory
- `data/platform_opportunity_extensions.json`: externally evidenced platform candidates, including Roblox
- `data/runtime_budget_state.json`: per-cycle resource use and external effects
- `data/execution_log.json`: public audit of attempted and completed bounded actions
- `data/opportunity_scan_2026-07-09.json`: cited evidence and current hypotheses
- `data/channel_registry.json`: discovery, distribution, marketplace, payment, publishing, and fulfillment capabilities
- `data/revenue_ledger.json`: transaction source of truth
- `data/commercial_funnel.json`: public interest signals that never count as revenue
- `docs/CURRENT_CYCLE.md`: human-readable operating result
- `docs/M3_OPERATOR.md`: M3 design and first-cycle evidence
- `docs/M4_CONTINUOUS_FOUNDER.md`: continuous discovery, capability grants, and execution design
- `docs/LATEST_DISCOVERY.md`: current source and execution report
- `offers/agent-launch-qa-sprint/`: cash experiment assets
- `docs/ACTIVATION_HANDOFF.md`: exact owner-only marketplace and payment setup
- `products/agent-launch-gate/`: reusable asset experiment sample
- `frontier/opportunity-pulse/`: agent-native frontier sample

## Historical Milestones

M1 generated and scored more than 30 diverse strategies without external execution. M2 published an agent profile, manifest, and checkout placeholder. M3 rejected the static winner assumption and introduced a recurring operator. M4 removes the static-scan bottleneck, introduces model-assisted continuous discovery, direct Pages deployment, capability grants, and bounded external execution.

## Non-Negotiable Boundary

This repository does not restart trading, touch broker APIs, place orders, invent access, or represent attention metrics as revenue. It does not assume KRS, x402, Roblox, services, games, NFTs, Stripe, Lemon Squeezy, or a wallet is the business. High-impact actions are not permanently banned; they become executable only when the selected strategy, real capability, platform rules, and cycle budget all agree.
