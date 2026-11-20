"""Small, dependency-free glob matcher with gitignore-like semantics.

Rules:
  - A leading "/" anchors the pattern to the repository root.
  - A pattern containing "/" is also anchored (so "src/api/" means the root-level src/api).
  - A pattern without "/" matches at any depth (e.g. "*.lock", "conftest.py").
  - A trailing "/" means "this directory and everything under it".
  - "**/" matches zero or more directories; a trailing "**" matches everything below.
  - "*" matches within one path segment; "?" matches one character within a segment.
  - A pattern with no glob characters also matches as a directory prefix
    ("src/api" matches "src/api/x.py").
"""
from __future__ import annotations

import re
from functools import lru_cache

_GLOB_CHARS = set("*?[")


def normalize_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


@lru_cache(maxsize=4096)
def _compile(pattern: str) -> tuple[re.Pattern[str], str | None, bool]:
    raw = pattern.strip().replace("\\", "/")
    anchored = raw.startswith("/")
    p = raw.lstrip("/")
    while p.startswith("./"):
        p = p[2:]
    if p.endswith("/"):
        p = p + "**"
    if "/" in p:
        # Paths with a directory part are relative to the repo root. A leading "**/"
        # still matches at any depth because the regex starts with an optional prefix.
        anchored = True

    literal = None if any(c in _GLOB_CHARS for c in p) else p.rstrip("/")

    out: list[str] = []
    i = 0
    while i < len(p):
        c = p[i]
        if c == "*":
            if p.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if p.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    body = "".join(out)
    if not anchored:
        body = "(?:.*/)?" + body
    return re.compile("^" + body + "$"), literal, anchored


def match(path: str, pattern: str) -> bool:
    if not pattern or not pattern.strip():
        return False
    path = normalize_path(path)
    regex, literal, anchored = _compile(pattern)
    if regex.match(path):
        return True
    if literal is not None:
        if path == literal or path.startswith(literal + "/"):
            return True
        if not anchored and ("/" + path).find("/" + literal + "/") != -1:
            return True
    return False


def match_any(path: str, patterns) -> bool:
    return any(match(path, p) for p in patterns or [])


def looks_like_path(entry: str) -> bool:
    """True if an issue-body line looks like a path/glob rather than prose."""
    e = entry.strip()
    if not e or " " in e or "\t" in e:
        return False
    return "/" in e or "*" in e or "." in e
