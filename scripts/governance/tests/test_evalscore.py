import evalscore


def test_scoring_and_ranking(tmp_path):
    seeds = tmp_path / "seeds"
    (seeds / "R01").mkdir(parents=True)
    (seeds / "R01" / "answer-key.yml").write_text("seed: R01\nbugs:\n  - id: B1\n  - id: B2\n")
    (seeds / "R02").mkdir()
    (seeds / "R02" / "answer-key.yml").write_text("seed: R02\nbugs: []\n")
    results = tmp_path / "results"
    results.mkdir()
    (results / "_example.yml").write_text("agent: ignored\n")
    (results / "2026-01-01-x.yml").write_text(
        "agent: x\ndate: 2026-01-01\nreview:\n  - {seed: R01, found: [B1], false_positives: 3}\n")
    (results / "2026-02-01-x.yml").write_text(
        "agent: x\ndate: 2026-02-01\n"
        "implement:\n  - {task: T1, ci_pass_first_push: true, accepted: true, in_scope: true}\n"
        "  - {task: T2, ci_pass_first_push: false, accepted: false, in_scope: true}\n"
        "review:\n  - {seed: R01, found: [B1, B2], false_positives: 0}\n  - {seed: R02, found: [], false_positives: 1}\n"
        "tests:\n  - {task: Q1, mutants_killed: 3, mutants_total: 4}\n")
    (results / "2026-02-01-y.yml").write_text(
        "agent: y\ndate: 2026-02-01\nreview:\n  - {seed: R01, found: [B1], false_positives: 0}\n"
        "planning:\n  - {task: P1, decomposition: 5, criteria_testable: 5, escalated_correctly: true}\n")
    s = evalscore.score(str(results), str(seeds))
    assert set(s) == {"x", "y"}
    x = s["x"]
    assert x["date"] == "2026-02-01"  # latest file wins
    assert abs(x["implement"] - 0.6) < 1e-9  # (1.0 + 0.2) / 2
    assert abs(x["review_precision"] - 2 / 3) < 1e-9
    assert x["review_recall"] == 1.0
    assert x["tests"] == 0.75
    y = s["y"]
    assert y["review_precision"] == 1.0 and y["review_recall"] == 0.5
    assert y["planning"] == 1.0
    out = evalscore.render(s, {"x": "fam-1"})
    assert "| x | fam-1 |" in out
    assert "**Reviewer** (review_f05): " in out
