import protected


def errors(ctx):
    return protected.run(ctx).errors


def test_agents_md_protected(make_ctx):
    assert errors(make_ctx(files=[("M", "AGENTS.md", ["x"], [])]))


def test_workflow_and_ci_script_protected(make_ctx):
    assert errors(make_ctx(files=[("M", ".github/workflows/ci.yml", ["x"], [])]))
    assert errors(make_ctx(files=[("M", "scripts/ci/test.sh", ["exit 0"], ["pytest"])]))


def test_new_adr_allowed_but_not_edits(make_ctx):
    assert errors(make_ctx(files=[("A", "docs/adr/0007-cache.md", ["x"], [])])) == []
    assert errors(make_ctx(files=[("M", "docs/adr/0001-model.md", ["x"], [])]))
    assert errors(make_ctx(files=[("D", "docs/adr/0001-model.md", [], ["x"])]))


def test_pointer_files_protected(make_ctx):
    assert errors(make_ctx(files=[("M", "TOOL_RULES.md", ["x"], [])], pointer_files=["TOOL_RULES.md"]))


def test_rename_out_of_protected(make_ctx):
    assert errors(make_ctx(files=[("R", "notes.md", [], [], "AGENTS.md")]))


def test_owner_may_edit(make_ctx):
    assert errors(make_ctx(author="the-owner", files=[("M", "AGENTS.md", ["x"], [])])) == []


def test_normal_code_ok(make_ctx):
    assert errors(make_ctx()) == []
