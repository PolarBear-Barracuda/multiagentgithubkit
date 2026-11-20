import copy
import os

import roster
import validate
from config import Config, load_config
from conftest import BASE_CONFIG

KIT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def errs(cfg_dict, **kw):
    return validate.run(Config(cfg_dict), **kw).errors


def test_base_config_valid():
    assert errs(BASE_CONFIG) == []


def test_shipped_config_has_no_structural_errors():
    # The only acceptable error is an unfilled owner placeholder in the untouched template.
    cfg = load_config(os.path.join(KIT_ROOT, ".github", "agents.yml"))
    e = validate.run(cfg).errors
    assert all("placeholder" in x for x in e), e


def test_shipped_roster_in_sync():
    cfg = load_config(os.path.join(KIT_ROOT, ".github", "agents.yml"))
    with open(os.path.join(KIT_ROOT, "docs", "agents", "roster.md"), encoding="utf-8") as fh:
        assert fh.read() == roster.render(cfg)


def test_duplicate_login_and_owner_login():
    c = copy.deepcopy(BASE_CONFIG)
    c["agents"][1]["github"] = "steward-a[bot]"
    c["agents"][2]["github"] = "the-owner"
    e = errs(c)
    assert any("used by another agent" in x for x in e)
    assert any("owner's login" in x for x in e)


def test_family_without_cross_family_reviewer():
    c = copy.deepcopy(BASE_CONFIG)
    c["agents"] = [
        {"id": "a", "github": "a[bot]", "family": "f1", "roles": ["implementer", "reviewer"], "status": "active"},
        {"id": "b", "github": "b[bot]", "family": "f1", "roles": ["reviewer"], "status": "active"},
    ]
    c["areas"] = []
    assert any("outside family 'f1'" in x for x in errs(c))


def test_bad_role_status_and_area_owner():
    c = copy.deepcopy(BASE_CONFIG)
    c["agents"][0]["roles"] = ["boss"]
    c["agents"][1]["status"] = "sleeping"
    c["areas"][0]["owner"] = "ghost"
    e = errs(c)
    assert any("unknown roles" in x for x in e)
    assert any("status must be" in x for x in e)
    assert any("ghost" in x for x in e)


def test_protected_paths_required():
    c = copy.deepcopy(BASE_CONFIG)
    c["protected_paths"]["no_touch"] = ["/docs/**"]
    assert any("/AGENTS.md" in x for x in errs(c))


def test_roster_drift_detected():
    cfg = Config(BASE_CONFIG)
    e = validate.run(cfg, roster_md="old", rendered_roster=roster.render(cfg)).errors
    assert any("out of date" in x for x in e)
