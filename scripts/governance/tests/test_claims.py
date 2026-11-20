from datetime import datetime, timedelta, timezone

from claims import decide

NOW = datetime(2026, 1, 10, 12, tzinfo=timezone.utc)


def d(**kw):
    base = dict(now=NOW, claimed_at=NOW - timedelta(hours=1), pr_last_commit=None, has_pr=False,
                blocked=False, already_warned=False, draft_hours=4, idle_hours=24)
    base.update(kw)
    return decide(**base).action


def test_fresh_claim():
    assert d() == "none"


def test_warn_once_without_pr():
    assert d(claimed_at=NOW - timedelta(hours=5)) == "warn"
    assert d(claimed_at=NOW - timedelta(hours=5), already_warned=True) == "none"


def test_release_without_pr():
    assert d(claimed_at=NOW - timedelta(hours=25)) == "release"


def test_active_pr_keeps_claim():
    assert d(claimed_at=NOW - timedelta(hours=40), has_pr=True, pr_last_commit=NOW - timedelta(hours=2)) == "none"


def test_idle_pr_released():
    assert d(claimed_at=NOW - timedelta(hours=40), has_pr=True, pr_last_commit=NOW - timedelta(hours=30)) == "release"


def test_reclaim_resets_clock_even_with_old_commits():
    assert d(claimed_at=NOW - timedelta(hours=1), has_pr=True, pr_last_commit=NOW - timedelta(hours=30)) == "none"


def test_blocked_is_left_alone():
    assert d(claimed_at=NOW - timedelta(hours=100), blocked=True) == "none"
