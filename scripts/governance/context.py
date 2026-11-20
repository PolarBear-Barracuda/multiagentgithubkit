"""Load the PR context directory produced by collect_context.sh.

Context directory layout (all files optional except pr.json):
  pr.json             gh pr view --json number,title,body,headRefName,headRefOid,baseRefName,author,labels,isDraft
  files.txt           git diff --name-status -M <base>...<head>
  diff.patch          git diff -U0 -M <base>...<head>
  issue.json          gh issue view <linked> --json number,title,body,labels,state,author
  issue_events.ndjson REST issue events for the linked issue
  issue_edits.json    GraphQL: issue author + userContentEdits (who edited the body)
  pr_events.ndjson    REST issue events for the PR (one JSON object per line)
  reviews.ndjson      REST pull request reviews (one JSON object per line)
  open_prs.json       gh pr list --state open --json number,author,isDraft
  agents.yml          roster/config from the base branch
  agent-pointer-files.txt
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from config import Config, load_config, normalize_login

LINK_RE = re.compile(r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)\b")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


@dataclass
class FileChange:
    status: str  # A, M, D, R, C, T
    path: str  # new path (or the path for A/M/D)
    old_path: str | None = None
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def touched_paths(self) -> list[str]:
        paths = [self.path]
        if self.old_path and self.old_path != self.path:
            paths.append(self.old_path)
        return paths


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text or "")


def linked_issues(body: str) -> list[int]:
    seen: list[int] = []
    for m in LINK_RE.finditer(strip_comments(body)):
        n = int(m.group(1))
        if n not in seen:
            seen.append(n)
    return seen


def parse_name_status(text: str) -> list[FileChange]:
    changes = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        code = parts[0].strip()
        kind = code[:1]
        if kind in ("R", "C") and len(parts) >= 3:
            changes.append(FileChange(status=kind, path=parts[2], old_path=parts[1]))
        elif len(parts) >= 2:
            changes.append(FileChange(status=kind, path=parts[1]))
    return changes


def parse_unified_diff(text: str) -> dict[str, dict[str, list[str]]]:
    """Return {path: {"added": [...], "removed": [...]}} from a unified diff."""
    result: dict[str, dict[str, list[str]]] = {}
    current = None
    old_path = new_path = None
    in_hunk = False

    def start_file():
        nonlocal current
        path = new_path if new_path and new_path != "/dev/null" else old_path
        if path:
            current = result.setdefault(path, {"added": [], "removed": []})

    for line in (text or "").splitlines():
        if line.startswith("diff --git "):
            current = None
            in_hunk = False
            old_path = new_path = None
            m = re.match(r"^diff --git a/(.*) b/(.*)$", line)
            if m:
                old_path, new_path = m.group(1), m.group(2)
                start_file()
            continue
        if not in_hunk:
            if line.startswith("--- "):
                p = line[4:].strip()
                if p != "/dev/null":
                    old_path = p[2:] if p.startswith("a/") else p
                continue
            if line.startswith("+++ "):
                p = line[4:].strip()
                new_path = "/dev/null" if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
                # re-key in case the header guess was wrong
                path = new_path if new_path != "/dev/null" else old_path
                if path:
                    current = result.setdefault(path, {"added": [], "removed": []})
                continue
            if line.startswith("rename to "):
                new_path = line[len("rename to "):].strip()
                start_file()
                continue
            if line.startswith("@@"):
                in_hunk = True
            continue
        # inside hunks
        if line.startswith("@@"):
            continue
        if current is None:
            continue
        if line.startswith("+"):
            current["added"].append(line[1:])
        elif line.startswith("-"):
            current["removed"].append(line[1:])
    # drop phantom keys created from the diff --git header when +++ re-keyed
    return result


def _read(path: str) -> str | None:
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _read_json(path: str):
    text = _read(path)
    if text is None or not text.strip():
        return None
    return json.loads(text)


def _read_ndjson(path: str) -> list[dict]:
    text = _read(path)
    if not text:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, list):
            out.extend(obj)
        else:
            out.append(obj)
    return out


class Context:
    def __init__(self, ctx_dir: str, config: Config | None = None):
        self.dir = ctx_dir
        self.pr = _read_json(os.path.join(ctx_dir, "pr.json")) or {}
        cfg_path = os.path.join(ctx_dir, "agents.yml")
        if config is not None:
            self.config = config
        else:
            ptr = os.path.join(ctx_dir, "agent-pointer-files.txt")
            self.config = load_config(cfg_path, ptr if os.path.exists(ptr) else "")
        self.changes = parse_name_status(_read(os.path.join(ctx_dir, "files.txt")) or "")
        diff = parse_unified_diff(_read(os.path.join(ctx_dir, "diff.patch")) or "")
        for ch in self.changes:
            d = diff.get(ch.path) or (diff.get(ch.old_path) if ch.old_path else None)
            if d:
                ch.added, ch.removed = d["added"], d["removed"]
        self.issue = _read_json(os.path.join(ctx_dir, "issue.json"))
        self.issue_events = _read_ndjson(os.path.join(ctx_dir, "issue_events.ndjson"))
        self.issue_edits = _read_json(os.path.join(ctx_dir, "issue_edits.json"))
        self.pr_events = _read_ndjson(os.path.join(ctx_dir, "pr_events.ndjson"))
        self.reviews = _read_ndjson(os.path.join(ctx_dir, "reviews.ndjson"))
        self.open_prs = _read_json(os.path.join(ctx_dir, "open_prs.json")) or []

    # ---- convenience ---------------------------------------------------
    @property
    def author(self) -> str:
        a = self.pr.get("author") or {}
        return normalize_login(a.get("login") if isinstance(a, dict) else a)

    @property
    def labels(self) -> list[str]:
        return [l["name"] if isinstance(l, dict) else str(l) for l in self.pr.get("labels") or []]

    @property
    def body(self) -> str:
        return self.pr.get("body") or ""

    @property
    def branch(self) -> str:
        return self.pr.get("headRefName") or ""

    @property
    def head_sha(self) -> str:
        return self.pr.get("headRefOid") or ""

    @property
    def issue_labels(self) -> list[str]:
        if not self.issue:
            return []
        return [l["name"] if isinstance(l, dict) else str(l) for l in self.issue.get("labels") or []]

    def touched_paths(self) -> list[str]:
        out: list[str] = []
        for ch in self.changes:
            for p in ch.touched_paths:
                if p not in out:
                    out.append(p)
        return out

    def issue_label_actor(self, label: str) -> str | None:
        """Login of whoever most recently applied `label` to the linked issue."""
        last = None
        for ev in self.issue_events:
            if ev.get("event") == "labeled" and (ev.get("label") or {}).get("name") == label:
                if last is None or (ev.get("created_at") or "") >= (last.get("created_at") or ""):
                    last = ev
        return (last.get("actor") or {}).get("login") if last else None

    def issue_body_writers(self) -> list[str] | None:
        """Author plus everyone who edited the issue body; None if unknown."""
        data = self.issue_edits
        if not data:
            return None
        node = data
        for key in ("data", "repository", "issue"):
            if isinstance(node, dict) and key in node:
                node = node[key]
        if not isinstance(node, dict):
            return None
        writers = []
        author = (node.get("author") or {}).get("login")
        if author:
            writers.append(author)
        for e in (node.get("userContentEdits") or {}).get("nodes") or []:
            login = (e.get("editor") or {}).get("login")
            if login and login not in writers:
                writers.append(login)
        return writers

    def label_applied_by_owner(self, label: str) -> bool:
        """True if `label` is on the PR and its most recent 'labeled' event was by an owner."""
        if label not in self.labels:
            return False
        last = None
        for ev in self.pr_events:
            if ev.get("event") == "labeled" and (ev.get("label") or {}).get("name") == label:
                if last is None or (ev.get("created_at") or "") >= (last.get("created_at") or ""):
                    last = ev
        if last is None:
            return False
        actor = (last.get("actor") or {}).get("login")
        return self.config.is_owner(actor)
