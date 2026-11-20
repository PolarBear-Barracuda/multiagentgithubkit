"""test-weakening: detect removed tests/assertions, new skip/focus markers, lowered coverage thresholds."""
from __future__ import annotations

import re

from config import LABEL_TEST_OVERRIDE
from context import Context
from globmatch import match_any
from report import Report

ASSERT_RE = re.compile(
    r"(\bassert\w*\b|\bexpect\s*\(|\.should\b|\bshould\.|\.to(Be|Equal|Have|Throw|Match|Contain|Strict)\w*\s*\(|"
    r"\brequire\.\w+\(|\bt\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\(|\bAssert\.\w+\(|\bXCTAssert\w*\b|"
    r"\bverify\s*\(|\bassertThat\s*\(|\bself\.assert\w*\s*\(|\bpytest\.(raises|warns|fail)\s*\(|"
    r"\.(rejects|resolves)\b|\b(REQUIRE|CHECK)(_\w+)?\s*\(|\bmust\.\w+\(|\bShould\(\))"
)

SKIP_PATTERNS = [
    r"@pytest\.mark\.(skip|skipif|xfail)\b",
    r"\bpytest\.(skip|xfail)\s*\(",
    r"@unittest\.(skip|skipIf|skipUnless|expectedFailure)\b",
    r"\b(it|test|describe|context|suite)\.(skip|todo)\s*\(",
    r"\b(xit|xdescribe|xtest|xcontext)\s*\(",
    r"\bt\.Skip(Now|f)?\s*\(",
    r"#\[\s*ignore\b",
    r"@(Disabled|Ignore)\b",
    r"\[\s*(Ignore|Skip)\b",
    r"\[\s*Fact\s*\(\s*Skip\s*=",
    r"\bpending\s*\(",
    r"\bmarkTestSkipped\s*\(",
]
SKIP_RE = re.compile("|".join(SKIP_PATTERNS))

FOCUS_RE = re.compile(r"\b(it|test|describe|context|suite)\.only\s*\(|\b(fit|fdescribe|ftest|fcontext)\s*\(")

COVERAGE_RE = re.compile(
    r"(fail_under|fail-under|cov-fail-under|coverageThreshold|minimum_coverage|min_coverage|"
    r"coverage_threshold|minCoverage|jacocoTestCoverageVerification|covermode)",
    re.I,
)


def _code(line: str) -> str:
    """Drop obvious comment-only lines so commented-out code doesn't count."""
    s = line.strip()
    if s.startswith(("#", "//", "/*", "*", "--")) and not s.startswith("#["):
        return ""
    return line


def analyze(ctx: Context) -> tuple[list[str], list[str]]:
    """Return (blocking_without_override, always_blocking)."""
    findings: list[str] = []
    always: list[str] = []
    patterns = ctx.config.test_patterns

    for ch in ctx.changes:
        is_test = match_any(ch.path, patterns)
        was_test = bool(ch.old_path and match_any(ch.old_path, patterns))

        if ch.status == "D" and is_test:
            findings.append(f"Test file deleted: {ch.path}")
            continue
        if ch.status == "R" and was_test and not is_test:
            findings.append(f"Test file moved out of test paths: {ch.old_path} -> {ch.path}")

        added = [_code(l) for l in ch.added]
        removed = [_code(l) for l in ch.removed]

        if is_test or was_test:
            a_add = sum(1 for l in added if ASSERT_RE.search(l))
            a_rem = sum(1 for l in removed if ASSERT_RE.search(l))
            if a_rem > a_add:
                findings.append(f"{ch.path}: net {a_rem - a_add} assertion(s) removed ({a_rem} removed, {a_add} added)")
            for l in added:
                if SKIP_RE.search(l):
                    findings.append(f"{ch.path}: skip/ignore marker added: `{l.strip()[:120]}`")
            for l in added:
                if FOCUS_RE.search(l):
                    always.append(f"{ch.path}: focus marker added (silently skips other tests): `{l.strip()[:120]}`")

        for l in removed:
            if COVERAGE_RE.search(l):
                findings.append(f"{ch.path}: coverage/threshold setting changed: `{l.strip()[:120]}`")
                break
    return findings, always


def run(ctx: Context) -> Report:
    r = Report("test-weakening")
    findings, always = analyze(ctx)
    owner = ctx.config.is_owner(ctx.author)

    for f in always:
        if owner:
            r.warn(f)
        else:
            r.error(f + " — remove it; this can't be overridden.")

    if findings:
        if owner:
            for f in findings:
                r.warn(f)
            r.note("Author is an owner: findings reported but not blocking.")
        elif ctx.label_applied_by_owner(LABEL_TEST_OVERRIDE):
            for f in findings:
                r.warn(f)
            r.note(f"Allowed: '{LABEL_TEST_OVERRIDE}' was applied by an owner.")
        else:
            for f in findings:
                r.error(f)
            r.error(
                f"Tests appear to be weakened. If this is intended, explain why in the PR and add "
                f"'needs-human-decision'; only an owner can apply '{LABEL_TEST_OVERRIDE}'."
            )
    if not findings and not always:
        r.note("No test weakening detected.")
    return r
