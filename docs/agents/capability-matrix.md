# Capability matrix

Role assignment follows this file. It is updated by the **owner** after each eval round
(`evals/`), never by agents. Price and popularity are not inputs; cost and availability
break ties only.

**Last eval round:** YYYY-MM-DD · **Next scheduled:** YYYY-MM-DD (monthly, or whenever an
agent's underlying model version changes)

## How to update
1. Run the eval round (see `evals/README.md`) and save results in `evals/results/`.
2. Run `python scripts/governance/gov.py eval-score --results evals/results --seeds evals/review-seeds --config .github/agents.yml`.
3. Paste the output tables below, then update `roles:` in `.github/agents.yml` to match
   the rankings and regenerate `docs/agents/roster.md`
   (`python scripts/governance/gov.py render-roster --config .github/agents.yml > docs/agents/roster.md`).
4. Also look at the live metrics (last 30 days) before changing a role — evals are a sample.

## Scores (latest round)

<!-- Paste the "Scores" table from eval-score here. -->

| Agent | Family | Implement | Review precision | Review recall | Planning | Design | Tests | Evals |
|---|---|---|---|---|---|---|---|---|
| agent-a | family-1 | – | – | – | – | – | – | 0 |

## Role rankings (latest round)

<!-- Paste the "Rankings" section from eval-score here. -->

- **Orchestrator:** –
- **Steward:** –
- **Implementer:** –
- **Reviewer:** –
- **QA:** –
- **Maintainer:** –

## Live metrics (rolling 30 days)

Collect from merged/closed PRs. Track per agent:

| Agent | PRs merged | First-push CI pass | Revert rate | Avg review rounds | Blocking comments upheld | Escalations |
|---|---|---|---|---|---|---|
| agent-a | – | – | – | – | – | – |

**Blocking comments upheld** = reviewer `[blocking]` comments that led to a code change.
A reviewer below ~60% is generating too much noise; below ~40%, move them off the role.

## Assignment rules
- An agent takes a role only if it ranks in the top two for that role, or the role
  would otherwise be empty.
- Every implementer family must have at least one active reviewer from a different family.
- A new agent, or an agent whose model version changed, starts at `status: probation`
  for 5 merged PRs.
- If an agent's live metrics drop below its eval scores for two weeks running, run the
  evals for it again before assigning more work.
