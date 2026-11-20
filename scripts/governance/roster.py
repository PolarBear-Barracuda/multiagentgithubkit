"""Render docs/agents/roster.md from .github/agents.yml (so the two never drift)."""
from __future__ import annotations

from config import Config

ROLE_ORDER = ["orchestrator", "steward", "implementer", "reviewer", "qa", "maintainer"]


def render(cfg: Config) -> str:
    lines = [
        "# Agent roster",
        "",
        "<!-- GENERATED from .github/agents.yml — do not edit by hand.",
        "     Regenerate: python scripts/governance/gov.py render-roster --config .github/agents.yml > docs/agents/roster.md -->",
        "",
        "Role assignments follow `docs/agents/capability-matrix.md`. Rules: `AGENTS.md`.",
        "",
        "## Owners",
        "",
    ]
    for o in cfg.data.get("owners") or []:
        lines.append(f"- @{o.get('github')}")
    lines += ["", "## Agents", "", "| ID | GitHub identity | Family | Roles | Status |", "|---|---|---|---|---|"]
    for a in sorted(cfg.agents, key=lambda x: x.id):
        roles = ", ".join(r for r in ROLE_ORDER if r in a.roles)
        lines.append(f"| `{a.id}` | `{a.github}` | {a.family} | {roles} | {a.status} |")

    lines += ["", "## Who holds each role", ""]
    for role in ROLE_ORDER:
        holders = [f"`{a.id}`" + ("" if a.status == "active" else f" ({a.status})")
                   for a in sorted(cfg.agents, key=lambda x: x.id)
                   if role in a.roles and a.status != "inactive"]
        lines.append(f"- **{role}:** {', '.join(holders) if holders else '—'}")

    lines += ["", "## Areas", "", "| Area | Paths | Owner |", "|---|---|---|"]
    for area in cfg.areas:
        paths = ", ".join(f"`{p}`" for p in area.paths)
        lines.append(f"| {area.name} | {paths} | {('`' + area.owner + '`') if area.owner else '—'} |")

    lines += [
        "",
        "## Reviewer pairing",
        "",
        "An approval counts only from an active agent with a reviewing role in a **different family** than the author.",
        "",
        "| Author family | Eligible reviewers |",
        "|---|---|",
    ]
    reviewers = [a for a in cfg.agents if a.status == "active" and a.has_role(*cfg.s("reviewing_roles"))]
    families = sorted({a.family for a in cfg.agents if a.status != "inactive" and a.has_role(*cfg.s("authoring_roles"))})
    for fam in families:
        elig = [f"`{r.id}`" for r in reviewers if r.family != fam]
        lines.append(f"| {fam} | {', '.join(elig) if elig else '**none — fix the roster**'} |")
    return "\n".join(lines) + "\n"
