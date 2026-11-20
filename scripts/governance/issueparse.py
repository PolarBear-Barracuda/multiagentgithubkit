"""Parse sections of issues created with the Task issue form."""
from __future__ import annotations

import re

from config import RISK_RANK
from context import strip_comments
from globmatch import looks_like_path


def issue_section(body: str, heading_prefix: str) -> str | None:
    """Content under a '### <heading>' whose text starts with heading_prefix (case-insensitive)."""
    lines = strip_comments(body or "").splitlines()
    out: list[str] = []
    capturing = False
    found = False
    for line in lines:
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if m:
            if capturing:
                break
            if m.group(1).strip().lower().startswith(heading_prefix.lower()):
                capturing = True
                found = True
            continue
        if capturing:
            out.append(line)
    return "\n".join(out).strip() if found else None


def _clean_entry(line: str) -> str:
    s = line.strip()
    s = re.sub(r"^[-*+]\s+(\[[ xX]\]\s+)?", "", s)  # bullets / checkboxes
    s = s.strip().strip("`").strip()
    return s


def path_entries(section: str | None) -> tuple[list[str], list[str]]:
    """Return (paths, ignored_prose_lines) from an issue section."""
    if not section:
        return [], []
    paths, prose = [], []
    for line in section.splitlines():
        if line.strip().startswith("```"):
            continue
        e = _clean_entry(line)
        if not e or e == "_No response_":
            continue
        if looks_like_path(e):
            paths.append(e)
        else:
            prose.append(e)
    return paths, prose


def issue_risk(body: str, labels: list[str]) -> str | None:
    """Highest risk declared by the issue's labels or its Risk form field."""
    found = [l for l in labels if l in RISK_RANK]
    sec = issue_section(body, "Risk")
    if sec:
        m = re.search(r"risk:(low|med|high)", sec)
        if m:
            found.append("risk:" + m.group(1))
    if not found:
        return None
    return max(found, key=lambda x: RISK_RANK[x])
