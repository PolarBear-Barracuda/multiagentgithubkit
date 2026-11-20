# Adding, changing and retiring agents

Only the owner performs these steps. The governance files they touch are protected.

## Identity: one GitHub identity per agent
Each agent needs its **own** identity so attribution, the "author never reviews" rule,
and the different-family rule can be enforced.

- **Recommended: one GitHub App per agent.** Apps aren't personal accounts, so you can
  create as many as you need; they get fine-grained, per-repository permissions; and pushes
  made with their tokens trigger workflows. Their login appears as `<app-name>[bot]`.
- **Machine user accounts** also work, but GitHub's Terms of Service allow only one
  free machine account per person on top of your personal account, so you can't
  run several agents on separate free machine accounts.
- Never share one token between agents, and never give an agent your personal token.

### Permissions for an agent's App (repository-scoped)
| Permission | Level | Why |
|---|---|---|
| Contents | Read & write | push branches |
| Pull requests | Read & write | open PRs, review, comment |
| Issues | Read & write | claim issues, labels, comments |
| Metadata | Read | required |
| Workflows | **No access** | agents must not change CI |
| Administration | **No access** | agents must not change rules |
| Actions / Secrets / Environments | **No access** | |

Install each App **only on the repositories that agent works in**. Agents must never be
repository admins and must never appear in ruleset bypass lists.

> **Approvals note.** Whether approvals from App identities count toward GitHub's native
> "required approvals" setting can vary by setup. This kit doesn't depend on it: the
> `risk-gate` check enforces the approval policy for any identity listed in
> `.github/agents.yml`. That's why the ruleset ships with native required approvals set
> to 0, with code-owner review on for governance paths. If your agents' approvals do count
> natively, you can raise it to 1 for an extra layer.

## Adding an agent
1. Create its identity (above) and install it on the repo.
2. Add an entry to `.github/agents.yml` with `status: probation`, its `family`, and the
   roles you're evaluating it for.
3. Regenerate `docs/agents/roster.md` and run `scripts/setup/bootstrap.sh --labels-only`
   to create its `agent:<id>` label.
4. Run the eval set for those roles (`evals/README.md`), then record results in
   `docs/agents/capability-matrix.md`.
5. Give it a system/instruction prompt that says only: "You are `<id>` in repository X.
   Read and follow AGENTS.md and docs/agents/roles/<role>.md." Keep rules in the repo,
   not in the prompt.
6. After 5 merged `risk:low` PRs with no reverts, switch to `status: active`.

## When an agent's model version changes
Set it back to `probation` and run the evals again. Capabilities can move in either direction.

## Retiring an agent
1. Set `status: inactive` (keeps history readable). Its open claims are released by the
   stale-claim job, or release them by hand.
2. Revoke its App installation / token.
3. Regenerate the roster.
