"""scope-check: every changed file must match the linked issue's 'In scope' list."""
from __future__ import annotations

from context import Context, linked_issues
from globmatch import match_any
from issueparse import issue_section, path_entries
from report import Report


def run(ctx: Context) -> Report:
    r = Report("scope-check")
    cfg = ctx.config
    if cfg.is_owner(ctx.author):
        r.note(f"Author @{ctx.author} is an owner: scope check skipped.")
        return r

    issues = linked_issues(ctx.body)
    if len(issues) != 1 or not ctx.issue:
        r.error("No single linked issue could be loaded, so scope can't be verified (see pr-hygiene).")
        return r

    writers = ctx.issue_body_writers()
    if writers is None:
        r.warn("Couldn't load the issue's edit history, so who wrote the scope wasn't verified.")
    else:
        bad = [w for w in writers if not cfg.can_assign(w)]
        if bad:
            r.error(
                f"Issue #{issues[0]} was written or edited by {', '.join('@' + b for b in bad)}. "
                "Only owners and active orchestrators may define scope. Post a scope request comment instead."
            )

    body = ctx.issue.get("body") or ""
    in_scope, prose = path_entries(issue_section(body, "In scope"))
    out_scope, _ = path_entries(issue_section(body, "Out of scope"))
    if prose:
        r.warn("Ignored non-path lines under 'In scope': " + "; ".join(prose[:5]))
    if not in_scope:
        r.error(
            f"Issue #{issues[0]} has no machine-readable 'In scope' paths. "
            "Ask the orchestrator to list paths/globs, one per line."
        )
        return r

    allowed = list(in_scope) + list(cfg.s("scope_always_allowed") or [])
    r.note("In scope: " + ", ".join(in_scope))
    for path in ctx.touched_paths():
        if out_scope and match_any(path, out_scope):
            r.error(f"{path} matches the issue's 'Out of scope' list.")
        elif not match_any(path, allowed):
            r.error(f"{path} is outside the issue's 'In scope' list. Post a scope request on the issue instead.")
    return r
