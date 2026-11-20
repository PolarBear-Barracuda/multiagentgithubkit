"""Load and query .github/agents.yml."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

VALID_ROLES = {"orchestrator", "steward", "implementer", "reviewer", "qa", "maintainer"}
VALID_STATUSES = {"active", "probation", "inactive"}
RISK_RANK = {"risk:low": 1, "risk:med": 2, "risk:high": 3}

DEFAULT_SETTINGS = {
    "max_diff_lines": 400,
    "diff_size_exclude": [],
    "wip_limit_per_agent": 2,
    "claim_draft_pr_hours": 4,
    "claim_idle_hours": 24,
    "require_approval_on_head": True,
    "high_risk_requires_agent_review": True,
    "authoring_roles": ["implementer", "qa", "maintainer", "steward"],
    "reviewing_roles": ["reviewer", "steward"],
    "pr_required_sections": [
        "Linked issue",
        "Scope",
        "How I verified",
        "Risk",
        "What I'm unsure about",
    ],
    "scope_always_allowed": [],
}

LABEL_DECISION = "needs-human-decision"
LABEL_TEST_OVERRIDE = "test-change-approved"
LABEL_LARGE_DIFF = "large-diff-approved"


def normalize_login(login: str | None) -> str:
    """Make App and user logins comparable across gh CLI and REST formats."""
    s = (login or "").strip().lower()
    if s.startswith("app/"):
        s = s[4:]
    if s.endswith("[bot]"):
        s = s[: -len("[bot]")]
    return s


@dataclass
class Agent:
    id: str
    github: str
    family: str
    roles: list[str]
    status: str
    raw: dict = field(default_factory=dict)

    @property
    def login(self) -> str:
        return normalize_login(self.github)

    def has_role(self, *roles: str) -> bool:
        return any(r in self.roles for r in roles)


@dataclass
class Area:
    name: str
    paths: list[str]
    owner: str | None


class Config:
    def __init__(self, data: dict, pointer_files: list[str] | None = None):
        self.data = data or {}
        self.settings = {**DEFAULT_SETTINGS, **(self.data.get("settings") or {})}
        self.owners = [normalize_login(o.get("github")) for o in self.data.get("owners") or [] if isinstance(o, dict)]
        self.agents = [
            Agent(
                id=str(a.get("id", "")),
                github=str(a.get("github", "")),
                family=str(a.get("family", "")),
                roles=list(a.get("roles") or []),
                status=str(a.get("status", "")),
                raw=a,
            )
            for a in self.data.get("agents") or []
            if isinstance(a, dict)
        ]
        self.areas = [
            Area(name=str(a.get("name", "")), paths=list(a.get("paths") or []), owner=a.get("owner"))
            for a in self.data.get("areas") or []
            if isinstance(a, dict)
        ]
        prot = self.data.get("protected_paths") or {}
        self.no_touch = list(prot.get("no_touch") or [])
        self.add_only = list(prot.get("add_only") or [])
        self.pointer_files = list(pointer_files or [])
        for pf in self.pointer_files:
            anchored = "/" + pf.lstrip("/")
            if anchored not in self.no_touch:
                self.no_touch.append(anchored)
        self.test_patterns = list(self.data.get("test_patterns") or [])

    # ---- lookups -------------------------------------------------------
    def is_owner(self, login: str | None) -> bool:
        return normalize_login(login) in self.owners

    def agent_by_login(self, login: str | None) -> Agent | None:
        n = normalize_login(login)
        for a in self.agents:
            if a.login == n:
                return a
        return None

    def agent_by_id(self, agent_id: str | None) -> Agent | None:
        for a in self.agents:
            if a.id == agent_id:
                return a
        return None

    def can_assign(self, login: str | None) -> bool:
        """Owners and active orchestrators may write issue scope and assign work."""
        if self.is_owner(login):
            return True
        a = self.agent_by_login(login)
        return bool(a and a.status == "active" and a.has_role("orchestrator"))

    def s(self, key: str):
        return self.settings.get(key, DEFAULT_SETTINGS.get(key))


def read_pointer_files(path: str | None) -> list[str]:
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def load_config(path: str, pointer_file_list: str | None = None) -> Config:
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if pointer_file_list is None:
        guess = os.path.join(os.path.dirname(path), "agent-pointer-files.txt")
        pointer_file_list = guess if os.path.exists(guess) else None
    return Config(data, read_pointer_files(pointer_file_list))


def risk_labels(labels) -> list[str]:
    return [l for l in labels if l in RISK_RANK]
