"""ruleset-audit: alert if the live branch ruleset is missing or weaker than the saved copy.

Compares the live ruleset (by name) with .github/rulesets/<name>.json. Anything weaker —
ruleset deleted or disabled, a rule removed, a required check dropped, a review requirement
turned off, an extra bypass actor — is a finding. Stricter live settings are fine.
"""
from __future__ import annotations

import json
import subprocess

from report import Report

ALERT_TITLE = "Governance alert: branch protection changed"


def _params(rule: dict) -> dict:
    return rule.get("parameters") or {}


def compare(expected: dict, actual: dict | None) -> tuple[list[str], list[str]]:
    """Return (problems, notes)."""
    problems: list[str] = []
    notes: list[str] = []
    name = expected.get("name")
    if actual is None:
        return [f"Ruleset '{name}' no longer exists."], notes
    if actual.get("enforcement") != "active":
        problems.append(f"Ruleset enforcement is '{actual.get('enforcement')}', expected 'active'.")

    exp_refs = set(((expected.get("conditions") or {}).get("ref_name") or {}).get("include") or [])
    act_refs = set(((actual.get("conditions") or {}).get("ref_name") or {}).get("include") or [])
    if not exp_refs <= act_refs:
        problems.append(f"Ruleset no longer targets {sorted(exp_refs - act_refs)}.")

    if "bypass_actors" in actual:
        allowed = {(b.get("actor_type"), b.get("actor_id"), b.get("bypass_mode")) for b in expected.get("bypass_actors") or []}
        for b in actual.get("bypass_actors") or []:
            key = (b.get("actor_type"), b.get("actor_id"), b.get("bypass_mode"))
            if key not in allowed:
                problems.append(f"Unexpected bypass actor: {b.get('actor_type')} {b.get('actor_id')} ({b.get('bypass_mode')}).")
    else:
        notes.append("Bypass list isn't visible to this token; not checked.")

    act_rules = {r.get("type"): r for r in actual.get("rules") or []}
    for rule in expected.get("rules") or []:
        rtype = rule.get("type")
        live = act_rules.get(rtype)
        if live is None:
            problems.append(f"Rule '{rtype}' was removed.")
            continue
        ep, lp = _params(rule), _params(live)
        if rtype == "required_status_checks":
            exp_ctx = {c.get("context") for c in ep.get("required_status_checks") or []}
            act_ctx = {c.get("context") for c in lp.get("required_status_checks") or []}
            missing = sorted(exp_ctx - act_ctx)
            if missing:
                problems.append(f"Required checks removed: {', '.join(missing)}.")
            if ep.get("strict_required_status_checks_policy") and not lp.get("strict_required_status_checks_policy"):
                problems.append("'Require branches to be up to date' was turned off.")
            continue
        for key, val in ep.items():
            have = lp.get(key)
            if isinstance(val, bool):
                if val and not have:
                    problems.append(f"{rtype}.{key} was turned off.")
            elif isinstance(val, int):
                if not isinstance(have, int) or have < val:
                    problems.append(f"{rtype}.{key} lowered from {val} to {have}.")
            elif isinstance(val, list):
                if have is not None and not set(have) <= set(val):
                    problems.append(f"{rtype}.{key} widened to {have} (expected subset of {val}).")
    return problems, notes


def _gh(args: list[str]) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def fetch_live(repo: str, name: str) -> dict | None:
    rulesets = json.loads(_gh(["api", f"repos/{repo}/rulesets"]))
    for rs in rulesets:
        if rs.get("name") == name:
            return json.loads(_gh(["api", f"repos/{repo}/rulesets/{rs['id']}"]))
    return None


def run(repo: str, expected_path: str, open_issue: bool = False) -> Report:
    r = Report("ruleset-audit")
    with open(expected_path, encoding="utf-8") as fh:
        expected = json.load(fh)
    problems, notes = compare(expected, fetch_live(repo, expected["name"]))
    for n in notes:
        r.note(n)
    for p in problems:
        r.error(p)
    if problems and open_issue:
        existing = json.loads(_gh(["issue", "list", "--repo", repo, "--state", "open", "--search",
                                   f'in:title "{ALERT_TITLE}"', "--json", "number"]))
        body = ("The live branch ruleset no longer matches `" + expected_path + "`:\n\n"
                + "\n".join(f"- {p}" for p in problems)
                + "\n\nCheck **Settings → Rules → Rulesets**. If the change was intended, update the saved "
                  "JSON through a PR; otherwise restore the ruleset (scripts/setup/bootstrap.sh can re-apply it).")
        if existing:
            _gh(["issue", "comment", str(existing[0]["number"]), "--repo", repo, "--body", body])
        else:
            _gh(["issue", "create", "--repo", repo, "--title", ALERT_TITLE, "--body", body,
                 "--label", "needs-human-decision"])
    if not problems:
        r.note(f"Ruleset '{expected['name']}' matches the saved copy (or is stricter).")
    return r
