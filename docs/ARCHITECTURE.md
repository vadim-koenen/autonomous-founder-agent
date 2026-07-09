# Autonomous Founder Agent Architecture

## Purpose

Autonomous Founder Agent is a revenue-seeking agent, not a trading agent. It tries to identify lawful opportunities where it can create, package, and prepare an economic output with minimal human labor and low startup cost.

M1 is deliberately non-executing. It builds a decision system and launch plan, but all external actions remain approval-gated.

## Agent Posture

The agent should think like an autonomous founder. It should be opportunistic, commercially direct, and willing to consider weird lawful revenue paths if they score well. It should not behave like a consultant waiting for a predefined client category, and it should not assume the user's existing business is the route to revenue.

## M1 Data Flow

1. Candidate generation
   - `founder_agent.strategy_library.build_candidate_strategies()` returns a diverse set of revenue strategies.
   - The library is not scoped to the user's existing business.
   - It includes NFTs/collectibles, agent-to-agent commerce, fast digital products, content/attention, marketplaces, APIs, reports, templates, licensing, lead generation, and entertainment.

2. Scoring
   - `founder_agent.scoring.rank_strategies()` validates every strategy against the same 12-dimension rubric.
   - Risk dimensions are reverse scored: higher means lower risk.
   - Weighting favors speed to first dollar, low startup cost, first-sale probability, automation leverage, and reinvestment potential.

3. Selection
   - `founder_agent.m1.run_m1_decision_system()` ranks all candidates.
   - It selects the top 3.
   - It chooses the highest-scoring strategy as the primary experiment.

4. Launch planning
   - `founder_agent.m1.build_launch_plan()` creates concrete internal build steps, draft assets, validation steps, external launch actions, approval checks, stop conditions, and reinvestment path.
   - External actions are represented as `ExternalActionRequest` records with `performed=False`.

5. Reporting
   - `founder_agent.reporting` renders JSON and Markdown artifacts.
   - `scripts/run_m1_example.py` writes `data/example_run.json` and `data/example_run.md`.

## Non-Execution Boundary

M1 can reason and build local artifacts. M1 cannot perform external execution.

Blocked external actions include:

- email or direct-message sending
- public posting
- paid ads
- wallet transactions
- NFT minting
- payment collection
- live page publishing
- public account creation
- spending money
- trading, investing, exchange, or financial-account activity

The safety layer records launch actions as plan items only. Tests assert that generated launch actions are not marked as performed.

## Selected M1 Experiment

The current example run selects **Agent-to-Agent Commerce Starter Kit**.

Why it fits the architecture:

- It is a fast digital product and an agent-to-agent commerce play.
- The agent can draft the kit, examples, templates, checklist, copy, and launch posts locally.
- It does not assume the user's business.
- It does not force NFTs as the revenue path.
- It creates a plausible bridge from early revenue to the physical-form fund.

## M2 Direction

M2 began after explicit approval. It adds a dual-channel activation layer:

- human checkout placeholder for a Lemon Squeezy or Stripe public checkout URL
- agent profile and machine-readable manifest for agent-native discovery
- ecosystem strategy comparing human checkout rails, agent-native payment rails, discovery networks, and optional NFT marketplaces
- payment activation steps
- revenue ledger initialized at $0
- tests proving secrets and external execution are not committed

M2 keeps checkout pending until a human provides a public checkout URL. Lemon Squeezy or Stripe are rails, not the strategy. The broader strategy is to test whether an autonomous founder agent can sell through both human-commerce and agent-native-commerce channels.

Likely next steps:

- create a Lemon Squeezy or Stripe product outside the repository
- provide only the public checkout URL
- wire the public checkout URL into `site/checkout-config.json` and `AGENT_MANIFEST.json`
- update `docs/REVENUE_LEDGER.md` after confirmed sales
- evaluate agent-native payment rails only after a separate wallet/testnet plan

Payment setup, posting, outreach, ad spend, minting, wallet transactions, or account actions remain approval-gated.
