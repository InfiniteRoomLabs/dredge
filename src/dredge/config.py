"""Layered configuration: CLI flag > $DREDGE_* env > dredge.toml > defaults.

Every knob resolves through the same four tiers so behavior is always
explainable by one precedence rule. `dredge config` prints the resolved
values and which tier each came from.

Values are PARSED, not coerced: a wrong shape (string where a list of ints
belongs, unknown key, empty env var) is a ConfigError naming the key and
tier, never a silent reinterpretation.

List-valued env vars: DREDGE_RUNNER is parsed with shlex (shell-like words,
so argv elements may contain commas); other lists are comma-separated.
Relative paths from the toml file resolve against the file's directory.
"""

from __future__ import annotations

import os
import shlex
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

ENV_PREFIX = "DREDGE_"
DEFAULT_BACKOFF = [300, 1800, 7200]

DEFAULT_PROMPT = """\
Exhaustive extraction pass over a corpus (one batch of a scripted full sweep; id: {batch_id}).
Process EVERY directory listed below; do not skip any.
For each, record what you extracted, then append every processed directory \
to {ledger_hint} as '- <path> - <one-word disposition>'.
Directories in this batch:
{items}
"""


class ConfigError(Exception):
    """Invalid or missing configuration; the CLI maps this to exit 2."""


@dataclass
class Config:
    corpus_globs: list[str] = field(default_factory=list[str])
    rewrites: list[str] = field(default_factory=list[str])  # "hostprefix=agentprefix"
    runner: list[str] = field(default_factory=list[str])  # argv; one exact {prompt} element
    ledger: Path = Path("coverage-ledger.md")
    ledger_hint: str = ""  # how the agent addresses the ledger; defaults to the resolved ledger path
    prompt_file: Path | None = None
    batch_size: int = 40
    backoff: list[int] = field(default_factory=lambda: list(DEFAULT_BACKOFF))
    batch_timeout: int = 0  # seconds per runner invocation; 0 = unlimited
    pause: int = 20  # seconds between batches
    state_dir: Path = Path(".dredge")
    provenance: dict[str, str] = field(default_factory=dict[str, str])  # key -> tier

    def prompt_template(self) -> str:
        if self.prompt_file:
            return Path(self.prompt_file).read_text(encoding="utf-8")
        return DEFAULT_PROMPT


KNOWN_KEYS = {
    "corpus_globs",
    "rewrites",
    "runner",
    "ledger",
    "ledger_hint",
    "prompt_file",
    "batch_size",
    "backoff",
    "batch_timeout",
    "pause",
    "state_dir",
}


def _env(name: str) -> str | None:
    # Empty is unset: an accidentally blank export must not shadow real config.
    val = os.environ.get(ENV_PREFIX + name)
    return val if val else None


def _err(key: str, tier: str, expected: str, got: object) -> ConfigError:
    return ConfigError(f"{key} (from {tier}): expected {expected}, got {got!r}")


def _parse_str(key: str, tier: str, v: object) -> str:
    if not isinstance(v, str):
        raise _err(key, tier, "string", v)
    return v


def _parse_path(key: str, tier: str, v: object) -> Path:
    return Path(_parse_str(key, tier, v))


def _parse_int(key: str, tier: str, v: object, minimum: int) -> int:
    # bool is an int subclass; a TOML `true` is not a number here.
    if isinstance(v, bool) or not isinstance(v, int):
        if isinstance(v, str) and v.lstrip("-").isdigit():
            v = int(v)
        else:
            raise _err(key, tier, "integer", v)
    if v < minimum:
        raise ConfigError(f"{key} (from {tier}): must be >= {minimum}, got {v}")
    return v


def _parse_str_list(key: str, tier: str, v: object) -> list[str]:
    bad: object = v
    if not isinstance(v, list) or not all(isinstance(x, str) for x in cast(list[object], v)):
        raise _err(key, tier, "list of strings", bad)
    return [x for x in (s.strip() for s in cast(list[str], v)) if x]


def _parse_int_list(key: str, tier: str, v: object) -> list[int]:
    if not isinstance(v, list):
        raise _err(key, tier, "list of integers", v)
    return [_parse_int(key, tier, x, minimum=0) for x in cast(list[object], v)]


def _split_comma(raw: str) -> list[str]:
    return [x for x in (s.strip() for s in raw.split(",")) if x]


def _validate(cfg: Config) -> None:
    for r in cfg.rewrites:
        src, sep, dst = r.partition("=")
        if not sep or not src.strip() or not dst.strip():
            raise ConfigError(f"rewrite must be 'hostprefix=agentprefix' with both sides nonempty (got {r!r})")
    if cfg.runner and "{prompt}" not in cfg.runner:
        raise ConfigError(
            "runner argv must contain an exact '{prompt}' element - without it every batch runs promptless"
        )


def load(config_path: Path | None = None, **flags: object) -> Config:
    """Resolve config through flag > env > toml > default, recording provenance."""
    env_config = _env("CONFIG")
    explicit = config_path is not None or env_config is not None
    path = config_path or Path(env_config or "dredge.toml")
    if explicit and not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    file_cfg: dict[str, object] = {}
    if path.is_file():
        try:
            doc = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: invalid TOML: {e}") from e
        section: object = doc.get("dredge", {})
        if not isinstance(section, dict):
            raise ConfigError(f"{path}: [dredge] must be a table")
        section = cast(dict[str, object], section)
        unknown = set(section) - KNOWN_KEYS
        if unknown:
            raise ConfigError(
                f"{path}: unknown keys: {', '.join(sorted(unknown))} (known: {', '.join(sorted(KNOWN_KEYS))})"
            )
        file_cfg = section

    unknown_flags = set(flags) - KNOWN_KEYS
    if unknown_flags:
        raise ConfigError(f"unknown option(s): {', '.join(sorted(unknown_flags))}")

    cfg = Config()
    tier_file = str(path)
    cfg.provenance["config"] = tier_file if path.is_file() else "(none)"

    def resolve(key: str, parse: Callable[[str, str, object], object], env_parse: Callable[[str], object]) -> None:
        flag = flags.get(key)
        if flag is not None:
            setattr(cfg, key, parse(key, "flag", flag))
            cfg.provenance[key] = "flag"
            return
        raw = _env(key.upper())
        if raw is not None:
            setattr(cfg, key, parse(key, "env", env_parse(raw)))
            cfg.provenance[key] = "env"
            return
        if key in file_cfg:
            setattr(cfg, key, parse(key, tier_file, file_cfg[key]))
            cfg.provenance[key] = tier_file
            return
        cfg.provenance[key] = "default"

    def as_is(raw: str) -> object:
        return raw

    resolve("corpus_globs", _parse_str_list, _split_comma)
    resolve("rewrites", _parse_str_list, _split_comma)
    resolve("runner", _parse_str_list, shlex.split)
    resolve("ledger", _parse_path, as_is)
    resolve("ledger_hint", _parse_str, as_is)
    resolve("prompt_file", _parse_path, as_is)
    resolve("batch_size", lambda k, t, v: _parse_int(k, t, v, minimum=1), as_is)
    resolve("backoff", _parse_int_list, lambda raw: [int(x) for x in _split_comma(raw)])
    resolve("batch_timeout", lambda k, t, v: _parse_int(k, t, v, minimum=0), as_is)
    resolve("pause", lambda k, t, v: _parse_int(k, t, v, minimum=0), as_is)
    resolve("state_dir", _parse_path, as_is)

    # Paths given in the toml file - or defaulted while a toml file is in
    # play - are relative to the file, not the process cwd: a project's
    # state belongs with its config.
    base = path.parent
    for key in ("ledger", "prompt_file", "state_dir"):
        val = getattr(cfg, key)
        anchored_tier = cfg.provenance.get(key) in (tier_file, "default") and path.is_file()
        if anchored_tier and val is not None and not Path(val).is_absolute():
            setattr(cfg, key, base / val)

    # A zero-config agent must be pointed at the same file dredge reads:
    # the hint defaults to the resolved ledger path itself.
    if cfg.provenance["ledger_hint"] == "default" or not cfg.ledger_hint:
        cfg.ledger_hint = str(cfg.ledger)
        cfg.provenance["ledger_hint"] = "derived(ledger)"

    _validate(cfg)
    return cfg
