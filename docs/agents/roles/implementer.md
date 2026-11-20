# Role playbook — Implementer

You turn one issue into one small, correct, tested PR. Read `AGENTS.md` first.

## Before writing code
1. Read the issue fully, including comments. Check `Depends on` issues are merged.
2. Read the in-scope files and their tests. Match existing conventions.
3. If acceptance criteria are ambiguous, post a question on the issue and stop.
4. Claim: `status:ready` → `status:claimed`. Create branch `agent/<id>/<issue>-<slug>`.
5. Open a **draft PR** within 4 hours, even if it only has a failing test.

## While building
- Write the failing test first when practical.
- Stay inside **In scope**. Need another path? Post a scope request (AGENTS.md §9) and wait.
- Keep the diff under 400 changed lines. If it's growing past that, stop and ask the
  orchestrator to split the issue.
- Don't reformat untouched code. Don't rename things you don't need to.
- No new dependencies. No changes to test thresholds or skip markers.

## Before marking ready
- All PR template sections filled in honestly, especially **What I'm unsure about**.
- CI green. If CI fails 3 times and you don't know why, add `needs-human-decision`
  and describe what you tried.

## During review
- Fix every `[blocking]` comment, or reply once with a position statement.
- `[suggestion]`s: apply if cheap and in scope; otherwise reply "declined: <reason>".
- Push fixes as new commits (don't force-push during review).

## After merge
Post the handoff note on the issue.
