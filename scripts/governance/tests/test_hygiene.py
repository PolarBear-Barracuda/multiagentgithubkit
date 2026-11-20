import hygiene
from conftest import GOOD_BODY, ev_label


def errors(ctx):
    return hygiene.run(ctx).errors


def test_good_pr_passes(make_ctx):
    assert errors(make_ctx()) == []


def test_owner_is_exempt(make_ctx):
    assert errors(make_ctx(author="the-owner", branch="whatever", body="")) == []


def test_unknown_author(make_ctx):
    assert any("not listed" in e for e in errors(make_ctx(author="stranger")))


def test_reviewer_only_agent_cannot_author(make_ctx):
    errs = errors(make_ctx(author="rev-d[bot]", branch="agent/rev-d/12-x", issue_labels=("agent:rev-d", "status:claimed")))
    assert any("authoring" in e for e in errs)


def test_missing_and_multiple_links(make_ctx):
    assert any("exactly one issue" in e for e in errors(make_ctx(body=GOOD_BODY.replace("Closes #12", "#12"))))
    assert any("several issues" in e for e in errors(make_ctx(body=GOOD_BODY.replace("Closes #12", "Closes #12 closes #13"))))


def test_branch_rules(make_ctx):
    assert any("must match" in e for e in errors(make_ctx(branch="feature/limit")))
    assert any("doesn't match the author" in e for e in errors(make_ctx(branch="agent/impl-c/12-limit")))
    assert any("linked issue #12" in e for e in errors(make_ctx(branch="agent/impl-b/13-limit")))


def test_issue_must_be_assigned_to_author(make_ctx):
    assert any("not assigned to you" in e for e in errors(make_ctx(issue_labels=("agent:impl-c", "status:claimed"))))


def test_risk_label_rules(make_ctx):
    assert any("exactly one risk label" in e for e in errors(make_ctx(labels=())))
    assert any("exactly one risk label" in e for e in errors(make_ctx(labels=("risk:low", "risk:med"))))
    body = __import__("conftest").ISSUE_BODY.replace("risk:low", "risk:high")
    assert any("lower than the linked issue" in e for e in errors(make_ctx(issue_body=body)))


def test_probation_agent_low_risk_only(make_ctx):
    ctx = make_ctx(author="newbie[bot]", branch="agent/newbie/12-x", labels=("risk:med",),
                   issue_labels=("agent:newbie", "status:claimed"))
    assert any("probation" in e for e in errors(ctx))


def test_empty_section(make_ctx):
    body = GOOD_BODY.replace("Nothing major.", "<!-- fill me -->")
    assert any("What I'm unsure about" in e and "empty" in e for e in errors(make_ctx(body=body)))


def test_diff_size_limit_and_owner_override(make_ctx):
    big = [("M", "src/api/items.py", [f"line {i}" for i in range(60)], [])]
    assert any("changed lines" in e for e in errors(make_ctx(files=big)))
    ok = make_ctx(files=big, labels=("risk:low", "large-diff-approved"),
                  pr_events=[ev_label("large-diff-approved", "the-owner")])
    assert errors(ok) == []
    bad = make_ctx(files=big, labels=("risk:low", "large-diff-approved"),
                   pr_events=[ev_label("large-diff-approved", "impl-b[bot]")])
    assert any("changed lines" in e for e in errors(bad))


def test_lockfiles_excluded_from_size(make_ctx):
    cfg = __import__("copy").deepcopy(__import__("conftest").BASE_CONFIG)
    cfg["settings"]["diff_size_exclude"] = ["**/*.lock"]
    files = [("M", "src/api/items.py", ["x"], []), ("M", "poetry.lock", [f"l{i}" for i in range(500)], [])]
    assert errors(make_ctx(files=files, config=cfg)) == []


def test_wip_limit(make_ctx):
    prs = [{"number": n, "author": {"login": "app/impl-b"}} for n in (1, 2, 99)]
    assert any("open PRs" in e for e in errors(make_ctx(open_prs=prs)))


def test_self_assignment_rejected(make_ctx):
    errs = errors(make_ctx(issue_events=[ev_label("agent:impl-b", "impl-b[bot]")]))
    assert any("only owners and active orchestrators assign" in e for e in errs)


def test_assignment_by_owner_ok(make_ctx):
    assert errors(make_ctx(issue_events=[ev_label("agent:impl-b", "the-owner")])) == []
