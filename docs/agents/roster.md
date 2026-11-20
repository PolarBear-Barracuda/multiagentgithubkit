# Agent roster

<!-- GENERATED from .github/agents.yml — do not edit by hand.
     Regenerate: python scripts/governance/gov.py render-roster --config .github/agents.yml > docs/agents/roster.md -->

Role assignments follow `docs/agents/capability-matrix.md`. Rules: `AGENTS.md`.

## Owners

- @PolarBear-Barracuda

## Agents

| ID | GitHub identity | Family | Roles | Status |
|---|---|---|---|---|
| `agent-a` | `chatgpt-codex-connector[bot]` | family-1 | implementer, reviewer | active |
| `agent-b` | `meta-muse-ai[bot]` | family-2 | implementer, reviewer | active |
| `agent-c` | `grok-by-xai[bot]` | family-3 | implementer, reviewer | active |

## Who holds each role

- **orchestrator:** —
- **steward:** —
- **implementer:** `agent-a`, `agent-b`, `agent-c`
- **reviewer:** `agent-a`, `agent-b`, `agent-c`
- **qa:** —
- **maintainer:** —

## Areas

| Area | Paths | Owner |
|---|---|---|

## Reviewer pairing

An approval counts only from an active agent with a reviewing role in a **different family** than the author.

| Author family | Eligible reviewers |
|---|---|
| family-1 | `agent-b`, `agent-c` |
| family-2 | `agent-a`, `agent-c` |
| family-3 | `agent-a`, `agent-b` |
