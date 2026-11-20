import json
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEAD = "a" * 40
OLD = "b" * 40

BASE_CONFIG = {
    "version": 1,
    "owners": [{"github": "the-owner"}],
    "settings": {"max_diff_lines": 50, "wip_limit_per_agent": 2},
    "protected_paths": {
        "no_touch": ["/AGENTS.md", "/.github/**", "/scripts/governance/**", "/scripts/ci/**"],
        "add_only": ["/docs/adr/**"],
    },
    "test_patterns": ["**/test_*.py", "**/tests/**", "**/*.test.*", "**/*_test.go"],
    "areas": [{"name": "api", "paths": ["/src/api/**"], "owner": "steward-a"}],
    "agents": [
        {"id": "steward-a", "github": "steward-a[bot]", "family": "fam-1", "roles": ["orchestrator", "steward"], "status": "active"},
        {"id": "impl-b", "github": "impl-b[bot]", "family": "fam-2", "roles": ["implementer", "reviewer"], "status": "active"},
        {"id": "impl-c", "github": "impl-c[bot]", "family": "fam-3", "roles": ["implementer", "reviewer"], "status": "active"},
        {"id": "rev-d", "github": "rev-d[bot]", "family": "fam-2", "roles": ["reviewer"], "status": "active"},
        {"id": "newbie", "github": "newbie[bot]", "family": "fam-4", "roles": ["implementer", "reviewer"], "status": "probation"},
    ],
}

GOOD_BODY = """## Linked issue
Closes #12

## Scope
Adds limit validation.

## How I verified
New test test_limit_zero.

## Risk
low

## What I'm unsure about
Nothing major.
"""

ISSUE_BODY = """### Summary

Validate limit.

### Acceptance criteria

- [ ] limit=0 returns 400

### In scope

src/api/items.py
tests/api/

### Out of scope

src/api/auth/**
Don't change pagination.

### Risk

risk:low

### Role

implementer
"""


def ev_label(name, actor, t="2026-01-01T00:00:00Z", event="labeled"):
    return {"event": event, "label": {"name": name}, "actor": {"login": actor}, "created_at": t}


def review(login, state, commit=HEAD, t="2026-01-02T00:00:00Z"):
    return {"user": {"login": login}, "state": state, "commit_id": commit, "submitted_at": t}


def make_diff(files):
    """files: list of (status, path, added_lines, removed_lines[, old_path])."""
    out = []
    for f in files:
        status, path, added, removed = f[:4]
        old = f[4] if len(f) > 4 else path
        out.append(f"diff --git a/{old} b/{path}")
        if status == "R":
            out += ["similarity index 90%", f"rename from {old}", f"rename to {path}"]
        out.append("--- /dev/null" if status == "A" else f"--- a/{old}")
        out.append("+++ /dev/null" if status == "D" else f"+++ b/{path}")
        if added or removed:
            out.append(f"@@ -1,{len(removed)} +1,{len(added)} @@")
            out += ["-" + l for l in removed]
            out += ["+" + l for l in added]
    return "\n".join(out) + "\n"


def make_name_status(files):
    lines = []
    for f in files:
        status, path = f[0], f[1]
        if status == "R":
            lines.append(f"R090\t{f[4]}\t{path}")
        else:
            lines.append(f"{status}\t{path}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def make_ctx(tmp_path):
    from context import Context

    def _make(author="impl-b[bot]", branch="agent/impl-b/12-limit", body=GOOD_BODY, labels=("risk:low",),
              files=(("M", "src/api/items.py", ["x = 1"], ["x = 0"]),),
              issue=None, issue_labels=("agent:impl-b", "status:claimed"), issue_body=ISSUE_BODY,
              pr_events=(), reviews=(), open_prs=None, config=None, pointer_files=(),
              issue_events=None, issue_writers=None):
        d = tmp_path / "ctx"
        d.mkdir(exist_ok=True)
        pr = {"number": 99, "title": "t", "body": body, "headRefName": branch, "headRefOid": HEAD,
              "author": {"login": author}, "labels": [{"name": l} for l in labels], "isDraft": False}
        (d / "pr.json").write_text(json.dumps(pr))
        (d / "files.txt").write_text(make_name_status(files))
        (d / "diff.patch").write_text(make_diff(files))
        if issue is not False:
            iss = issue or {"number": 12, "title": "i", "body": issue_body, "state": "OPEN",
                            "labels": [{"name": l} for l in issue_labels]}
            (d / "issue.json").write_text(json.dumps(iss))
        elif (d / "issue.json").exists():
            (d / "issue.json").unlink()
        if issue_events is None:
            issue_events = [ev_label("agent:" + author.split("[")[0].replace("app/", ""), "steward-a[bot]")]
        (d / "issue_events.ndjson").write_text("\n".join(json.dumps(e) for e in issue_events))
        writers = issue_writers if issue_writers is not None else ["steward-a"]
        edits = {"data": {"repository": {"issue": {"author": {"login": writers[0]} if writers else None,
                 "userContentEdits": {"nodes": [{"editor": {"login": w}} for w in writers[1:]]}}}}}
        (d / "issue_edits.json").write_text(json.dumps(edits))
        (d / "pr_events.ndjson").write_text("\n".join(json.dumps(e) for e in pr_events))
        (d / "reviews.ndjson").write_text("\n".join(json.dumps(r) for r in reviews))
        (d / "open_prs.json").write_text(json.dumps(open_prs if open_prs is not None else [{"number": 99, "author": {"login": author}}]))
        (d / "agents.yml").write_text(yaml.safe_dump(config or BASE_CONFIG))
        (d / "agent-pointer-files.txt").write_text("\n".join(pointer_files))
        return Context(str(d))

    return _make
