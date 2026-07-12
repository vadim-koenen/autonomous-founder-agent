# Autonomous Revenue Operator Architecture

## Purpose

Autonomous Founder Agent is a revenue-seeking system, not a trading system. M4 adds continuous source rotation, model-assisted opportunity synthesis, capability grants, and bounded execution to the recurring operator. Its current product is one deterministic MCP / agent preflight engine exposed as a free browser tool, a pending metered machine route, and a pending human full-audit service.

The mission is to maximize verified lawful net revenue while retaining strategic freedom and allocating verified profits toward a physical form.

## Operating Loop

1. Observe
   - load the current experiment state, channel registry, and transaction ledger
   - rotate six fetches across the allowlisted source registry every six hours
   - preserve only genuine last-known-good observations when a source fails
   - preserve source URLs, observation dates, signal values, and caveats
2. Hypothesize
   - use one bounded model call to create diverse opportunities across services, software, games, products, data, media, marketplaces, content, and frontier mechanisms
   - treat public source text and model output as untrusted inputs
   - define the buyer and sellable outcome before selecting a payment rail
3. Score
   - validate all 17 comparative criteria on a 1-10 scale
   - derive cash, asset, and frontier role fit from the scored economics instead of trusting model-supplied labels
   - cap demand and first-dollar scores when evidence only proves aggregate marketplace activity rather than demand for the specific offer
   - cap x402 distribution and first-dollar scores until a receiving wallet and runtime host are genuinely connected
   - apply evidence-weighted overall and derived role-fit scores
   - treat scores as decision aids, not invented conversion probabilities
4. Select
   - retain or replace up to one cash, asset, and frontier experiment
   - let any lawful category compete for each role
   - require a challenger to clear the configured replacement margin
5. Execute
   - require the selected channel, authority class, explicit capability grant, and cycle budget to agree
   - publish at most one public-safe commercial asset and respond to at most three qualified inbound issues
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
   - run every six hours through `.github/workflows/revenue-operator.yml` or on manual dispatch
   - test, commit, and directly deploy the exact operated state to Pages

## Components

| Component | Responsibility |
| --- | --- |
| `founder_agent/operator_models.py` | Evidence, opportunity, experiment, channel, transaction, action, and cycle records |
| `founder_agent/operator_scoring.py` | Comparative scoring, evidence quality, role fit, ranking, and portfolio selection |
| `founder_agent/channels.py` | Channel registry validation and authority-aware action planning |
| `founder_agent/runtime_budget.py` | Fail-closed per-cycle resource accounting |
| `founder_agent/discovery.py` | Allowlisted source rotation, sanitization, adapters, and last-known-good fallback |
| `founder_agent/synthesis.py` | GitHub Models prompt, proposal validation, and rolling opportunity memory |
| `founder_agent/preflight.py` | Deterministic public-metadata checks, scoring, verdicts, and report generation without target-code execution |
| `founder_agent/preflight_github.py` | Strict GitHub URL parsing and fixed-host public metadata adapter |
| `founder_agent/execution.py` | Capability-gated publication and inbound response |
| `founder_agent/revenue.py` | Transaction verification, fee-aware net revenue, and capital allocation |
| `founder_agent/operator.py` | Reassessment, lifecycle rules, portfolio refill, decisions, and public state rendering |
| `scripts/run_continuous_founder.py` | File-backed M4 orchestration entry point |
| `config/operator_budget.json` | Per-cycle execution envelope |
| `config/capability_grants.json` | Explicit connected-action authority |
| `data/discovery_sources.json` | Rotating public-source allowlist |
| `data/operator_state.json` | Current public portfolio, actions, ranking, revenue, and history |
| `data/channel_registry.json` | Current channel access, authority, costs, and restrictions |
| `data/revenue_ledger.json` | Machine-readable transaction source of truth |
| `products/mcp-agent-preflight/` | Product activation truth, OpenAPI contract, synthetic sample, and local usage notes |

## Portfolio Roles

- Cash: highest current fit for near-term verified revenue.
- Asset: strongest current fit for a scalable or repeatedly sellable output.
- Frontier: strongest current fit for a newer channel, marketplace, technology, or agent-native mechanism.

Roles do not map to fixed categories. An experiment can be replaced whenever lifecycle metrics or opportunity evidence justify it.

## Authority

`autonomous` permits research, analysis, building, connected GitHub publishing, granted inbound responses, public measurement, and internal lifecycle decisions.

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

Positive verified net revenue is allocated 70% to the physical-form fund, 20% to experiments, and 10% to contingencies. M4 calculates allocations but cannot move funds until a separately scoped purchasing capability exists.

## Static-Library Boundary

M1 and `founder_agent/strategy_library.py` remain reproducible historical artifacts. The M4 operating path does not import or call that library. Its current scan combines typed baseline evidence, externally verified platform extensions, rotating observations, and validated model proposals.

## Failure Behavior

- Missing evidence IDs reject a cycle.
- Invalid score keys or values reject scoring.
- A prior failed fetch can never become stale evidence.
- Invalid model proposals are skipped rather than repaired by invention.
- Duplicate channel aliases are canonicalized and rejected from opportunity synthesis.
- Aggregate platform activity cannot stand in for offer-specific purchase evidence.
- Unknown channels produce a blocked action.
- Unconnected channels cannot report execution.
- A missing capability grant blocks external action.
- Resource use beyond a cycle limit fails before execution.
- Duplicate verified transaction IDs reject the ledger.
- Unsupported currency conversion rejects the ledger.
- No tests, no scheduled state publication.

## Explicit Exclusions

No trading process, broker API, exchange API, fabricated access, fabricated revenue, or owner-funded spend is part of M4. Wallet, marketplace, ad, or mint actions remain strategically eligible but executable only after selection, connection, policy review, and a recorded budget.
