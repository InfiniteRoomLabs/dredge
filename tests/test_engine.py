"""Engine behavior: ledger-derived pending, progress verification, bisection."""

from pathlib import Path

from dredge.config import Config
from dredge.engine import Sweep, covered, pending


def make_cfg(tmp_path: Path, **kw) -> Config:
    cfg = Config(**kw)
    cfg.ledger = tmp_path / "ledger.md"
    cfg.backoff = [0]  # one retry, no waiting
    cfg.pause = 0
    return cfg


def append_ledger(cfg: Config, items) -> None:
    with cfg.ledger.open("a") as f:
        for p in items:
            f.write(f"- {p} - done\n")


def test_pending_is_manifest_minus_ledger(tmp_path):
    cfg = make_cfg(tmp_path)
    append_ledger(cfg, ["/c/a", "/c/b"])
    assert pending(["/c/a", "/c/b", "/c/x"], cfg.ledger) == ["/c/x"]
    assert covered(cfg.ledger) == {"/c/a", "/c/b"}


def test_sweep_completes_and_verifies_progress(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=2)
    manifest = [f"/c/{i}" for i in range(5)]
    calls = []

    def fake_run(argv):
        # Extract the batch items from the rendered prompt and cover them.
        items = [l for l in argv[1].splitlines() if l.startswith("/c/")]
        calls.append(items)
        append_ledger(cfg, items)
        return True

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert result.completed == 5
    assert result.unprocessable == []
    assert pending(manifest, cfg.ledger) == []
    assert len(calls) == 3  # 2 + 2 + 1


def test_exit_zero_without_ledger_growth_is_failure_then_bisected(tmp_path):
    """A runner that lies (exit 0, no ledger writes) for one poison item."""
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=4)
    manifest = ["/c/good1", "/c/poison", "/c/good2", "/c/good3"]

    def fake_run(argv):
        items = [l for l in argv[1].splitlines() if l.startswith("/c/")]
        append_ledger(cfg, [p for p in items if p != "/c/poison"])
        return True  # always claims success

    result = Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert result.completed == 3
    assert result.unprocessable == ["/c/poison"]
    assert pending(manifest, cfg.ledger) == ["/c/poison"]


def test_ledger_paths_containing_delimiter(tmp_path):
    cfg = make_cfg(tmp_path)
    append_ledger(cfg, ["/c/notes - draft/conv"])
    assert covered(cfg.ledger) == {"/c/notes - draft/conv"}
    assert pending(["/c/notes - draft/conv"], cfg.ledger) == []


def test_prompt_render_survives_braces(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"])
    cfg.prompt_file = tmp_path / "p.txt"
    cfg.prompt_file.write_text("literal {braces} ok\n{items}\n")
    s = Sweep(cfg, [], run_cmd=lambda a: True, sleep=lambda s: None)
    out = s._render_prompt("b", ["/c/{weird}/path"])
    assert "literal {braces} ok" in out and "/c/{weird}/path" in out


def test_rewrite_component_boundaries(tmp_path):
    from dredge.engine import enumerate_corpus

    (tmp_path / "data").mkdir()
    (tmp_path / "database").mkdir()
    got = enumerate_corpus([str(tmp_path / "data*")], [f"{tmp_path}/data=/x"])
    assert f"{tmp_path}/database" in got and "/x" in got


def test_resume_skips_covered(tmp_path):
    cfg = make_cfg(tmp_path, runner=["fake", "{prompt}"], batch_size=10)
    manifest = ["/c/a", "/c/b", "/c/c"]
    append_ledger(cfg, ["/c/a", "/c/b"])
    seen = []

    def fake_run(argv):
        items = [l for l in argv[1].splitlines() if l.startswith("/c/")]
        seen.extend(items)
        append_ledger(cfg, items)
        return True

    Sweep(cfg, manifest, run_cmd=fake_run, sleep=lambda s: None).run()
    assert seen == ["/c/c"]
