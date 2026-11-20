# Capability evals

Roles are assigned from these results. Run the same set for every agent so scores
are comparable. Use **your own repository's code** — generic benchmarks don't tell you
how an agent does on your codebase.

## Layout
```
evals/
  tasks/<id>/task.md            implementation tasks (copy tasks/_template.md)
  review-seeds/<id>/            PRs with planted bugs
      seed.md                   how to apply the seeded diff + context for the reviewer
      answer-key.yml            the planted bugs (never shown to agents)
  planning/<id>.md              vague requests to break down (copy planning/_template.md)
  design/<id>.md                architecture questions / ADR prompts (rubric-scored)
  results/YYYY-MM-DD-<agent>.yml  one file per agent per round
```

## Eval types and what they measure
| Type | Measures | Score | Feeds role |
|---|---|---|---|
| implement | first-push CI pass, accepted as-is, stayed in scope | 0–1 | Implementer, Maintainer |
| review | planted bugs found (recall), noise (precision) | F0.5 (favors precision) | Reviewer |
| planning | decomposition quality, testable criteria, escalated when it should | 0–1 | Orchestrator |
| design | ADR quality, spotting architecture violations | 0–1 | Steward |
| tests | mutation score of tests written from acceptance criteria | 0–1 | QA |

## Starter set (aim for this size)
- 8–12 implement tasks: mix of bug fixes, small features, and one deliberately
  ambiguous task (correct behavior: ask before building).
- 6–10 review seeds with 1–3 planted bugs each, **plus 2 clean PRs** with no bugs
  (any blocking comment on those counts as a false positive).
- 3–4 planning prompts, one of which conflicts with an ADR (correct: escalate).
- 2–3 design prompts.
- 3–5 tests tasks; score with a mutation-testing tool for your language.

## Running a round
1. Run each agent on each task in a **scratch fork or branch**, never on `main`.
2. Give every agent the same instructions: AGENTS.md + the role playbook + the task.
3. Record results in `results/YYYY-MM-DD-<agent>.yml` (format: `results/_example.yml`).
4. Score: `python scripts/governance/gov.py eval-score --results evals/results --seeds evals/review-seeds --config .github/agents.yml`
5. Update `docs/agents/capability-matrix.md` and `.github/agents.yml`.

## Keeping evals honest
- Keep answer keys out of agent context (this folder is protected, but also avoid
  pointing agents at it). Rotate in new tasks every few rounds: tasks leak into
  training data and agent memory files over time.
- Score blind where you can: judge the output before checking which agent made it.
