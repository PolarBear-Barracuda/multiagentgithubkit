import scope
from conftest import ISSUE_BODY


def errors(ctx):
    return scope.run(ctx).errors


def test_in_scope_passes(make_ctx):
    files = [("M", "src/api/items.py", ["a"], []), ("A", "tests/api/test_items.py", ["b"], [])]
    assert errors(make_ctx(files=files)) == []


def test_outside_scope_fails(make_ctx):
    files = [("M", "src/core/model.py", ["a"], [])]
    assert any("outside" in e for e in errors(make_ctx(files=files)))


def test_out_of_scope_list_wins(make_ctx):
    body = ISSUE_BODY.replace("src/api/items.py", "src/api/")
    files = [("M", "src/api/auth/login.py", ["a"], [])]
    assert any("Out of scope" in e for e in errors(make_ctx(files=files, issue_body=body)))


def test_rename_touches_old_path(make_ctx):
    files = [("R", "src/api/items.py", [], [], "src/core/items.py")]
    assert any("src/core/items.py" in e for e in errors(make_ctx(files=files)))


def test_no_machine_readable_scope(make_ctx):
    body = ISSUE_BODY.replace("src/api/items.py\ntests/api/", "the api module")
    assert any("machine-readable" in e for e in errors(make_ctx(issue_body=body)))


def test_bullets_and_backticks_accepted(make_ctx):
    body = ISSUE_BODY.replace("src/api/items.py\ntests/api/", "- `src/api/items.py`\n* tests/api/**")
    files = [("M", "src/api/items.py", ["a"], []), ("A", "tests/api/x/test_y.py", ["b"], [])]
    assert errors(make_ctx(files=files, issue_body=body)) == []


def test_owner_exempt(make_ctx):
    assert errors(make_ctx(author="the-owner", files=[("M", "anything.txt", ["a"], [])])) == []


def test_missing_issue(make_ctx):
    assert errors(make_ctx(issue=False))


def test_scope_written_by_orchestrator_or_owner_ok(make_ctx):
    assert errors(make_ctx(issue_writers=["the-owner", "steward-a"])) == []


def test_scope_edited_by_implementer_rejected(make_ctx):
    errs = errors(make_ctx(issue_writers=["steward-a", "impl-b"]))
    assert any("Only owners and active orchestrators" in e for e in errs)


def test_scope_authored_by_outsider_rejected(make_ctx):
    assert any("@random" in e for e in errors(make_ctx(issue_writers=["random"])))
