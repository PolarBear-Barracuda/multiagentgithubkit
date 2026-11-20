"""protected-paths: agents may not change governance files."""
from __future__ import annotations

from context import Context
from globmatch import match_any
from report import Report


def run(ctx: Context) -> Report:
    r = Report("protected-paths")
    cfg = ctx.config
    if cfg.is_owner(ctx.author):
        r.note(f"Author @{ctx.author} is an owner: protected paths may be changed (code-owner review still applies).")
        return r

    for ch in ctx.changes:
        for path in ch.touched_paths:
            if match_any(path, cfg.no_touch):
                r.error(f"{path} is a protected path; agents may not change it. Open an issue for the owner instead.")
            elif match_any(path, cfg.add_only):
                is_new_file = ch.status in ("A",) or (ch.status == "C" and path == ch.path)
                if not is_new_file:
                    r.error(f"{path} is add-only: agents may add new files here but not modify, rename or delete existing ones.")
    return r
