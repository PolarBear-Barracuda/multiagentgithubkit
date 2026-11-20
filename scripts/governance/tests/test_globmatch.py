from globmatch import looks_like_path, match


def test_anchored_and_unanchored():
    assert match("AGENTS.md", "/AGENTS.md")
    assert not match("docs/AGENTS.md", "/AGENTS.md")
    assert match("docs/AGENTS.md", "AGENTS.md")  # unanchored basename matches anywhere
    assert match("a/b/c.lock", "*.lock")
    assert match("yarn.lock", "**/*.lock")


def test_double_star():
    assert match(".github/workflows/ci.yml", "/.github/**")
    assert match("src/api/v1/items.py", "src/api/**")
    assert not match("src/apix/items.py", "src/api/**")
    assert match("tests/test_x.py", "**/test_*.py")
    assert match("pkg/deep/tests/helpers.py", "**/tests/**")


def test_directory_forms():
    assert match("tests/api/test_items.py", "tests/api/")
    assert match("tests/api/test_items.py", "tests/api")
    assert not match("tests/apifoo.py", "tests/api")
    assert match("src/x.py", "./src/")


def test_single_star_stays_in_segment():
    assert match("src/a.py", "src/*.py")
    assert not match("src/sub/a.py", "src/*.py")


def test_looks_like_path():
    assert looks_like_path("src/api/**")
    assert looks_like_path("README.md")
    assert not looks_like_path("Don't change pagination.")
    assert not looks_like_path("none")
