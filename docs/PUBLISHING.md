# Publishing Notes

## Connected Route

The public repository and GitHub Pages are connected owner-controlled channels:

- Dashboard: https://vadim-koenen.github.io/autonomous-founder-agent/site/
- Source: https://github.com/vadim-koenen/autonomous-founder-agent
- Operator state: https://vadim-koenen.github.io/autonomous-founder-agent/data/operator_state.json

The root `index.html` redirects to `site/`. GitHub Pages serves the dashboard, functional preflight tool, machine-readable state, evidence scan, product contracts, offer samples, channel registry, and revenue ledger directly from the repository.

## Scheduled Publication

`.github/workflows/revenue-operator.yml` runs every six hours at minute `17` and on manual dispatch. It refreshes stable public evidence and validation assets, runs the decision cycle, executes the complete test suite, and commits only changed public state.

The workflow uses the scoped GitHub Actions token for repository content, model access, and at most three inbound-only public issue replies that match the recorded label and capability grant. It cannot open unsolicited issues, send email or direct messages, activate checkout, transact with a wallet, buy ads, mint NFTs, or touch broker APIs.

## Public-Safe Assets

- functional MCP / agent public-metadata preflight
- truthful product activation state and OpenAPI contract
- synthetic preflight input and response, explicitly marked as non-market evidence
- current three-role experiment portfolio
- evidence-backed opportunity scan and ranking
- public channel registry
- machine-readable and human-readable revenue ledgers
- MCP / Agent Preflight Full Audit offer, intake, public target queue, and audit hooks
- buyer-ready full-audit sales page and public commercial-funnel metrics
- launch-gate product sample and report schema
- opportunity-pulse manifest and sample
- generated social preview image
- historical M1/M2 artifacts clearly separated from current decisions

## Not Connected

- no marketplace seller account
- no Stripe API, webhook secret, account-management access, or stored payment credential; one owner-provided public Stripe Payment Link is active
- no dedicated wallet, receiving address, runtime host, or live paid x402 endpoint
- no ad account
- no email or direct-message sender
- no dedicated social posting account
- an owner LinkedIn profile is available for manual publication only; automated posting and messaging remain disabled
- no customer private repository or system access
- no trading, investing, broker, exchange, or financial-account API

## Publication Boundary

Publishing public-safe files through the connected repository is autonomous. Identity, KYC, legal acceptance, bank or tax setup, contracts, private access grants, and fund transfers remain human actions.

No provider should be connected merely to make the project look active. An account request is triggered only by the demand gate documented for the selected experiment.

The free preflight needs no owner account and performs no payment action. The human full-audit rail uses the active owner-provided public Stripe Payment Link. The metered contract remains inactive until at least three qualified recurring-use requests identify a real machine workflow, after which wallet and runtime setup become explicit human approvals.

## Historical Search Note

The prior Tony Robbins plus agent NFTs search found no public workflow that this project could accurately claim to reproduce. The project does not claim endorsement, affiliation, or copied execution. NFTs remain an ordinary candidate and were not selected in the first M3 cycle.
