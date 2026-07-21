"""Config layering: precedence, provenance, parsing totality, path anchoring."""

from pathlib import Path

import pytest

from dredge.config import Config, ConfigError, load


def write_toml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "dredge.toml"
    p.write_text(f"[dredge]\n{body}", encoding="utf-8")
    return p


def test_precedence_flag_env_file_default(tmp_path, monkeypatch):
    p = write_toml(tmp_path, "batch_size = 10\npause = 5\n")
    monkeypatch.setenv("DREDGE_PAUSE", "7")
    cfg = load(p, batch_size=3)
    assert (cfg.batch_size, cfg.provenance["batch_size"]) == (3, "flag")
    assert (cfg.pause, cfg.provenance["pause"]) == (7, "env")
    assert cfg.provenance["backoff"] == "default"


def test_empty_env_is_unset(tmp_path, monkeypatch):
    p = write_toml(tmp_path, "batch_size = 10\n")
    monkeypatch.setenv("DREDGE_BATCH_SIZE", "")
    assert load(p).batch_size == 10


def test_unknown_toml_key_rejected(tmp_path):
    p = write_toml(tmp_path, "batchsize = 10\n")
    with pytest.raises(ConfigError, match="unknown keys: batchsize"):
        load(p)


def test_backoff_string_rejected_not_charsplit(tmp_path):
    p = write_toml(tmp_path, 'backoff = "300"\n')
    with pytest.raises(ConfigError, match="backoff"):
        load(p)


def test_bool_is_not_an_int(tmp_path):
    p = write_toml(tmp_path, "batch_size = true\n")
    with pytest.raises(ConfigError, match="integer"):
        load(p)


def test_batch_size_zero_rejected(tmp_path):
    p = write_toml(tmp_path, "batch_size = 0\n")
    with pytest.raises(ConfigError, match=">= 1"):
        load(p)


def test_runner_requires_prompt_element(tmp_path):
    p = write_toml(tmp_path, 'runner = ["echo", "hi"]\n')
    with pytest.raises(ConfigError, match="prompt"):
        load(p)


def test_runner_env_shlex_allows_commas(tmp_path, monkeypatch):
    p = write_toml(tmp_path, "")
    monkeypatch.setenv("DREDGE_RUNNER", "docker run --label 'a,b' img {prompt}")
    assert load(p).runner == ["docker", "run", "--label", "a,b", "img", "{prompt}"]


def test_rewrite_needs_both_sides(tmp_path):
    p = write_toml(tmp_path, 'rewrites = ["=/x"]\n')
    with pytest.raises(ConfigError, match="rewrite"):
        load(p)


def test_toml_relative_paths_anchor_to_file(tmp_path):
    sub = tmp_path / "cfgdir"
    sub.mkdir()
    p = sub / "dredge.toml"
    p.write_text('[dredge]\nledger = "wiki/ledger.md"\n', encoding="utf-8")
    assert load(p).ledger == sub / "wiki/ledger.md"


def test_explicit_missing_config_fails(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load(tmp_path / "nope.toml")


def test_invalid_toml_is_config_error(tmp_path):
    p = tmp_path / "dredge.toml"
    p.write_text("[dredge\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load(p)


def test_ledger_hint_derives_from_ledger(tmp_path):
    p = write_toml(tmp_path, 'ledger = "l.md"\n')
    cfg = load(p)
    assert cfg.ledger_hint == str(tmp_path / "l.md")
    assert cfg.provenance["ledger_hint"] == "derived(ledger)"


def test_default_prompt_has_all_tokens():
    t = Config().prompt_template()
    assert all(tok in t for tok in ("{batch_id}", "{items}", "{ledger_hint}"))
