"""risk-gate: the approval policy, enforced for any identity type (users or Apps).

risk:low  -> 1 valid reviewer approval (or an owner approval)
risk:med  -> 1 valid reviewer approval AND, for every area touched, approval from that
             area's owner agent, a steward, or an owner (an owner approval satisfies both)
risk:high -> owner approval (+ a valid agent reviewer approval if
             settings.high_risk_requires_agent_review)
Always:   no outstanding 'changes requested' from a registered reviewer/owner,
          no 'needs-human-decision' label, exactly one risk label, risk downgrades only by an owner.

A *valid* agent approval: reviewer is an active agent (not probation/inactive) holding a
reviewing role, is not the author, is from a different model family than an agent author,
and (if require_approval_on_head) approved the PR's current head commit.
"""
from __future__ import annotations

from config import LABEL_DECISION, RISK_RANK, Agent, normalize_login, risk_labels
from context import Context
from globmatch import match_any
from report import Report


def latest_states(reviews: list[dict]) -> dict[str, dict]:
    """Latest decisive review per reviewer (COMMENTED reviews don't change state)."""
    out: dict[str, dict] = {}
    for rv in sorted(reviews, key=lambda x: x.get("submitted_at") or ""):
        state = (rv.get("state") or "").upper()
        login = normalize_login((rv.get("user") or {}).get("login"))
        if not login or state not in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            continue
        out[login] = rv
    return out


def touched_areas(ctx: Context) -> list:
    areas = []
    for area in ctx.config.areas:
        if any(match_any(p, area.paths) for p in ctx.touched_paths()):
            areas.append(area)
    return areas


def run(ctx: Context) -> Report:
    r = Report("risk-gate")
    cfg = ctx.config
    author_login = ctx.author
    author_agent = cfg.agent_by_login(author_login)
    author_is_owner = cfg.is_owner(author_login)
    reviewing_roles = cfg.s("reviewing_roles")

    # --- label preconditions ------------------------------------------
    if LABEL_DECISION in ctx.labels:
        r.error(f"'{LABEL_DECISION}' is set: merging is blocked until the owner decides and removes it.")

    risks = risk_labels(ctx.labels)
    if len(risks) != 1:
        r.error(f"Exactly one risk label required; found {risks or 'none'}.")
        return r
    risk = risks[0]

    ever = [
        (ev.get("label") or {}).get("name")
        for ev in ctx.pr_events
        if ev.get("event") == "labeled" and (ev.get("label") or {}).get("name") in RISK_RANK
    ]
    if ever:
        highest = max(ever, key=lambda x: RISK_RANK[x])
        if RISK_RANK[risk] < RISK_RANK[highest] and not ctx.label_applied_by_owner(risk):
            r.error(f"Risk was lowered from {highest} to {risk}; only an owner may lower risk.")

    # --- classify approvals --------------------------------------------
    head = ctx.head_sha
    on_head_required = bool(cfg.s("require_approval_on_head"))
    states = latest_states(ctx.reviews)

    owner_approvals: list[str] = []
    agent_approvals: list[Agent] = []
    for login, rv in states.items():
        state = (rv.get("state") or "").upper()
        reviewer_agent = cfg.agent_by_login(login)
        reviewer_is_owner = cfg.is_owner(login)

        if state == "CHANGES_REQUESTED" and (reviewer_is_owner or reviewer_agent):
            r.error(f"@{login} requested changes. Resolve them and get a new review.")
            continue
        if state != "APPROVED":
            continue
        if login == author_login:
            continue
        if on_head_required and head and rv.get("commit_id") and rv.get("commit_id") != head:
            r.note(f"Approval by @{login} is on an older commit and doesn't count.")
            continue
        if reviewer_is_owner:
            owner_approvals.append(login)
            continue
        if reviewer_agent is None:
            r.note(f"Approval by @{login} ignored: not in .github/agents.yml.")
            continue
        if reviewer_agent.status != "active":
            r.note(f"Approval by {reviewer_agent.id} ignored: status is {reviewer_agent.status}.")
            continue
        if not reviewer_agent.has_role(*reviewing_roles):
            r.note(f"Approval by {reviewer_agent.id} ignored: no reviewing role ({reviewing_roles}).")
            continue
        if author_agent and reviewer_agent.family == author_agent.family:
            r.note(f"Approval by {reviewer_agent.id} ignored: same model family as the author ({author_agent.family}).")
            continue
        agent_approvals.append(reviewer_agent)

    has_owner = bool(owner_approvals)
    reviewer_ok = has_owner or any(a.has_role("reviewer", "steward") for a in agent_approvals)

    # --- apply policy ---------------------------------------------------
    if risk == "risk:low":
        if not reviewer_ok:
            r.error("risk:low needs 1 valid reviewer approval on the latest commit.")
    elif risk == "risk:med":
        if not reviewer_ok:
            r.error("risk:med needs a valid reviewer approval on the latest commit.")
        if not has_owner:
            areas = touched_areas(ctx)
            stewards = [a for a in agent_approvals if a.has_role("steward")]
            if not areas:
                if not stewards:
                    r.error("risk:med needs approval from a steward (different family) or an owner.")
            for area in areas:
                owner_agent = cfg.agent_by_id(area.owner) if area.owner else None
                ok = bool(stewards) or (owner_agent is not None and owner_agent in agent_approvals)
                if not ok:
                    who = f"area owner {area.owner}" if area.owner else "a steward"
                    r.error(f"risk:med touches area '{area.name}': needs approval from {who}, a steward, or an owner.")
    elif risk == "risk:high":
        if not has_owner and not author_is_owner:
            r.error("risk:high needs an owner's approval.")
        elif not has_owner and author_is_owner:
            r.note("risk:high authored by an owner.")
        if cfg.s("high_risk_requires_agent_review") and not any(a.has_role("reviewer", "steward") for a in agent_approvals):
            r.error("risk:high also needs a valid agent reviewer approval (settings.high_risk_requires_agent_review).")

    if r.ok:
        approvers = [f"@{o} (owner)" for o in owner_approvals] + [f"{a.id} ({a.family})" for a in agent_approvals]
        r.note(f"{risk}: policy satisfied by " + (", ".join(approvers) or "owner authorship"))
    return r
