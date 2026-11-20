from context import linked_issues, parse_name_status, parse_unified_diff


def test_linked_issues_ignores_comments_and_dedupes():
    body = "<!-- Closes #1 -->\nCloses #12\nfixes #12\nResolves: #13"
    assert linked_issues(body) == [12, 13]
    assert linked_issues("Closes #<!-- n -->") == []


def test_name_status_rename():
    ch = parse_name_status("M\ta.py\nR087\told/t.py\tnew/t.py\nD\tgone.py\n")
    assert [(c.status, c.path, c.old_path) for c in ch] == [("M", "a.py", None), ("R", "new/t.py", "old/t.py"), ("D", "gone.py", None)]
    assert ch[1].touched_paths == ["new/t.py", "old/t.py"]


def test_unified_diff_parsing():
    diff = """diff --git a/src/a.py b/src/a.py
index 1..2 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
--- not a header, a removed line starting with --
+++ an added line starting with ++
diff --git a/gone.py b/gone.py
deleted file mode 100644
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-assert x
-y
diff --git a/img.png b/img.png
Binary files a/img.png and b/img.png differ
"""
    d = parse_unified_diff(diff)
    assert d["src/a.py"]["removed"] == ["-- not a header, a removed line starting with --"]
    assert d["src/a.py"]["added"] == ["++ an added line starting with ++"]
    assert d["gone.py"]["removed"] == ["assert x", "y"]
    assert d["img.png"] == {"added": [], "removed": []}
