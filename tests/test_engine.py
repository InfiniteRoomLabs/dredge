"""Engine behavior: ledger truth, fixpoint completion, bisection, rewrites."""

from pathlib import Path

import pytest

from dredge.config import Config
from dredge.engine import CorpusError, RetryPolicy, Sweep, covered, enumerate_corpus, pending


def make_cfg(tmp_path: Path, **kw) -> Config:
    cfg = Config(**kw)
    cfg.ledger = tmp_path / "ledger.md"
    cfg.ledger_hint = str(cfg.ledger)
    cfg.backoff = [0]  # one retry, no waiting
    cfg.pause = 0
    return cfg


def append_ledger(cfg: Config, items, disposition="done") -> None:
    with cfg.ledger.open("a", encoding="utf-8") as f:
        for p in items:
            f.write(f"- {p} - {disposition}\n")


def batch_items(argv) -> list[str]:
    return [line for line in argv[1].splitlines() if line.startswith("/c/")]


# --- ledger parsing -------------------------------------------------------


def test_pending_is_manifest_minus_ledger(tmp_path):
    cfg = make_cfg(tmp_path)
    append_ledger(cfg, ["/c/a", "/c/b"])
    assert pending(["/c/a", "/c/b", "/c/x"], cfg.ledger) == ["/c/x"]
    assert covered(cfg.ledger) == {"/c/a", "/c/b"}


def test_ledger_paths_containing_delimiter(tmp_path):
    cfg = make_cfg(tmp_path)
    append_ledger(cfg, ["/c/notes - draft/conv"])
    assert covered(cfg.ledger) == {"/c/notes - draft/conv"}


def test_malformed_ledger_lines_ignored(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.ledger.write_text(
        "# heading\n"
        "- /c/good - done\n"
        "- nodisposition\n"
        "* /c/wrongbullet - done\n"
        "-/c/nospace - done\n"
        "random prose\n"
        "- /c/dup - done\n"
        "- /c/dup - done\n",
        encoding="utf-8",
    )
    assert covered(cfg.ledger) == {"/c/good", "/c/dup"}


def test_bom_tolerated(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.ledger.write_bytes(b"\xef\xbb\xbf- /c/a - done\n")
    assert covered(cfg.ledger) == {"/c/a"}


# --- enumeration and rewrites ---------------------------------------------


def test_recursive_globs(tmp_path):
    (tmp_path / "a/b").mkdir(parents=True)
    (tmp_path / "a/b/f.md").write_text("x", encoding="utf-8")
    got = enumerate_corpus([str(tmp_path / "**/*.md")])
    assert got == [str(tmp_path / "a/b/f.md")]


def test_rewrite_component_boundaries(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "database").mkdir()
    got = enumerate_corpus([str(tmp_path / "data*")], [f"{tmp_path}/data=/x"])
    assert f"{tmp_path}/database" in got and "/x" in got


def test_rewrite_collision_detected(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    with pytest.raises(CorpusError, match="collision"):
        enumerate_corpus([str(tmp_path / "*")], [f"{tmp_path}/a=/x", f"{tmp_path}/b=/x"])


def test_rewrite_root_collapse_detected(tmp_path):
    (tmp_path / "a").mkdir()
    with pytest.raises(CorpusError, match="collapsed"):
        enumerate_corpus([str(tmp_path / "a")], [f"{tmp_path}/a=/"])


# --- retry policy ----------------------------------------------------------


def test_retry_policy_truncates_bisection_budget():
    p = RetryPolicy.from_backoff([300, 1800, 7200])
    assert p.initial == (300, 1800, 7200)
    assert p.bisection == (300,)
    assert p.final == ()


# --- sweep -----------------------------------------------------------------


def test_sweep_completes_and_verifies_progress(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=2)
    manifest = [f"/c/{i}" for i in range(5)]
    calls = []

    def fake_run(argv):
        items = batch_items(argv)
        calls.append(items)
        append_ledger(cfg, items)
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert result.complete and result.completed == 5
    assert result.remaining == [] and result.unprocessable == []
    assert len(calls) == 3  # 2 + 2 + 1


def test_exit_zero_without_ledger_growth_is_failure_then_bisected(tmp_path):
    """A runner that lies (exit 0, no ledger writes) for one poison item."""
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=4)
    manifest = ["/c/good1", "/c/poison", "/c/good2", "/c/good3"]

    def fake_run(argv):
        append_ledger(cfg, [p for p in batch_items(argv) if p != "/c/poison"])
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert not result.complete
    assert result.completed == 3
    assert result.remaining == ["/c/poison"]
    assert result.unprocessable == ["/c/poison"]


def test_multiple_poison_items_isolated(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=8)
    manifest = [f"/c/{i}" for i in range(6)] + ["/c/p1", "/c/p2"]

    def fake_run(argv):
        append_ledger(cfg, [p for p in batch_items(argv) if p not in ("/c/p1", "/c/p2")])
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert not result.complete
    assert sorted(result.unprocessable) == ["/c/p1", "/c/p2"]
    assert result.completed == 6


def test_ledger_regression_yields_incomplete(tmp_path):
    """An entry removed mid-run must surface at the final fixpoint."""
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=10)
    manifest = ["/c/a", "/c/b"]
    append_ledger(cfg, ["/c/a"])

    def fake_run(argv):
        # Covers /c/b but clobbers the whole ledger, losing /c/a.
        cfg.ledger.write_text("- /c/b - done\n", encoding="utf-8")
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert not result.complete
    assert result.remaining == ["/c/a"]


def test_resume_skips_covered(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=10)
    manifest = ["/c/a", "/c/b", "/c/c"]
    append_ledger(cfg, ["/c/a", "/c/b"])
    seen = []

    def fake_run(argv):
        items = batch_items(argv)
        seen.extend(items)
        append_ledger(cfg, items)
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert seen == ["/c/c"] and result.complete


def test_manifest_deduped(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=10)
    seen = []

    def fake_run(argv):
        items = batch_items(argv)
        seen.extend(items)
        append_ledger(cfg, items)
        return True

    Sweep(cfg, ["/c/a", "/c/a"], run_cmd=fake_run, sleep=lambda s: None).run()
    assert seen == ["/c/a"]


def test_prompt_render_survives_braces_and_no_reexpansion(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"])
    pf = tmp_path / "p.txt"
    pf.write_text("literal {braces} ok\nhint={ledger_hint}\n{items}\n", encoding="utf-8")
    cfg.prompt_file = pf
    cfg.ledger_hint = "contains {items} token"
    s = Sweep(cfg, [], run_cmd=lambda a: True, sleep=lambda s: None)
    out = s._render_prompt("b", ["/c/{weird}/path"])
    assert "literal {braces} ok" in out
    assert "hint=contains {items} token" in out
    assert "/c/{weird}/path" in out
    assert out.count("/c/{weird}/path") == 1  # hint's {items} not re-expanded
