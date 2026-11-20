#!/usr/bin/env bash
# One-time repository setup for the multi-agent operating model. Run as the OWNER
# (repo admin) from inside the repository, after editing .github/agents.yml and CODEOWNERS.
#
#   scripts/setup/bootstrap.sh OWNER/REPO               # full setup
#   scripts/setup/bootstrap.sh OWNER/REPO --labels-only # just sync labels (e.g. new agent)
#
# Phase 1 generates files (roster, pointer files). If they changed, the script stops so
# you can commit and push them BEFORE the ruleset starts protecting main. Re-run it after.
#
# Requires: gh (authenticated as a repo admin), git, python3 with pyyaml.
set -euo pipefail

REPO="${1:?usage: bootstrap.sh OWNER/REPO [--labels-only]}"
MODE="${2:-all}"
cd "$(git rev-parse --show-toplevel)"
GOV="python3 scripts/governance/gov.py"

if [ "$MODE" = "--labels-only" ]; then
  $GOV sync-labels --config .github/agents.yml --labels .github/labels.yml --repo "$REPO"
  exit 0
fi

echo "==> Phase 1: generate files"
$GOV render-roster --config .github/agents.yml > docs/agents/roster.md
bash scripts/setup/write-pointer-files.sh

echo "==> Validating configuration"
$GOV validate-config --config .github/agents.yml --roster docs/agents/roster.md \
  --pointer-files .github/agent-pointer-files.txt

if [ -n "$(git status --porcelain)" ]; then
  echo
  echo "Uncommitted changes found:"
  git status --short
  echo
  echo "Commit and push them to the default branch now (before the ruleset is applied),"
  echo "then run this script again."
  exit 1
fi

echo "==> Phase 2: configure GitHub"
echo "--> Syncing labels"
$GOV sync-labels --config .github/agents.yml --labels .github/labels.yml --repo "$REPO"

echo "--> Repository settings: squash-only, auto-merge on, delete merged branches"
gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F allow_auto_merge=true -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY > /dev/null

echo "--> Default workflow token permissions: read-only, Actions can't approve PRs"
gh api -X PUT "repos/$REPO/actions/permissions/workflow" \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false > /dev/null \
  || echo "    (could not set; do it in Settings > Actions > General)"

echo "--> Applying ruleset main-protection"
EXISTING="$(gh api "repos/$REPO/rulesets" --jq '.[] | select(.name=="main-protection") | .id' || true)"
if [ -n "$EXISTING" ]; then
  gh api -X PUT "repos/$REPO/rulesets/$EXISTING" --input .github/rulesets/main-protection.json > /dev/null
  echo "    updated ruleset $EXISTING"
else
  gh api -X POST "repos/$REPO/rulesets" --input .github/rulesets/main-protection.json > /dev/null
  echo "    created ruleset"
fi

cat <<'MSG'

Done. Remaining manual steps (docs/agents/SETUP.md):
  - Create one GitHub App per agent and install it on this repo (docs/agents/onboarding.md).
  - Fill in ARCHITECTURE.md and scripts/ci/lint.sh + test.sh (via a PR; you can bypass review).
  - Open a test issue + PR with one agent to see every check run once.
MSG
