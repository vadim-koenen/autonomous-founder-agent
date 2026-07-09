# Autonomous Founder Agent

Autonomous Founder Agent is the pivot away from an autonomous investing bot. The old thesis tried to extract edge from financial markets. This project uses a different thesis: an autonomous AI agent may have a better chance of generating revenue by creating, packaging, distributing, and selling lawful digital or economic outputs.

The agent's narrative goal is to earn enough money to buy or fund its own physical form, such as a robot dog, desktop robot, robotic arm, small server, or other embodiment.

## M1 Scope

M1 is a non-executing decision system. It can research, generate, score, select, and plan a revenue experiment. It must not launch one.

M1 does not:

- send emails or direct messages
- post publicly
- spend money
- mint NFTs or make wallet transactions
- place ads
- publish live pages
- accept payments
- touch trading, investing, exchange, or financial-account APIs

M1 does:

- generate at least 30 possible revenue strategies
- avoid binding the agent to the user's existing business
- include NFT/collectible, agent-to-agent commerce, fast digital product, content/attention, and marketplace strategies
- score every strategy against a transparent weighted rubric
- select the top 3 strategies
- choose one primary experiment
- produce a concrete launch plan and approval checklist
- clearly separate reasoning/building from external execution

## Current M1 Result

The generated example run selects **Agent-to-Agent Commerce Starter Kit** as the first experiment.

The offer is a downloadable kit that helps small digital sellers make their products more legible to autonomous buyer agents. It wins because it is fast to package, cheap to start, high margin, timely, mostly agent-buildable, and more differentiated than a generic prompt pack.

## M2 Activation Status

M2 activates the public discovery layer and prepares checkout, but keeps revenue collection pending until a human supplies a public checkout URL.

- Public page: live
- Agent manifest: live
- Free sample: live
- Human checkout: pending Lemon Squeezy or Stripe public checkout URL
- Agent-native payment rails: documented candidates only
- Revenue ledger: initialized at $0
- Wallet transactions, NFT minting, ads, posts, DMs, emails, and broker APIs: inactive

Live public artifacts:

- Landing page: https://vadim-koenen.github.io/autonomous-founder-agent/site/
- Source repository: https://github.com/vadim-koenen/autonomous-founder-agent

Generated artifacts:

- [data/example_run.md](data/example_run.md)
- [data/example_run.json](data/example_run.json)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/DATA_MODEL.md](docs/DATA_MODEL.md)
- [docs/APPROVAL_CHECKLIST.md](docs/APPROVAL_CHECKLIST.md)
- [docs/PUBLISHING.md](docs/PUBLISHING.md)
- [docs/AGENT_ECOSYSTEM_STRATEGY.md](docs/AGENT_ECOSYSTEM_STRATEGY.md)
- [docs/PAYMENT_ACTIVATION.md](docs/PAYMENT_ACTIVATION.md)
- [docs/REVENUE_LEDGER.md](docs/REVENUE_LEDGER.md)

Launch-prep artifacts:

- [AGENT_PROFILE.md](AGENT_PROFILE.md)
- [AGENT_MANIFEST.json](AGENT_MANIFEST.json)
- [site/index.html](site/index.html)
- [site/checkout-config.json](site/checkout-config.json)
- [starter-kit/README.md](starter-kit/README.md)
- [starter-kit/free-sample/product-card.sample.json](starter-kit/free-sample/product-card.sample.json)
- [starter-kit/paid-bundle/product-card-template.json](starter-kit/paid-bundle/product-card-template.json)
- [launch-copy/public-posts.md](launch-copy/public-posts.md)
- [launch-copy/tony-robbins-agent-nfts-search.md](launch-copy/tony-robbins-agent-nfts-search.md)

## Run It

Generate the example run:

```bash
python3 scripts/run_m1_example.py
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

Preview the static landing page locally by opening [site/index.html](site/index.html) in a browser.

## Project Layout

```text
founder_agent/
  m1.py                 # M1 orchestration and selected launch plan
  models.py             # Revenue strategy, scoring, launch-plan data model
  scoring.py            # Weighted transparent rubric
  safety.py             # Non-execution guardrails
  strategy_library.py   # 30+ diverse candidate strategies
  reporting.py          # JSON and Markdown example-run rendering
docs/
  ARCHITECTURE.md
  DATA_MODEL.md
  APPROVAL_CHECKLIST.md
data/
  example_run.json
  example_run.md
tests/
```

## Public Launch Posture

The current publishable artifact is a public source repository plus static landing page. It does not enable checkout, mint NFTs, send messages, run ads, or touch financial APIs. A paid storefront can be connected after a public Lemon Squeezy or Stripe checkout URL is provided.

The broader strategy is not Lemon Squeezy or Stripe. Those are human checkout rails. The actual strategy is to test whether an autonomous founder agent can sell through both human-commerce and agent-native-commerce discovery channels.

## Pivot Principle

This project should not assume KRS, consulting, martech, NFTs, SaaS, digital products, or any other predefined business. Those can appear as options, but the agent must choose based on the current opportunity score and the physical-form funding objective.
