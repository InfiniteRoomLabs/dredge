"""CLI surface: exit codes, stream discipline, examples validity."""

from pathlib import Path

from typer.testing import CliRunner

from dredge.cli import app
from dredge.config import load

runner = CliRunner()

REPO = Path(__file__).resolve().parent.parent


def write_setup(tmp_path: Path, n_items: int = 3) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for i in range(n_items):
        (corpus / f"item{i}").mkdir()
    p = tmp_path / "dredge.toml"
    p.write_text(
        f'[dredge]\ncorpus_globs = ["{corpus}/*"]\nledger = "ledger.md"\n',
        encoding="utf-8",
    )
    return p


def test_help_and_version():
    assert runner.invoke(app, ["--help"]).exit_code == 0
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0 and r.stdout.strip()


def test_missing_config_exits_2(tmp_path):
    r = runner.invoke(app, ["-c", str(tmp_path / "nope.toml"), "status"])
    assert r.exit_code == 2


def test_no_globs_exits_2(tmp_path):
    p = tmp_path / "dredge.toml"
    p.write_text("[dredge]\n", encoding="utf-8")
    assert runner.invoke(app, ["-c", str(p), "status"]).exit_code == 2


def test_empty_corpus_exits_2(tmp_path):
    p = tmp_path / "dredge.toml"
    p.write_text(f'[dredge]\ncorpus_globs = ["{tmp_path}/nothing/*"]\n', encoding="utf-8")
    assert runner.invoke(app, ["-c", str(p), "status"]).exit_code == 2


def test_verify_incomplete_exits_1_lists_missing_on_stdout(tmp_path):
    p = write_setup(tmp_path)
    r = runner.invoke(app, ["-c", str(p), "verify"])
    assert r.exit_code == 1
    assert str(tmp_path / "corpus" / "item0") in r.stdout


def test_verify_complete_exits_0(tmp_path):
    p = write_setup(tmp_path, n_items=1)
    (tmp_path / "ledger.md").write_text(f"- {tmp_path}/corpus/item0 - done\n", encoding="utf-8")
    assert runner.invoke(app, ["-c", str(p), "verify"]).exit_code == 0


def test_run_without_runner_exits_2(tmp_path):
    p = write_setup(tmp_path)
    assert runner.invoke(app, ["-c", str(p), "run"]).exit_code == 2


def test_status_and_plan_show_counts(tmp_path):
    p = write_setup(tmp_path)
    s = runner.invoke(app, ["-c", str(p), "status"])
    assert "corpus:  3 items" in s.stdout
    pl = runner.invoke(app, ["-c", str(p), "plan"])
    assert "first batch" in pl.stdout


def test_config_shows_provenance(tmp_path):
    p = write_setup(tmp_path)
    r = runner.invoke(app, ["-c", str(p), "config"])
    assert r.exit_code == 0 and "[flag]" not in r.stdout and str(p) in r.stdout


RUNNER_SCRIPT = """\
import sys
from pathlib import Path

prompt = sys.argv[1]
ledger = Path(sys.argv[2])
skip = sys.argv[3] if len(sys.argv) > 3 else None
with ledger.open("a", encoding="utf-8") as f:
    for line in prompt.splitlines():
        if line.startswith("/") or (line and line[1:3] == ":\\\\"):
            if skip and skip in line:
                continue
        else:
            continue
        f.write(f"- {line} - done\\n")
"""


def write_run_setup(tmp_path: Path, skip: str = "") -> Path:
    import sys

    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    for i in range(3):
        (corpus / f"item{i}").mkdir(exist_ok=True)
    script = tmp_path / "runner.py"
    script.write_text(RUNNER_SCRIPT, encoding="utf-8")
    ledger = tmp_path / "ledger.md"
    runner = [sys.executable, str(script), "{prompt}", str(ledger)] + ([skip] if skip else [])
    runner_toml = ", ".join(f'"{a}"' for a in runner)
    p = tmp_path / "dredge.toml"
    p.write_text(
        f'[dredge]\ncorpus_globs = ["{corpus}/*"]\nledger = "ledger.md"\n'
        f"runner = [{runner_toml}]\nbackoff = [0]\npause = 0\n",
        encoding="utf-8",
    )
    return p


def test_run_end_to_end_success(tmp_path):
    p = write_run_setup(tmp_path)
    r = runner.invoke(app, ["-c", str(p), "run"])
    assert r.exit_code == 0, r.output
    assert "sweep complete: +3 covered" in r.stdout
    assert runner.invoke(app, ["-c", str(p), "verify"]).exit_code == 0


def test_run_incomplete_exits_1_and_writes_unprocessable(tmp_path):
    p = write_run_setup(tmp_path, skip="item1")
    r = runner.invoke(app, ["-c", str(p), "run"])
    assert r.exit_code == 1
    report = tmp_path / ".dredge" / "unprocessable.txt"
    assert report.is_file() and "item1" in report.read_text(encoding="utf-8")
    # A later successful run must clear the stale report.
    p2 = write_run_setup(tmp_path)
    assert runner.invoke(app, ["-c", str(p2), "run"]).exit_code == 0
    assert not report.is_file()


def test_run_missing_runner_binary_exits_3(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a").mkdir()
    p = tmp_path / "dredge.toml"
    p.write_text(
        f'[dredge]\ncorpus_globs = ["{corpus}/*"]\nledger = "l.md"\n'
        'runner = ["/nonexistent/binary", "{prompt}"]\nbackoff = [0]\npause = 0\n',
        encoding="utf-8",
    )
    assert runner.invoke(app, ["-c", str(p), "run"]).exit_code == 3


def test_orphans_lists_vanished_items(tmp_path):
    p = write_setup(tmp_path, n_items=1)
    (tmp_path / "ledger.md").write_text("- /gone/item - done\n", encoding="utf-8")
    r = runner.invoke(app, ["-c", str(p), "orphans"])
    assert r.exit_code == 0 and "/gone/item" in r.stdout


def test_config_command_reports_bad_config(tmp_path):
    p = tmp_path / "dredge.toml"
    p.write_text("[dredge]\nbatch_size = 0\n", encoding="utf-8")
    assert runner.invoke(app, ["-c", str(p), "config"]).exit_code == 2


def test_examples_are_loadable_and_reference_real_files():
    for example in (REPO / "examples").glob("*.toml"):
        cfg = load(example)
        if cfg.prompt_file is not None:
            assert Path(cfg.prompt_file).is_file(), f"{example.name} references missing {cfg.prompt_file}"
