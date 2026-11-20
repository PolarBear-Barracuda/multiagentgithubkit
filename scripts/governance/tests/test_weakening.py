import weakening
from conftest import ev_label


def run(ctx):
    return weakening.run(ctx)


def test_clean(make_ctx):
    files = [("M", "tests/test_items.py", ["    assert f(0) == 400", "    assert f(1) == 200"], [])]
    assert run(make_ctx(files=files)).ok


def test_deleted_test_file(make_ctx):
    r = run(make_ctx(files=[("D", "tests/test_items.py", [], ["assert x"])]))
    assert not r.ok and any("deleted" in e for e in r.errors)


def test_removed_assertions(make_ctx):
    files = [("M", "tests/test_items.py", ["    pass"], ["    assert f(0) == 400", "    assert g() is None"])]
    r = run(make_ctx(files=files))
    assert any("assertion" in e for e in r.errors)


def test_replaced_assertion_is_fine(make_ctx):
    files = [("M", "tests/test_items.py", ["    assert f(0) == 422"], ["    assert f(0) == 400"])]
    assert run(make_ctx(files=files)).ok


def test_skip_markers(make_ctx):
    for line, path in [
        ("@pytest.mark.skip(reason='flaky')", "tests/test_a.py"),
        ("  it.skip('works', () => {})", "src/a.test.ts"),
        ("  xit('works', () => {})", "src/a.test.js"),
        ("\tt.Skip(\"later\")", "pkg/a_test.go"),
    ]:
        r = run(make_ctx(files=[("M", path, [line], [])]))
        assert any("skip" in e for e in r.errors), line


def test_skip_in_comment_ignored(make_ctx):
    assert run(make_ctx(files=[("M", "tests/test_a.py", ["# @pytest.mark.skip was removed"], [])])).ok


def test_focus_marker_never_overridable(make_ctx):
    r = run(make_ctx(files=[("M", "src/a.test.ts", ["  it.only('x', () => {})"], [])],
                     labels=("risk:low", "test-change-approved"),
                     pr_events=[ev_label("test-change-approved", "the-owner")]))
    assert any("focus" in e for e in r.errors)


def test_coverage_threshold(make_ctx):
    r = run(make_ctx(files=[("M", "pyproject.toml", ["fail_under = 50"], ["fail_under = 80"])]))
    assert any("coverage" in e for e in r.errors)


def test_owner_override_label(make_ctx):
    files = [("D", "tests/test_items.py", [], ["assert x"])]
    ok = run(make_ctx(files=files, labels=("risk:low", "test-change-approved"),
                      pr_events=[ev_label("test-change-approved", "the-owner")]))
    assert ok.ok
    bad = run(make_ctx(files=files, labels=("risk:low", "test-change-approved"),
                       pr_events=[ev_label("test-change-approved", "impl-b[bot]")]))
    assert not bad.ok


def test_label_reapplied_by_agent_after_owner_does_not_count(make_ctx):
    files = [("D", "tests/test_items.py", [], ["assert x"])]
    events = [ev_label("test-change-approved", "the-owner", "2026-01-01T00:00:00Z"),
              ev_label("test-change-approved", "impl-b[bot]", "2026-01-03T00:00:00Z", "unlabeled"),
              ev_label("test-change-approved", "impl-b[bot]", "2026-01-03T00:00:01Z")]
    assert not run(make_ctx(files=files, labels=("risk:low", "test-change-approved"), pr_events=events)).ok


def test_assertion_forms_recognized(make_ctx):
    # replacing an assert with pytest.raises / expect().rejects / REQUIRE is not weakening
    for path, new, old in [
        ("tests/test_a.py", "    with pytest.raises(ValueError):", "    assert f(0) == []"),
        ("src/a.test.ts", "  await expect(p).rejects.toThrow()", "  expect(x).toBe(1)"),
        ("tests/a_test.cpp", "  REQUIRE(x == 1);", "  assert(x == 1);"),
    ]:
        assert run(make_ctx(files=[("M", path, [new], [old])])).ok, path
