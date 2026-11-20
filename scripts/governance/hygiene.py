"""pr-hygiene: identity, roles, linked issue, branch name, risk label, PR body, size, WIP."""
from __future__ import annotations

import re

from config import LABEL_LARGE_DIFF, RISK_RANK, normalize_login, risk_labels
from context import Context, linked_issues, strip_comments
from globmatch import match_any
from issueparse import issue_risk
from report import Report

BRANCH_RE = re.compile(r"^agent/(?P<id>[a-z0-9][a-z0-9-]*)/(?P<issue>\d+)-[a-z0-9][a-z0-9._-]*$")


def parse_sections(body: str) -> dict[str, str]:
    """Split a markdown body into {heading: content} for '## ' headings."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in strip_comments(body).splitlines():
        m = re.match(r"^##\s+(.+?)\s*#*\s*$", line)
        if m and not line.startswith("###"):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def diff_size(ctx: Context) -> int:
    exclude = ctx.config.s("diff_size_exclude") or []
    total = 0
    for ch in ctx.changes:
        if match_any(ch.path, exclude):
            continue
        total += len(ch.added) + len(ch.removed)
    return total


def run(ctx: Context) -> Report:
    r = Report("pr-hygiene")
    cfg = ctx.config
    author = ctx.author

    if cfg.is_owner(author):
        r.note(f"Author @{author} is an owner: agent-only rules skipped.")
        if not risk_labels(ctx.labels):
            r.warn("No risk label. Add one so the risk-gate can apply the right policy.")
        return r

    agent = cfg.agent_by_login(author)
    if agent is None:
        r.error(f"Author @{author} is not listed in .github/agents.yml (agents or owners).")
        return r
    if agent.status == "inactive":
        r.error(f"Agent {agent.id} is inactive and may not open PRs.")
    authoring = cfg.s("authoring_roles")
    if not agent.has_role(*authoring):
        r.error(f"Agent {agent.id} has roles {agent.roles}; authoring PRs needs one of {authoring}.")

    # Linked issue
    issues = linked_issues(ctx.body)
    if len(issues) == 0:
        r.error("PR body must link exactly one issue with 'Closes #N'.")
    elif len(issues) > 1:
        r.error(f"PR links several issues ({', '.join('#' + str(i) for i in issues)}); one PR = one issue.")
    issue_no = issues[0] if len(issues) == 1 else None

    if issue_no is not None:
        if not ctx.issue:
            r.error(f"Linked issue #{issue_no} could not be loaded.")
        else:
            if str(ctx.issue.get("state", "")).upper() not in ("OPEN", ""):
                r.error(f"Linked issue #{issue_no} is not open.")
            if f"agent:{agent.id}" not in ctx.issue_labels:
                r.error(f"Linked issue #{issue_no} is not assigned to you (missing label agent:{agent.id}).")
            elif ctx.issue_events:
                actor = ctx.issue_label_actor(f"agent:{agent.id}")
                if actor is not None and not cfg.can_assign(actor):
                    r.error(f"Label agent:{agent.id} on #{issue_no} was applied by @{normalize_login(actor)}; "
                            "only owners and active orchestrators assign work.")
            else:
                r.warn(f"Couldn't load events for #{issue_no}, so who assigned it wasn't verified.")
            if "status:claimed" not in ctx.issue_labels and "status:in-review" not in ctx.issue_labels:
                r.warn(f"Linked issue #{issue_no} isn't labeled status:claimed. Claim it before working.")

    # Branch name
    m = BRANCH_RE.match(ctx.branch)
    if not m:
        r.error(f"Branch '{ctx.branch}' must match agent/<agent-id>/<issue#>-<slug> (lowercase).")
    else:
        if m.group("id") != agent.id:
            r.error(f"Branch agent id '{m.group('id')}' doesn't match the author's id '{agent.id}'.")
        if issue_no is not None and int(m.group("issue")) != issue_no:
            r.error(f"Branch issue #{m.group('issue')} doesn't match the linked issue #{issue_no}.")

    # Risk labels
    risks = risk_labels(ctx.labels)
    if len(risks) != 1:
        r.error(f"PR needs exactly one risk label (risk:low|risk:med|risk:high); found {risks or 'none'}.")
    else:
        pr_risk = risks[0]
        if ctx.issue:
            ir = issue_risk(ctx.issue.get("body") or "", ctx.issue_labels)
            if ir and RISK_RANK[pr_risk] < RISK_RANK[ir]:
                r.error(f"PR risk {pr_risk} is lower than the linked issue's {ir}.")
        if agent.status == "probation" and pr_risk != "risk:low":
            r.error(f"Agent {agent.id} is on probation and may only author risk:low PRs.")

    # Body sections
    sections = parse_sections(ctx.body)
    lowered = {k.lower(): v for k, v in sections.items()}
    for name in cfg.s("pr_required_sections"):
        content = lowered.get(name.lower())
        if content is None:
            r.error(f"PR body is missing the '## {name}' section.")
        elif not content.strip():
            r.error(f"PR body section '## {name}' is empty.")

    # Size
    size = diff_size(ctx)
    limit = int(cfg.s("max_diff_lines"))
    if size > limit:
        if ctx.label_applied_by_owner(LABEL_LARGE_DIFF):
            r.note(f"Diff is {size} lines (limit {limit}); allowed by owner label {LABEL_LARGE_DIFF}.")
        else:
            r.error(f"Diff is {size} changed lines (limit {limit}, excluding generated/lock files). Split the work.")
    else:
        r.note(f"Diff size: {size}/{limit} lines.")

    # WIP limit
    wip = int(cfg.s("wip_limit_per_agent"))
    mine = [
        p for p in ctx.open_prs
        if normalize_login((p.get("author") or {}).get("login") if isinstance(p.get("author"), dict) else p.get("author")) == agent.login
    ]
    if len(mine) > wip:
        r.error(f"Agent {agent.id} has {len(mine)} open PRs (limit {wip}). Finish or close one first.")
    return r
