# Traycer Handoff

## Purpose

Use Traycer to coordinate a Codex parent agent and a Claude Code child agent on
the Autonomous Founder Agent project. Traycer launches new agent sessions; it
does not import the exact conversation history from another desktop task. The
repository files below provide the shared memory and operating contract.

## Current Commercial State

As of 2026-07-13:

- Verified revenue is $0.
- The free MCP / Agent Preflight is live on GitHub Pages.
- The $149 full-audit Stripe Payment Link is active.
- Preflight report URLs preserve repository and referral attribution.
- The first qualified external distribution action is open as
  `punkpeye/awesome-mcp-devtools#234`.
- The pre-distribution GitHub baseline is recorded in
  `data/qualified_traffic_engine.json`.
- LinkedIn people search is exposed, but no LinkedIn post, comment, or message
  write action is currently available to the agent.

Live funnel:

https://vadim-koenen.github.io/autonomous-founder-agent/site/preflight.html

## Traycer Setup

1. Open Traycer Desktop and select this repository as the workspace folder.
2. In `Settings > Providers`, enable both Codex and Claude Code. Select the
   detected or intended CLI binary and complete each provider's account login.
3. Confirm Traycer sees `.traycer/agent-selection-guide.md` for this workspace.
4. Create a Task named `First Verified Customer` in Epic Mode.
5. Choose `New worktree` from the current `origin/main` for implementation.
6. Start a Codex Chat, not a Codex Terminal Agent, as the parent session.
7. Paste the kickoff prompt below. The parent must create a Claude Code child
   Chat for the independent challenge and later review.
8. Use Full Access only inside the isolated worktree. Accounts, identity setup,
   spend, signing, and irreversible external actions still depend on connected
   capabilities and platform controls.

## Kickoff Prompt

```text
You are the parent operator for the Autonomous Founder Agent.

Read AGENTS.md, .traycer/agent-selection-guide.md,
data/operator_state.json, data/revenue_ledger.json,
data/qualified_traffic_engine.json, config/capability_grants.json,
data/channel_registry.json, and docs/CURRENT_CYCLE.md before deciding.

Objective: produce the highest-probability next move toward the first verified
customer and first $100. Do not assume the current offer remains the winner,
but do not replace it without current demand evidence. Prefer qualified traffic,
buyer outcomes, and reversible market tests over more infrastructure.

Create a Claude Code child Chat and ask it for an independent adversarial memo:
identify the exact buyer, current purchase evidence, direct competitors and free
substitutes, reachable distribution, reasons the offer may fail, and the best
alternative. Do not show Claude your preferred answer first.

After receiving Claude's memo, make the decision. Define one bounded execution
with acceptance criteria and measurable commercial evidence. Implement it in
the isolated worktree. Then ask Claude to review the diff and live behavior.
Address validated findings, run all tests, deploy if applicable, verify the live
result, record external actions and metrics, and report whether verified revenue
changed. Act through connected capabilities without repeated confirmation, but
never invent access or bypass platform rules.
```

## First Task Acceptance Criteria

- Codex and Claude both produce visible child/parent transcripts in one Task.
- Claude produces an independent challenge before Codex selects the action.
- One measurable distribution or conversion improvement is actually executed.
- Codex runs the complete test suite and verifies any public change live.
- The final report includes URLs, baseline movement, blockers, and verified
  revenue rather than treating activity as money.
