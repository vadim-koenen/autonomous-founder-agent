# Autonomous Revenue Operator Architecture

## Purpose

Autonomous Founder Agent is a revenue-seeking system, not a trading system. M3 replaces the one-time winner model with a recurring operator that can observe, rank, build, validate, retain, replace, kill, pivot, and scale lawful revenue experiments.

The mission is to maximize verified lawful net revenue while retaining strategic freedom and allocating verified profits toward a physical form.

## Operating Loop

1. Observe
   - load the current experiment state, channel registry, and transaction ledger
   - refresh current public evidence through stable unauthenticated sources
   - preserve source URLs, observation dates, signal values, and caveats
2. Hypothesize
   - load or create diverse opportunities across services, software, products, data, media, marketplaces, content, and frontier mechanisms
   - define the buyer and sellable outcome before selecting a payment rail
3. Score
   - validate all 17 comparative criteria on a 1-10 scale
   - apply evidence-weighted overall and role-fit scores
   - treat scores as decision aids, not invented conversion probabilities
4. Select
   - retain or replace up to one cash, asset, and frontier experiment
   - let any lawful category compete for each role
   - require a challenger to clear the configured replacement margin
5. Execute
   - create only actions permitted by the selected channel and configured authority
   - build and publish public-safe assets through the connected GitHub repository and GitHub Pages
   - represent unavailable channels as blocked, never as fabricated execution
6. Measure
   - keep impressions, contacts, replies, checkout starts, and purchases separate
   - count revenue only from verifiable completed transaction records
   - subtract processor fees, platform fees, refunds, and direct costs
7. Decide
   - apply explicit scale, kill, and pivot rules to recorded metrics
   - record each decision and review date
   - refill vacated portfolio roles from the current ranking
8. Repeat
   - run daily through `.github/workflows/revenue-operator.yml` or on manual dispatch
   - publish changed public state only after tests pass

## Components

| Component | Responsibility |
| --- | --- |
| `founder_agent/operator_models.py` | Evidence, opportunity, experiment, channel, transaction, action, and cycle records |
| `founder_agent/operator_scoring.py` | Comparative scoring, evidence quality, role fit, ranking, and portfolio selection |
| `founder_agent/channels.py` | Channel registry validation and authority-aware action planning |
| `founder_agent/revenue.py` | Transaction verification, fee-aware net revenue, and capital allocation |
| `founder_agent/operator.py` | Reassessment, lifecycle rules, portfolio refill, decisions, and public state rendering |
| `scripts/refresh_public_evidence.py` | Stable public evidence refresh |
| `scripts/run_operator_cycle.py` | File-backed operating cycle entry point |
| `data/operator_state.json` | Current public portfolio, actions, ranking, revenue, and history |
| `data/channel_registry.json` | Current channel access, authority, costs, and restrictions |
| `data/revenue_ledger.json` | Machine-readable transaction source of truth |

## Portfolio Roles

- Cash: highest current fit for near-term verified revenue.
- Asset: strongest current fit for a scalable or repeatedly sellable output.
- Frontier: strongest current fit for a newer channel, marketplace, technology, or agent-native mechanism.

Roles do not map to fixed categories. An experiment can be replaced whenever lifecycle metrics or opportunity evidence justify it.

## Authority

`autonomous` permits research, analysis, building, connected GitHub publishing, public measurement, and internal lifecycle decisions.

`preauthorized_when_connected` permits configured marketplace, messaging, checkout, fulfillment, paid endpoint, receipt, or budget actions only after the owner has connected that channel and the platform permits the automation.

`human_identity_required` covers account opening, KYC, banking, tax data, legal acceptance, contracts, access grants, transfers, and purchasing the physical form.

Authority affects action executability, not opportunity score. A promising strategy can remain selected while its identity-bound action is visibly blocked.

## Revenue Truth

A transaction counts only when all of these are present:

- status `completed`
- non-empty unique transaction ID
- non-empty verification reference
- non-empty verification timestamp
- positive gross amount

Public traffic, calls, contacts, replies, intent, checkout starts, and marketplace counters cannot increase revenue. Net revenue is gross less processor fees, platform fees, refunds, and direct costs.

Positive verified net revenue is allocated 70% to the physical-form fund, 20% to experiments, and 10% to contingencies. M3 calculates allocations but does not move funds.

## Static-Library Boundary

M1 and `founder_agent/strategy_library.py` remain reproducible historical artifacts. The M3 operating path does not import or call that library. Its current scan is structured external evidence plus replaceable opportunity hypotheses.

## Failure Behavior

- Missing evidence IDs reject a cycle.
- Invalid score keys or values reject scoring.
- Unknown channels produce a blocked action.
- Unconnected channels cannot report execution.
- Duplicate verified transaction IDs reject the ledger.
- Unsupported currency conversion rejects the ledger.
- No tests, no scheduled state publication.

## Explicit Exclusions

No trading process, broker API, exchange API, wallet transaction, NFT mint, ad purchase, or owner-funded spend is part of M3.
