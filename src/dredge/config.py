"""Layered configuration: CLI flag > $DREDGE_* env > dredge.toml > defaults.

Every knob resolves through the same four tiers so behavior is always
explainable by one precedence rule. `dredge config` prints the resolved
values and which tier each came from.

List-valued env vars: DREDGE_RUNNER is parsed with shlex (shell-like words,
so argv elements may contain commas); other lists are comma-separated.
Relative paths from the toml file resolve against the file's directory.
"""

from __future__ import annotations

import os
import shlex
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ENV_PREFIX = "DREDGE_"
DEFAULT_BACKOFF = [300, 1800, 7200]

DEFAULT_PROMPT = """\
Exhaustive extraction pass over a corpus (one batch of a scripted full sweep; id: {batch_id}).
Process EVERY directory listed below; do not skip any.
For each, record what you extracted, then append every processed directory to {ledger_hint} as '- <path> - <one-word disposition>'.
Directories in this batch:
{items}
"""


class ConfigError(Exception):
    """Invalid or missing configuration; CLI maps this to exit 2."""


@dataclass
class Config:
    corpus_globs: list[str] = field(default_factory=list)
    rewrites: list[str] = field(default_factory=list)  # "hostprefix=agentprefix"
    runner: list[str] = field(default_factory=list)  # argv; {prompt} placeholder
    ledger: Path = Path("coverage-ledger.md")
    ledger_hint: str = "/coverage-ledger.md"  # how the agent addresses the ledger
    prompt_file: Path | None = None
    batch_size: int = 40
    backoff: list[int] = field(default_factory=lambda: list(DEFAULT_BACKOFF))
    pause: int = 20  # seconds between batches
    state_dir: Path = Path(".dredge")
    provenance: dict[str, str] = field(default_factory=dict)  # key -> tier

    def prompt_template(self) -> str:
        if self.prompt_file:
            return Path(self.prompt_file).read_text()
        return DEFAULT_PROMPT


def _env(name: str) -> str | None:
    return os.environ.get(ENV_PREFIX + name)


def _validate(cfg: Config) -> None:
    if cfg.batch_size < 1:
        raise ConfigError(f"batch_size must be >= 1 (got {cfg.batch_size})")
    if cfg.pause < 0:
        raise ConfigError(f"pause must be >= 0 (got {cfg.pause})")
    if any(b < 0 for b in cfg.backoff):
        raise ConfigError(f"backoff waits must be >= 0 (got {cfg.backoff})")
    for r in cfg.rewrites:
        if "=" not in r:
            raise ConfigError(f"rewrite must be 'hostprefix=agentprefix' (got {r!r})")


def load(config_path: Path | None = None, **flags: object) -> Config:
    """Resolve config through flag > env > toml > default, recording provenance."""
    env_config = _env("CONFIG")
    explicit = config_path is not None or env_config is not None
    path = config_path or Path(env_config or "dredge.toml")
    if explicit and not path.is_file():
        raise ConfigError(f"config file not found: {path}")

    file_cfg: dict[str, object] = {}
    if path.is_file():
        file_cfg = tomllib.loads(path.read_text()).get("dredge", {})

    cfg = Config()
    cfg.provenance["config"] = str(path) if path.is_file() else "(none)"

    def resolve(key: str, cast, env_cast=None) -> None:
        flag = flags.get(key)
        if flag is not None:
            setattr(cfg, key, cast(flag))
            cfg.provenance[key] = "flag"
            return
        raw = _env(key.upper())
        if raw is not None:
            setattr(cfg, key, (env_cast or cast)(raw))
            cfg.provenance[key] = "env"
            return
        if key in file_cfg:
            setattr(cfg, key, cast(file_cfg[key]))
            cfg.provenance[key] = str(path)
            return
        cfg.provenance[key] = "default"

    comma = lambda raw: [x for x in raw.split(",") if x]
    resolve("corpus_globs", list, env_cast=comma)
    resolve("rewrites", list, env_cast=comma)
    resolve("runner", list, env_cast=shlex.split)
    resolve("ledger", Path)
    resolve("ledger_hint", str)
    resolve("prompt_file", lambda v: Path(v) if v else None)
    resolve("batch_size", int)
    resolve("backoff", lambda v: [int(x) for x in v], env_cast=lambda raw: [int(x) for x in comma(raw)])
    resolve("pause", int)
    resolve("state_dir", Path)

    # Paths given in the toml file are relative to the file, not the cwd.
    base = path.parent
    for key in ("ledger", "prompt_file", "state_dir"):
        val = getattr(cfg, key)
        if cfg.provenance.get(key) == str(path) and val is not None and not Path(val).is_absolute():
            setattr(cfg, key, base / val)

    _validate(cfg)
    return cfg
