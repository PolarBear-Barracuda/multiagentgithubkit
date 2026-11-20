"""config-valid: validate .github/agents.yml and check docs/agents/roster.md is in sync."""
from __future__ import annotations

import re

from config import VALID_ROLES, VALID_STATUSES, Config
from report import Report

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PLACEHOLDER_RE = re.compile(r"YOUR_|TODO|CHANGEME", re.I)


def run(cfg: Config, roster_md: str | None = None, rendered_roster: str | None = None) -> Report:
    r = Report("config-valid")
    data = cfg.data

    if data.get("version") != 1:
        r.error("agents.yml: 'version: 1' is required.")

    if not cfg.owners:
        r.error("agents.yml: at least one owner is required.")
    for o in data.get("owners") or []:
        if PLACEHOLDER_RE.search(str(o.get("github", ""))):
            r.error(f"agents.yml: owner login is still a placeholder ({o.get('github')}).")

    ids, logins = set(), set()
    for a in cfg.agents:
        label = a.id or "<missing id>"
        if not ID_RE.match(a.id):
            r.error(f"agent {label}: id must be lowercase letters, digits and dashes.")
        if a.id in ids:
            r.error(f"agent {label}: duplicate id.")
        ids.add(a.id)
        if not a.github:
            r.error(f"agent {label}: 'github' login is required.")
        elif PLACEHOLDER_RE.search(a.github) and a.status != "inactive":
            r.warn(f"agent {label}: github login looks like a placeholder ({a.github}).")
        if a.login in logins:
            r.error(f"agent {label}: github login {a.github} is used by another agent; every agent needs its own identity.")
        logins.add(a.login)
        if a.login in cfg.owners:
            r.error(f"agent {label}: uses an owner's login. Agents need their own identities.")
        if not a.family:
            r.error(f"agent {label}: 'family' is required.")
        bad = [x for x in a.roles if x not in VALID_ROLES]
        if bad:
            r.error(f"agent {label}: unknown roles {bad}. Valid: {sorted(VALID_ROLES)}.")
        if not a.roles:
            r.error(f"agent {label}: at least one role is required.")
        if a.status not in VALID_STATUSES:
            r.error(f"agent {label}: status must be one of {sorted(VALID_STATUSES)}.")

    active = [a for a in cfg.agents if a.status == "active"]
    working = [a for a in cfg.agents if a.status in ("active", "probation")]
    reviewers = [a for a in active if a.has_role(*cfg.s("reviewing_roles"))]
    if not reviewers:
        r.error("No active agent holds a reviewing role; no agent PR could ever be approved.")
    authoring = cfg.s("authoring_roles")
    for fam in sorted({a.family for a in working if a.has_role(*authoring)}):
        if not any(rv.family != fam for rv in reviewers):
            r.error(f"No active reviewer outside family '{fam}': its PRs can't get a valid approval.")
    if not any(a.has_role("orchestrator") for a in active):
        r.warn("No active orchestrator. The owner will have to assign and sequence work by hand.")

    for area in cfg.areas:
        if not area.paths:
            r.error(f"area {area.name}: 'paths' is required.")
        if area.owner:
            owner = cfg.agent_by_id(area.owner)
            if owner is None:
                r.error(f"area {area.name}: owner '{area.owner}' is not a known agent id.")
            elif owner.status != "active":
                r.warn(f"area {area.name}: owner '{area.owner}' is {owner.status}; its approvals won't count.")

    if not cfg.no_touch:
        r.error("protected_paths.no_touch is empty; governance files would be unprotected.")
    for must in ("/AGENTS.md", "/.github/**"):
        if must not in cfg.no_touch:
            r.error(f"protected_paths.no_touch must include {must}.")

    s = cfg.settings
    for key in ("max_diff_lines", "wip_limit_per_agent", "claim_draft_pr_hours", "claim_idle_hours"):
        v = s.get(key)
        if not isinstance(v, (int, float)) or v <= 0:
            r.error(f"settings.{key} must be a positive number.")
    if isinstance(s.get("claim_draft_pr_hours"), (int, float)) and isinstance(s.get("claim_idle_hours"), (int, float)):
        if s["claim_draft_pr_hours"] >= s["claim_idle_hours"]:
            r.error("settings.claim_draft_pr_hours must be smaller than claim_idle_hours.")

    if roster_md is not None and rendered_roster is not None:
        if roster_md.strip() != rendered_roster.strip():
            r.error("docs/agents/roster.md is out of date. Run: python scripts/governance/gov.py render-roster "
                    "--config .github/agents.yml > docs/agents/roster.md")
    return r
