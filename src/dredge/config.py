"""Layered configuration: CLI flag > $DREDGE_* env > dredge.toml > defaults.

Every knob resolves through the same four tiers so behavior is always
explainable by one precedence rule. `dredge config` prints the resolved
values and which tier each came from.
"""

from __future__ import annotations

import os
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
    pause: int = 20  # seconds between successful batches
    state_dir: Path = Path(".dredge")
    provenance: dict[str, str] = field(default_factory=dict)  # key -> tier

    def prompt_template(self) -> str:
        if self.prompt_file:
            return Path(self.prompt_file).read_text()
        return DEFAULT_PROMPT


def _env(name: str) -> str | None:
    return os.environ.get(ENV_PREFIX + name)


def load(config_path: Path | None = None, **flags: object) -> Config:
    """Resolve config through flag > env > toml > default, recording provenance."""
    path = config_path or Path(os.environ.get(ENV_PREFIX + "CONFIG", "dredge.toml"))
    file_cfg: dict[str, object] = {}
    if path.is_file():
        file_cfg = tomllib.loads(path.read_text()).get("dredge", {})

    cfg = Config()

    def resolve(key: str, cast, env_split: bool = False) -> None:
        flag = flags.get(key)
        if flag is not None:
            setattr(cfg, key, cast(flag))
            cfg.provenance[key] = "flag"
            return
        raw = _env(key.upper())
        if raw is not None:
            setattr(cfg, key, cast(raw.split(",") if env_split else raw))
            cfg.provenance[key] = "env"
            return
        if key in file_cfg:
            setattr(cfg, key, cast(file_cfg[key]))
            cfg.provenance[key] = str(path)
            return
        cfg.provenance[key] = "default"

    resolve("corpus_globs", list, env_split=True)
    resolve("rewrites", list, env_split=True)
    resolve("runner", list, env_split=True)
    resolve("ledger", Path)
    resolve("ledger_hint", str)
    resolve("prompt_file", lambda v: Path(v) if v else None)
    resolve("batch_size", int)
    resolve("backoff", lambda v: [int(x) for x in v], env_split=True)
    resolve("pause", int)
    resolve("state_dir", Path)
    return cfg
