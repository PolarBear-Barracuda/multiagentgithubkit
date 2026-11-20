#!/usr/bin/env python3
"""Governance checks for the multi-agent operating model. See AGENTS.md.

Usage (CI runs these; you can run them locally against a context directory):
  gov.py hygiene     --context DIR
  gov.py scope       --context DIR
  gov.py protected   --context DIR
  gov.py weakening   --context DIR
  gov.py riskgate    --context DIR
  gov.py linked-issue --context DIR            # prints the linked issue number, if exactly one
  gov.py validate-config --config .github/agents.yml [--roster docs/agents/roster.md]
  gov.py render-roster   --config .github/agents.yml
  gov.py stale-claims    --config .github/agents.yml --repo OWNER/REPO [--dry-run]
  gov.py sync-labels     --config .github/agents.yml --labels .github/labels.yml [--repo OWNER/REPO] [--dry-run]
  gov.py eval-score      --results evals/results --seeds evals/review-seeds [--config .github/agents.yml]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.dont_write_bytecode = True  # never write caches into a checked-out repo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config  # noqa: E402
from context import Context, linked_issues  # noqa: E402

PR_CHECKS = {
    "hygiene": "hygiene",
    "scope": "scope",
    "protected": "protected",
    "weakening": "weakening",
    "riskgate": "riskgate",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Multi-agent governance checks")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in list(PR_CHECKS) + ["linked-issue"]:
        p = sub.add_parser(name)
        p.add_argument("--context", required=True, help="context directory from collect_context.sh")
        p.add_argument("--config", help="override path to agents.yml")

    p = sub.add_parser("validate-config")
    p.add_argument("--config", required=True)
    p.add_argument("--roster", help="path to docs/agents/roster.md to check for drift")
    p.add_argument("--pointer-files", help="path to agent-pointer-files.txt")

    p = sub.add_parser("render-roster")
    p.add_argument("--config", required=True)

    p = sub.add_parser("stale-claims")
    p.add_argument("--config", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("sync-labels")
    p.add_argument("--config", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--repo")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("eval-score")
    p.add_argument("--results", required=True)
    p.add_argument("--seeds", required=True)
    p.add_argument("--config")

    a = ap.parse_args(argv)

    if a.cmd in PR_CHECKS or a.cmd == "linked-issue":
        cfg = load_config(a.config) if a.config else None
        ctx = Context(a.context, cfg)
        if a.cmd == "linked-issue":
            issues = linked_issues(ctx.body)
            if len(issues) == 1:
                print(issues[0])
            return 0
        module = __import__(PR_CHECKS[a.cmd])
        return module.run(ctx).emit()

    if a.cmd == "validate-config":
        import roster
        import validate
        cfg = load_config(a.config, a.pointer_files)
        roster_md = None
        if a.roster:
            roster_md = open(a.roster, encoding="utf-8").read() if os.path.exists(a.roster) else ""
        return validate.run(cfg, roster_md, roster.render(cfg) if a.roster else None).emit()

    if a.cmd == "render-roster":
        import roster
        sys.stdout.write(roster.render(load_config(a.config)))
        return 0

    if a.cmd == "stale-claims":
        import claims
        return claims.run(a.repo, load_config(a.config), dry_run=a.dry_run).emit()

    if a.cmd == "sync-labels":
        import labels
        return labels.run(load_config(a.config), a.labels, a.repo, a.dry_run).emit()

    if a.cmd == "eval-score":
        import evalscore
        fams = {}
        if a.config:
            fams = {ag.id: ag.family for ag in load_config(a.config).agents}
        sys.stdout.write(evalscore.render(evalscore.score(a.results, a.seeds), fams))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
