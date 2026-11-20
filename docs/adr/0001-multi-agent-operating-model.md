# ADR-0001: Adopt a light-hierarchy, capability-driven multi-agent operating model

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Proposed by:** owner
- **Decided by:** owner
- **Related issue:** none
- **Supersedes:** none

## Context
Several AI agents from different providers, free and paid, work in this repository at once.
They don't carry memory between sessions, they can make the same mistakes as other models
from the same family, and their relative strengths change as new versions ship. We need
high-quality software with low coordination chaos, and role assignment that follows
measured capability rather than price or habit.

## Options considered
### Option A — Pure collaboration (peers, ownership boundaries only)
- Pros: no bottleneck, simple.
- Cons: no convergence mechanism; duplicated work and conflicting edits; agents
  agreeing with each other in loops.

### Option B — Light hierarchy: orchestrator + specialists, owner on top
- Pros: one agent sequences work and prevents overlap; specialists answer to repo
  artifacts (ADRs, tests, CI), not to a lead agent; roles are reassignable.
- Cons: orchestrator quality matters; needs enforcement tooling.

### Option C — Strong hierarchy with a lead architect agent
- Pros: consistent design voice.
- Cons: the lead's blind spots spread everywhere; context bottleneck; locks one model
  into the top role regardless of future capability changes.

## Decision
We adopt **Option B**. Authority lives in the repository: `AGENTS.md`, `ARCHITECTURE.md`,
accepted ADRs, tests and CI. The orchestrator routes work; it does not decide design.
Domain decisions belong to area owners; the human owner is the final authority.
Roles are assigned from `docs/agents/capability-matrix.md`, which is refreshed from the
evals in `evals/`. Cost is a tie-breaker only.

Enforcement is mechanical, through CI checks in `.github/workflows/agent-governance.yml`
(`pr-hygiene`, `scope-check`, `protected-paths`, `test-weakening`, `risk-gate`,
`config-valid`) and the `main` ruleset.

## Consequences
- Easier: adding or swapping agents; auditing who did what; keeping main stable.
- Harder: agents must write machine-readable issues (scope paths), and work is split
  into small PRs.
- Follow-ups: fill in `ARCHITECTURE.md`; run the first eval round.
- Revisit if: the owner spends more than ~30% of review time on escalations, or
  merge throughput stalls because of review bottlenecks.
