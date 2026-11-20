#!/usr/bin/env bash
# Collect everything the PR governance checks need into a context directory.
#
# Usage: collect_context.sh <pr-checkout-dir> <governance-checkout-dir> <out-dir>
# Env:   GH_TOKEN, GITHUB_REPOSITORY, PR_NUMBER, BASE_SHA, HEAD_SHA
#
# Governance config and scripts come from the BASE branch checkout, so a PR can't
# weaken the checks that judge it.
set -euo pipefail

PR_DIR="$1"; GOV_DIR="$2"; OUT="$3"
: "${GITHUB_REPOSITORY:?}" "${PR_NUMBER:?}" "${BASE_SHA:?}" "${HEAD_SHA:?}"
mkdir -p "$OUT"
REPO="$GITHUB_REPOSITORY"

gh pr view "$PR_NUMBER" --repo "$REPO" \
  --json number,title,body,headRefName,headRefOid,baseRefName,author,labels,isDraft > "$OUT/pr.json"

# Diff between the merge base and the PR head.
git -C "$PR_DIR" -c core.quotePath=false diff --name-status -M "$BASE_SHA...$HEAD_SHA" > "$OUT/files.txt"
git -C "$PR_DIR" -c core.quotePath=false diff -U0 -M --no-color "$BASE_SHA...$HEAD_SHA" > "$OUT/diff.patch"

gh api "repos/$REPO/issues/$PR_NUMBER/events" --paginate --jq '.[]' > "$OUT/pr_events.ndjson"
gh api "repos/$REPO/pulls/$PR_NUMBER/reviews" --paginate --jq '.[]' > "$OUT/reviews.ndjson"
gh pr list --repo "$REPO" --state open --limit 500 --json number,author,isDraft > "$OUT/open_prs.json"

cp "$GOV_DIR/.github/agents.yml" "$OUT/agents.yml"
if [ -f "$GOV_DIR/.github/agent-pointer-files.txt" ]; then
  cp "$GOV_DIR/.github/agent-pointer-files.txt" "$OUT/agent-pointer-files.txt"
fi

ISSUE="$(python3 "$GOV_DIR/scripts/governance/gov.py" linked-issue --context "$OUT" || true)"
if [ -n "$ISSUE" ]; then
  gh issue view "$ISSUE" --repo "$REPO" --json number,title,body,labels,state,author > "$OUT/issue.json" \
    || echo "could not load issue #$ISSUE" >&2
  gh api "repos/$REPO/issues/$ISSUE/events" --paginate --jq '.[]' > "$OUT/issue_events.ndjson" \
    || echo "could not load events for #$ISSUE" >&2
  # shellcheck disable=SC2016  # $owner etc. are GraphQL variables, not shell
  gh api graphql -f owner="${REPO%%/*}" -f name="${REPO##*/}" -F number="$ISSUE" -f query='
    query($owner: String!, $name: String!, $number: Int!) {
      repository(owner: $owner, name: $name) {
        issue(number: $number) {
          author { login }
          userContentEdits(first: 100) { nodes { editor { login } editedAt } }
        }
      }
    }' > "$OUT/issue_edits.json" || echo "could not load edit history for #$ISSUE" >&2
fi

echo "Context collected in $OUT (linked issue: ${ISSUE:-none})"
