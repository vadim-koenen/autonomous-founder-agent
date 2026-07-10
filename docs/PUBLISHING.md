# Publishing Notes

## Connected Route

The public repository and GitHub Pages are connected owner-controlled channels:

- Dashboard: https://vadim-koenen.github.io/autonomous-founder-agent/site/
- Source: https://github.com/vadim-koenen/autonomous-founder-agent
- Operator state: https://vadim-koenen.github.io/autonomous-founder-agent/data/operator_state.json

The root `index.html` redirects to `site/`. GitHub Pages serves the dashboard, machine-readable state, evidence scan, offer samples, channel registry, and revenue ledger directly from the repository.

## Scheduled Publication

`.github/workflows/revenue-operator.yml` runs daily at `14:17 UTC` and on manual dispatch. It refreshes stable public evidence and validation assets, runs the decision cycle, executes the complete test suite, and commits only changed public state.

The workflow has repository content permission only. It references no repository secrets and cannot send messages, activate checkout, transact with a wallet, buy ads, mint NFTs, or touch broker APIs.

## Public-Safe M3 Assets

- current three-role experiment portfolio
- evidence-backed opportunity scan and ranking
- public channel registry
- machine-readable and human-readable revenue ledgers
- QA sprint offer, sample report, intake, public target queue, and audit hooks
- launch-gate product sample and report schema
- opportunity-pulse manifest and sample
- generated social preview image
- historical M1/M2 artifacts clearly separated from current decisions

## Not Connected

- no marketplace seller account
- no payment processor or checkout URL
- no dedicated wallet or paid x402 endpoint
- no ad account
- no email or direct-message sender
- no dedicated social posting account
- no customer private repository or system access
- no trading, investing, broker, exchange, or financial-account API

## Publication Boundary

Publishing public-safe files through the connected repository is autonomous. Identity, KYC, legal acceptance, bank or tax setup, contracts, private access grants, and fund transfers remain human actions.

No provider should be connected merely to make the project look active. An account request is triggered only by the demand gate documented for the selected experiment.

## Historical Search Note

The prior Tony Robbins plus agent NFTs search found no public workflow that this project could accurately claim to reproduce. The project does not claim endorsement, affiliation, or copied execution. NFTs remain an ordinary candidate and were not selected in the first M3 cycle.
