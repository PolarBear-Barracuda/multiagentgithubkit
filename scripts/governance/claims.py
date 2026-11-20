"""Stale-claim management: warn, then release issues an agent claimed but isn't working on.

decide() is pure and unit-tested. run() gathers data with the gh CLI and applies actions.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

from config import Config
from report import Report

WARN_MARKER = "<!-- stale-claim-warning -->"
RELEASE_MARKER = "<!-- stale-claim-released -->"


def parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Decision:
    action: str  # none | warn | release
    reason: str


def decide(*, now: datetime, claimed_at: datetime | None, pr_last_commit: datetime | None,
           has_pr: bool, blocked: bool, already_warned: bool,
           draft_hours: float, idle_hours: float) -> Decision:
    if blocked:
        return Decision("none", "blocked")
    if claimed_at is None:
        return Decision("none", "no claim event found")
    if has_pr:
        last = pr_last_commit or claimed_at
        idle = (now - max(last, claimed_at)).total_seconds() / 3600
        if idle >= idle_hours:
            return Decision("release", f"no commits for {idle:.0f}h (limit {idle_hours:g}h)")
        return Decision("none", f"active ({idle:.1f}h since last commit)")
    age = (now - claimed_at).total_seconds() / 3600
    if age >= idle_hours:
        return Decision("release", f"claimed {age:.0f}h ago with no PR (limit {idle_hours:g}h)")
    if age >= draft_hours and not already_warned:
        return Decision("warn", f"claimed {age:.1f}h ago and no draft PR yet (expected within {draft_hours:g}h)")
    return Decision("none", f"claimed {age:.1f}h ago")


# ---------------------------------------------------------------------------
def _gh(args: list[str]) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _gh_ndjson(path: str) -> list[dict]:
    out = _gh(["api", path, "--paginate", "--jq", ".[]"])
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def run(repo: str, cfg: Config, dry_run: bool = False, now: datetime | None = None) -> Report:
    r = Report("stale-claims")
    now = now or datetime.now(timezone.utc)
    draft_h = float(cfg.s("claim_draft_pr_hours"))
    idle_h = float(cfg.s("claim_idle_hours"))

    issues = json.loads(_gh(["issue", "list", "--repo", repo, "--label", "status:claimed", "--state", "open",
                             "--limit", "500", "--json", "number,labels"]))
    prs = json.loads(_gh(["pr", "list", "--repo", repo, "--state", "open", "--limit", "500",
                          "--json", "number,headRefName,commits"]))

    for issue in issues:
        n = issue["number"]
        labels = [l["name"] for l in issue.get("labels", [])]
        agent_ids = [l.split(":", 1)[1] for l in labels if l.startswith("agent:")]
        events = _gh_ndjson(f"repos/{repo}/issues/{n}/events")
        claim_events = [e for e in events if e.get("event") == "labeled" and (e.get("label") or {}).get("name") == "status:claimed"]
        claimed_at = parse_time(max((e["created_at"] for e in claim_events), default=None))

        pr_match = None
        for pr in prs:
            m = re.match(r"^agent/([^/]+)/(\d+)-", pr.get("headRefName", ""))
            if m and int(m.group(2)) == n and (not agent_ids or m.group(1) in agent_ids):
                pr_match = pr
                break
        last_commit = None
        if pr_match:
            dates = [parse_time(c.get("committedDate")) for c in pr_match.get("commits") or []]
            dates = [d for d in dates if d]
            last_commit = max(dates) if dates else None

        comments = json.loads(_gh(["issue", "view", str(n), "--repo", repo, "--json", "comments"])).get("comments", [])
        already_warned = False
        if claimed_at:
            already_warned = any(WARN_MARKER in (c.get("body") or "") and (parse_time(c.get("createdAt")) or now) >= claimed_at
                                 for c in comments)

        d = decide(now=now, claimed_at=claimed_at, pr_last_commit=last_commit, has_pr=pr_match is not None,
                   blocked="status:blocked" in labels, already_warned=already_warned,
                   draft_hours=draft_h, idle_hours=idle_h)
        who = ", ".join(f"agent:{a}" for a in agent_ids) or "unassigned"
        if d.action == "none":
            r.note(f"#{n} ({who}): {d.reason}")
            continue
        if d.action == "warn":
            r.warn(f"#{n} ({who}): {d.reason}")
            body = (f"{WARN_MARKER}\n⏰ Claim check: {d.reason}. Open a draft PR, or comment if you're blocked "
                    f"(add `status:blocked`). The claim is released after {idle_h:g}h without progress.")
            if not dry_run:
                _gh(["issue", "comment", str(n), "--repo", repo, "--body", body])
        elif d.action == "release":
            r.warn(f"#{n} ({who}): releasing — {d.reason}")
            if not dry_run:
                args = ["issue", "edit", str(n), "--repo", repo, "--remove-label", "status:claimed", "--add-label", "status:ready"]
                for a in agent_ids:
                    args += ["--remove-label", f"agent:{a}"]
                _gh(args)
                body = (f"{RELEASE_MARKER}\n🔓 Claim released: {d.reason}. Orchestrator: please reassign. "
                        f"Previous assignee: post a handoff note if you made progress.")
                _gh(["issue", "comment", str(n), "--repo", repo, "--body", body])
    if dry_run:
        r.note("Dry run: no changes made.")
    return r
