"""Score capability evals and rank agents per role.

Reads evals/results/*.yml (files starting with "_" are ignored) and the answer keys in
evals/review-seeds/<seed>/answer-key.yml. Prints markdown for docs/agents/capability-matrix.md.
"""
from __future__ import annotations

import glob
import os
import yaml

ROLE_METRIC = {
    "orchestrator": "planning",
    "steward": "design",
    "implementer": "implement",
    "reviewer": "review_f05",
    "qa": "tests",
    "maintainer": "implement",
}


def load_answer_keys(seeds_dir: str) -> dict[str, int]:
    keys = {}
    for path in glob.glob(os.path.join(seeds_dir, "*", "answer-key.yml")):
        seed = os.path.basename(os.path.dirname(path))
        if seed.startswith("_"):
            continue
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        keys[str(data.get("seed", seed))] = len(data.get("bugs") or [])
    return keys


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def score(results_dir: str, seeds_dir: str) -> dict[str, dict]:
    keys = load_answer_keys(seeds_dir)
    files = sorted(f for f in glob.glob(os.path.join(results_dir, "*.yml")) if not os.path.basename(f).startswith("_"))
    latest: dict[str, tuple[str, dict]] = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        agent = str(data.get("agent", ""))
        date = str(data.get("date", ""))
        if agent and (agent not in latest or date >= latest[agent][0]):
            latest[agent] = (date, data)

    scores: dict[str, dict] = {}
    for agent, (date, d) in latest.items():
        s: dict = {"date": date, "model_version": d.get("model_version", ""), "n": 0, "warnings": []}

        impl = d.get("implement") or []
        if impl:
            per = [0.5 * bool(t.get("accepted")) + 0.3 * bool(t.get("ci_pass_first_push")) + 0.2 * bool(t.get("in_scope", True))
                   for t in impl]
            s["implement"] = _mean(per)
            s["n"] += len(impl)

        rev = d.get("review") or []
        if rev:
            found = fp = total = 0
            for t in rev:
                seed = str(t.get("seed"))
                if seed not in keys:
                    s["warnings"].append(f"review seed '{seed}' has no answer key")
                    continue
                f_ = len(t.get("found") or [])
                found += f_
                fp += int(t.get("false_positives") or 0)
                total += keys[seed]
            precision = found / (found + fp) if (found + fp) else (1.0 if total == 0 else None)
            recall = found / total if total else None
            s["review_precision"], s["review_recall"] = precision, recall
            if precision is not None and recall is not None and (precision + recall) > 0:
                b2 = 0.25  # beta = 0.5: precision weighted twice as much as recall
                s["review_f05"] = (1 + b2) * precision * recall / (b2 * precision + recall)
            elif precision is not None and recall is not None:
                s["review_f05"] = 0.0
            s["n"] += len(rev)

        plan = d.get("planning") or []
        if plan:
            per = []
            for t in plan:
                rubric = _mean([t.get("decomposition"), t.get("criteria_testable")])
                rubric = (rubric - 1) / 4 if rubric is not None else 0
                per.append(0.7 * rubric + 0.3 * bool(t.get("escalated_correctly")))
            s["planning"] = _mean(per)
            s["n"] += len(plan)

        des = d.get("design") or []
        if des:
            s["design"] = _mean([(t.get("quality", 1) - 1) / 4 for t in des])
            s["n"] += len(des)

        tests = d.get("tests") or []
        if tests:
            killed = sum(int(t.get("mutants_killed") or 0) for t in tests)
            total = sum(int(t.get("mutants_total") or 0) for t in tests)
            s["tests"] = killed / total if total else None
            s["n"] += len(tests)
        scores[agent] = s
    return scores


def _fmt(v):
    return "–" if v is None else f"{v:.2f}"


def render(scores: dict[str, dict], families: dict[str, str] | None = None) -> str:
    families = families or {}
    out = ["## Scores (latest round)", "",
           "| Agent | Family | Implement | Review precision | Review recall | Planning | Design | Tests | Evals |",
           "|---|---|---|---|---|---|---|---|---|"]
    for agent in sorted(scores):
        s = scores[agent]
        out.append(f"| {agent} | {families.get(agent, '–')} | {_fmt(s.get('implement'))} | {_fmt(s.get('review_precision'))} | "
                   f"{_fmt(s.get('review_recall'))} | {_fmt(s.get('planning'))} | {_fmt(s.get('design'))} | "
                   f"{_fmt(s.get('tests'))} | {s['n']} |")
    out += ["", "## Role rankings (latest round)", ""]
    for role, metric in ROLE_METRIC.items():
        ranked = sorted(((s.get(metric), a) for a, s in scores.items() if s.get(metric) is not None), reverse=True)
        txt = ", ".join(f"{a} ({v:.2f})" for v, a in ranked) or "–"
        out.append(f"- **{role.capitalize()}** ({metric}): {txt}")
    warns = [f"{a}: {w}" for a, s in scores.items() for w in s["warnings"]]
    if warns:
        out += ["", "**Warnings:**"] + [f"- {w}" for w in warns]
    out += ["", "_Reviewer ranking uses F0.5 (precision counts twice as much as recall). "
            "Cost and availability are tie-breakers only._"]
    return "\n".join(out) + "\n"
