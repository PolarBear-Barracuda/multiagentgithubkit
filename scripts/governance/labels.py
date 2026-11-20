"""Sync labels from .github/labels.yml plus agent:<id> labels generated from agents.yml."""
from __future__ import annotations

import subprocess

import yaml

from config import Config
from report import Report


def desired_labels(cfg: Config, labels_path: str) -> list[dict]:
    with open(labels_path, encoding="utf-8") as fh:
        base = yaml.safe_load(fh) or []
    out = [dict(l) for l in base]
    names = {l["name"] for l in out}
    for a in cfg.agents:
        name = f"agent:{a.id}"
        if name not in names:
            out.append({"name": name, "color": "bfdadc", "description": f"Assigned to agent {a.id} ({a.status})"})
    return out


def run(cfg: Config, labels_path: str, repo: str | None, dry_run: bool) -> Report:
    r = Report("sync-labels")
    for l in desired_labels(cfg, labels_path):
        args = ["gh", "label", "create", l["name"], "--color", str(l.get("color", "ededed")),
                "--description", l.get("description", "")[:100], "--force"]
        if repo:
            args += ["--repo", repo]
        if dry_run:
            r.note("would run: " + " ".join(args[:4]))
            continue
        res = subprocess.run(args, capture_output=True, text=True)
        if res.returncode != 0:
            r.error(f"{l['name']}: {res.stderr.strip()}")
        else:
            r.note(f"synced {l['name']}")
    return r
