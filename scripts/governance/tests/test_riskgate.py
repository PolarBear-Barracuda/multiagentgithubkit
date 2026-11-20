import riskgate
from conftest import OLD, ev_label, review


def errors(ctx):
    return riskgate.run(ctx).errors


def test_low_with_cross_family_approval(make_ctx):
    assert errors(make_ctx(reviews=[review("impl-c[bot]", "APPROVED")])) == []


def test_low_without_approval(make_ctx):
    assert any("valid reviewer approval" in e for e in errors(make_ctx()))


def test_same_family_approval_ignored(make_ctx):
    # rev-d is fam-2 like the author impl-b
    assert errors(make_ctx(reviews=[review("rev-d[bot]", "APPROVED")]))


def test_probation_and_unknown_reviewers_ignored(make_ctx):
    assert errors(make_ctx(reviews=[review("newbie[bot]", "APPROVED")]))
    assert errors(make_ctx(reviews=[review("random-person", "APPROVED")]))


def test_approval_on_old_commit_ignored(make_ctx):
    assert errors(make_ctx(reviews=[review("impl-c[bot]", "APPROVED", commit=OLD)]))


def test_changes_requested_blocks_even_with_other_approval(make_ctx):
    rv = [review("impl-c[bot]", "APPROVED"), review("steward-a[bot]", "CHANGES_REQUESTED")]
    assert any("requested changes" in e for e in errors(make_ctx(reviews=rv)))


def test_later_approval_clears_changes_requested(make_ctx):
    rv = [review("impl-c[bot]", "CHANGES_REQUESTED", t="2026-01-01T00:00:00Z"),
          review("impl-c[bot]", "COMMENTED", t="2026-01-01T12:00:00Z"),
          review("impl-c[bot]", "APPROVED", t="2026-01-02T00:00:00Z")]
    assert errors(make_ctx(reviews=rv)) == []


def test_decision_label_blocks(make_ctx):
    ctx = make_ctx(labels=("risk:low", "needs-human-decision"), reviews=[review("impl-c[bot]", "APPROVED")])
    assert any("needs-human-decision" in e for e in errors(ctx))


def test_med_needs_area_owner_or_steward(make_ctx):
    only_reviewer = make_ctx(labels=("risk:med",), reviews=[review("impl-c[bot]", "APPROVED")])
    assert any("area 'api'" in e for e in errors(only_reviewer))
    with_steward = make_ctx(labels=("risk:med",), reviews=[review("impl-c[bot]", "APPROVED"),
                                                           review("steward-a[bot]", "APPROVED")])
    assert errors(with_steward) == []
    with_owner = make_ctx(labels=("risk:med",), reviews=[review("the-owner", "APPROVED")])
    assert errors(with_owner) == []


def test_med_outside_areas_needs_steward(make_ctx):
    ctx = make_ctx(labels=("risk:med",), files=[("M", "lib/x.py", ["a"], [])],
                   reviews=[review("impl-c[bot]", "APPROVED")])
    assert any("steward" in e for e in errors(ctx))


def test_high_needs_owner_and_agent_review(make_ctx):
    agent_only = make_ctx(labels=("risk:high",), reviews=[review("impl-c[bot]", "APPROVED")])
    assert any("owner" in e for e in errors(agent_only))
    owner_only = make_ctx(labels=("risk:high",), reviews=[review("the-owner", "APPROVED")])
    assert any("agent reviewer" in e for e in errors(owner_only))
    both = make_ctx(labels=("risk:high",), reviews=[review("the-owner", "APPROVED"), review("impl-c[bot]", "APPROVED")])
    assert errors(both) == []


def test_risk_downgrade(make_ctx):
    events = [ev_label("risk:high", "steward-a[bot]", "2026-01-01T00:00:00Z"),
              ev_label("risk:high", "impl-b[bot]", "2026-01-01T01:00:00Z", "unlabeled"),
              ev_label("risk:low", "impl-b[bot]", "2026-01-01T01:00:01Z")]
    ctx = make_ctx(pr_events=events, reviews=[review("impl-c[bot]", "APPROVED")])
    assert any("lowered" in e for e in errors(ctx))
    events[-1] = ev_label("risk:low", "the-owner", "2026-01-01T01:00:01Z")
    ctx = make_ctx(pr_events=events, reviews=[review("impl-c[bot]", "APPROVED")])
    assert errors(ctx) == []


def test_self_approval_ignored(make_ctx):
    assert errors(make_ctx(reviews=[review("impl-b[bot]", "APPROVED")]))


def test_gh_cli_app_login_format(make_ctx):
    ctx = make_ctx(author="app/impl-b", reviews=[review("impl-c[bot]", "APPROVED")])
    assert errors(ctx) == []
