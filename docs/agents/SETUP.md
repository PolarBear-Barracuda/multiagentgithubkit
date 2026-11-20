# Setup guide (for the human owner)

This kit makes the multi-agent operating model real and enforceable in a GitHub repository.
Allow about an hour for steps 1–5. Step 6 (first eval round) takes longer and can follow later.

## What's in the kit

```
AGENTS.md                         rules every agent follows (single source of truth)
ARCHITECTURE.md                   module map + invariants (fill in the TODOs)
docs/adr/                         decision records: README, template, ADR-0001
docs/agents/
  SETUP.md                        this file
  roster.md                       GENERATED from .github/agents.yml
  capability-matrix.md            eval scores and role rankings (drives assignment)
  onboarding.md                   adding / changing / retiring agents, identities, permissions
  review-checklist.md             what reviewers check
  roles/*.md                      one playbook per role
evals/                            capability eval templates + result format
.github/
  agents.yml                      roster, areas, protected paths, settings (machine-readable)
  labels.yml                      label set
  agent-pointer-files.txt         per-tool instruction files that should point to AGENTS.md
  CODEOWNERS                      governance paths -> you
  PULL_REQUEST_TEMPLATE.md
  ISSUE_TEMPLATE/                 task, bug, ADR proposal, decision request
  rulesets/main-protection.json   branch ruleset for the default branch
  workflows/
    agent-governance.yml          pr-hygiene, scope-check, protected-paths, test-weakening, risk-gate, config-valid
    ci.yml                        lint + test (calls scripts/ci/*.sh)
    stale-claims.yml              hourly: warn, then release abandoned claims
    sync-labels.yml               keeps labels in sync with labels.yml + agents.yml
    governance-selftest.yml       unit tests for the governance scripts
scripts/
  governance/                     the checks (Python 3.10+, needs pyyaml) + tests
  setup/bootstrap.sh              one-time GitHub configuration
  setup/write-pointer-files.sh
  ci/lint.sh, ci/test.sh          your project's real lint/test commands go here
```

## 1. Copy the kit into your repository
Copy everything into the repo root. If you already have files at any of these paths
(`.github/CODEOWNERS`, a PR template, `ci.yml`), merge them by hand instead of overwriting.
Add `__pycache__/` to your `.gitignore` if it isn't there.

## 2. Edit the configuration
1. **`.github/agents.yml`**
   - `owners`: your GitHub login.
   - `agents`: one entry per agent with its own identity (step 3), its model `family`, starting
     `roles`, and `status: probation` for every agent until it has eval results.
   - `areas`: match your real directory layout (and ARCHITECTURE.md §2).
   - Check `test_patterns` and `diff_size_exclude` fit your languages.
2. **`.github/CODEOWNERS`**: replace `@YOUR_GITHUB_LOGIN`.
3. **`ARCHITECTURE.md`**: replace every TODO. The invariants section matters most.
4. **`scripts/ci/lint.sh` and `test.sh`**: your real commands, including the coverage gate.
   Add language setup steps in `.github/workflows/ci.yml`.
5. **`.github/agent-pointer-files.txt`**: the default instruction filename each of your
   agents' tools reads, one per line.
6. Check it: `pip install pyyaml && python3 scripts/governance/gov.py validate-config --config .github/agents.yml`

## 3. Create one identity per agent
Follow `docs/agents/onboarding.md`: one GitHub App per agent, installed on this repository only,
with Contents/Pull requests/Issues read & write and **no** Workflows or Administration access.
Put each App's login (`<app-name>[bot]`) in `agents.yml`.

## 4. Bootstrap
```bash
gh auth login                     # as yourself (repo admin)
scripts/setup/bootstrap.sh OWNER/REPO
```
The first run generates `docs/agents/roster.md` and the pointer files, then stops if anything
changed. Commit and push to the default branch, then run it again. The second run syncs labels,
sets squash-only merging with auto-merge, sets read-only workflow tokens, and applies the ruleset.

From then on, you change governance files through PRs too. As a repository admin you can
bypass review on your own PRs (the ruleset's bypass list allows admins, via pull requests only).

## 5. Smoke test (15 minutes)
1. Open a **Task** issue with a tiny change, `risk:low`, scope = one file plus its test.
2. Label it `agent:<implementer-id>` + `status:ready`, and have that agent work it.
3. On the PR, confirm these checks appear: `lint`, `test`, `config-valid`, `pr-hygiene`,
   `scope-check`, `protected-paths`, `test-weakening`, `risk-gate`.
4. Have the reviewer agent (different family) approve. `risk-gate` should turn green.
5. Negative tests (on a throwaway branch): have the agent edit `AGENTS.md`, add a skip marker,
   or touch a file outside scope. Each should fail its check with a clear message.

## 6. First eval round
Follow `evals/README.md`. Build a small set from your own code, run every agent on it, score
with `gov.py eval-score`, record results in `capability-matrix.md`, then set `roles` and
`status` in `agents.yml` from the rankings.

## Your recurring jobs as owner
| When | What |
|---|---|
| Daily-ish | Answer `needs-human-decision` items (Decision requests, ADR proposals). |
| Per `risk:high` PR | Review and approve. |
| When an agent asks | Apply `test-change-approved` or `large-diff-approved` if justified. Only labels **you** apply count. |
| Model version change | Set that agent back to `probation` and run its evals again. |
| Monthly | Eval round, update the capability matrix, adjust roles. |
| Quarterly | Rotate eval tasks, re-read AGENTS.md for rules that no longer earn their place. |

## Known limits (and what covers them)
- **Heuristic checks.** `test-weakening` looks for common patterns in many languages. An agent
  could still weaken tests in a way it doesn't recognize, for example by changing the test
  command in a package manifest. Reviewers and the checklist are the second layer, and
  `scripts/ci/` is protected.
- **Scope edits on the issue don't re-run PR checks.** After you or the orchestrator edit an
  issue's scope, re-run the failed check from the PR's Checks tab (or push a commit).
- **Strict status checks** mean PRs must be up to date with `main` before merging. With many
  agents, expect rebases. A merge queue is the next step if this becomes a bottleneck.
- **Native required approvals are set to 0** because whether App approvals count natively can
  vary. `risk-gate` enforces the real policy. If your agents' approvals count natively, raise
  `required_approving_review_count` to 1 in the ruleset.
- **Pin actions.** The workflows use version tags (`@v4`). For stronger supply-chain safety, pin
  them to full commit SHAs.
- **Labels can be applied by anyone with triage access.** That's why override labels and
  risk downgrades only count when the event log shows an owner applied them.
