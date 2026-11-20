#!/usr/bin/env bash
# Write a pointer file at every path listed in .github/agent-pointer-files.txt so each
# agent tool's default instruction file sends it to AGENTS.md (one source of truth).
# Run from the repository root.
set -euo pipefail
LIST=".github/agent-pointer-files.txt"
[ -f "$LIST" ] || { echo "missing $LIST" >&2; exit 1; }

count=0
while IFS= read -r line || [ -n "$line" ]; do
  path="$(echo "$line" | sed 's/#.*//' | xargs)"
  [ -z "$path" ] && continue
  mkdir -p "$(dirname "$path")"
  cat > "$path" <<'POINTER'
# Agent instructions

Read and follow `/AGENTS.md` in this repository. It is the single source of truth for
rules, roles, workflow and escalation. Then read your role playbook in
`/docs/agents/roles/<role>.md`. Your identity and roles are in `/.github/agents.yml`.

Do not add rules to this file. It is a protected path; only the owner edits it.
POINTER
  echo "wrote $path"
  count=$((count + 1))
done < "$LIST"
echo "$count pointer file(s) written."
