import copy
import json
import os

from rulesetaudit import compare

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXPECTED = json.load(open(os.path.join(ROOT, ".github", "rulesets", "main-protection.json")))


def live():
    return copy.deepcopy(EXPECTED)


def test_identical_ok():
    assert compare(EXPECTED, live()) == ([], [])


def test_missing_or_disabled():
    assert "no longer exists" in compare(EXPECTED, None)[0][0]
    a = live(); a["enforcement"] = "disabled"
    assert compare(EXPECTED, a)[0]


def test_removed_rule_and_check():
    a = live()
    a["rules"] = [r for r in a["rules"] if r["type"] != "non_fast_forward"]
    for r in a["rules"]:
        if r["type"] == "required_status_checks":
            r["parameters"]["required_status_checks"] = [c for c in r["parameters"]["required_status_checks"] if c["context"] != "risk-gate"]
    probs = compare(EXPECTED, a)[0]
    assert any("non_fast_forward" in p for p in probs)
    assert any("risk-gate" in p for p in probs)


def test_weakened_review_and_extra_bypass():
    a = live()
    for r in a["rules"]:
        if r["type"] == "pull_request":
            r["parameters"]["require_code_owner_review"] = False
            r["parameters"]["allowed_merge_methods"] = ["squash", "merge"]
    a["bypass_actors"].append({"actor_type": "Integration", "actor_id": 123, "bypass_mode": "always"})
    probs = compare(EXPECTED, a)[0]
    assert any("require_code_owner_review" in p for p in probs)
    assert any("widened" in p for p in probs)
    assert any("Integration 123" in p for p in probs)


def test_stricter_is_fine_and_hidden_bypass_noted():
    a = live()
    for r in a["rules"]:
        if r["type"] == "pull_request":
            r["parameters"]["required_approving_review_count"] = 2
    del a["bypass_actors"]
    probs, notes = compare(EXPECTED, a)
    assert probs == [] and notes
