# Autonomous Founder Agent - Traycer Agent Selection Guide

## Default Team Topology

- Use a Codex Chat as the parent, integrator, implementation owner, and final
  decision-maker. Prefer GPT-5.5 Thinking with high reasoning when available.
- Spawn a Claude Code child Chat as the independent commercial challenger,
  architecture critic, UX/copy reviewer, and adversarial code reviewer. Prefer
  the strongest available Claude model with high reasoning.
- Use Traycer Chats for both agents when they must communicate. Do not use a
  Codex Terminal Agent for agent-to-agent coordination because that surface
  cannot receive agent-to-agent messages.
- Run implementation in a fresh worktree based on the current `origin/main`.
  Keep the main workspace clean and use one implementation branch per outcome.

## Routing

- Opportunity selection, buyer pain, competition, positioning, and channel
  strategy: Claude investigates independently; Codex challenges and decides.
- Repository exploration, implementation, tests, deployment, GitHub operations,
  and integration: Codex owns execution.
- Security, platform-policy, conversion-copy, UX, and regression review: Claude
  reviews the proposed plan or diff without editing first.
- Conflicting recommendations: Codex resolves them using current evidence,
  fastest path to verified revenue, access reality, and reversible tests.

## Required Collaboration Loop

1. Codex reads `AGENTS.md` and every source-of-truth file listed there.
2. Codex asks Claude for an independent challenge memo before selecting a
   substantial new revenue experiment or distribution channel.
3. Claude must identify the buyer, purchase evidence, free substitutes,
   distribution path, failure modes, and the strongest reason not to proceed.
4. Codex records a decision, defines a measurable test, and implements it.
5. Claude reviews the resulting diff and live behavior against acceptance
   criteria. Claude reports findings by severity and does not repeat the plan.
6. Codex fixes validated findings, runs tests, deploys when applicable, verifies
   the live surface, and records external effects and revenue truth.
7. Both agents stop building infrastructure when the next uncertainty can be
   answered by distribution, buyer contact, or a smaller market test.

## Execution Authority

The owner authorizes broad lawful strategy and execution. Agents may act
without repeated confirmation only through capabilities marked connected and
enabled in `config/capability_grants.json`. Missing credentials, identity steps,
wallets, sender accounts, or budgets are setup gaps, not strategy prohibitions.
Never bypass platform controls or fabricate access.

## Parallelism Rules

- Parallelize read-only research, competitive analysis, and review.
- Do not let Codex and Claude edit the same files concurrently.
- Give each implementation child a disjoint file scope and a separate worktree.
- Merge only after tests and an independent review. Codex owns final integration.

## Commercial Scoreboard

Every execution summary must report:

- verified gross and net revenue
- qualified traffic or referral change from the recorded baseline
- completed external distribution actions with URLs
- buyer-intent signals and their limitations
- current bottleneck and the next highest-value action
