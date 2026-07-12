# MCP / Agent Preflight

One deterministic engine, sold through two channels:

| Offer | Buyer | Price | Status |
| --- | --- | ---: | --- |
| Public metadata preflight | Agent builders evaluating a repository | Free | Browser demo ready |
| Metered preflight API | Agents and orchestrators evaluating tools repeatedly | $0.25 basic / $1 full | Contract ready; wallet and runtime host pending |
| Full launch audit | Human teams preparing an MCP server or agent endpoint for launch | $149 fixed | Stripe Payment Link active |

The engine evaluates public repository and registry metadata without executing target code. It reports maintenance, documentation, licensing, security-policy, version, transport, and HTTPS-readiness signals. It does not claim to be a security audit or a live protocol test.

## Run Locally

From the repository root:

```bash
python3 scripts/run_preflight.py \
  --input products/mcp-agent-preflight/sample-input.json
```

To inspect a real public GitHub repository:

```bash
python3 scripts/run_preflight.py \
  --repo-url https://github.com/OWNER/REPOSITORY
```

The live-repository adapter only accepts `https://github.com/OWNER/REPOSITORY` and only requests the fixed `api.github.com` host. A runtime-only `GITHUB_TOKEN` is optional and is never included in the report.

## Commercial Boundary

- `site/preflight.html` is the free functional demonstration.
- `openapi.json` defines the planned public and metered routes.
- `product.json` is the truthful activation state for human and x402 rails.
- The human checkout is the owner-provided public Stripe Payment Link; no Stripe API key or account-management access is stored.
- No paid agent endpoint, wallet receipt, customer, or revenue is claimed until independently configured and verified.

The official MCP Inspector remains the correct tool for interactive protocol debugging. This product packages a repeatable decision report for buyers and agents who need to screen many candidate servers.
