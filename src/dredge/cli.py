"""dredge - coverage-guaranteed agent sweeps over a file corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import config as config_mod
from .engine import Sweep, covered, enumerate_corpus, pending

app = typer.Typer(help=__doc__, no_args_is_help=True, add_completion=True)

ConfigOpt = typer.Option(None, "--config", "-c", help="Path to dredge.toml")


def _load(config: Optional[Path], **flags: object) -> config_mod.Config:
    cfg = config_mod.load(config, **{k: v for k, v in flags.items() if v is not None})
    if not cfg.corpus_globs:
        typer.echo("dredge: no corpus_globs configured (dredge.toml, $DREDGE_CORPUS_GLOBS, or --glob)", err=True)
        raise typer.Exit(2)
    return cfg


def _coverage_view(config: Optional[Path], glob: Optional[list[str]]) -> None:
    cfg = _load(config, corpus_globs=glob)
    manifest = enumerate_corpus(cfg.corpus_globs, cfg.rewrites)
    todo = pending(manifest, cfg.ledger)
    batches = (len(todo) + cfg.batch_size - 1) // cfg.batch_size if todo else 0
    typer.echo(f"corpus:  {len(manifest)} items")
    typer.echo(f"covered: {len(manifest) - len(todo)}")
    typer.echo(f"pending: {len(todo)}  ({batches} batches of <= {cfg.batch_size})")


@app.command()
def plan(
    config: Optional[Path] = ConfigOpt,
    glob: Optional[list[str]] = typer.Option(None, "--glob", "-g", help="Corpus glob (repeatable)"),
) -> None:
    """Enumerate the corpus and show what a sweep would cover."""
    _coverage_view(config, glob)


@app.command()
def run(
    config: Optional[Path] = ConfigOpt,
    glob: Optional[list[str]] = typer.Option(None, "--glob", "-g"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", "-b"),
) -> None:
    """Run the sweep to completion (resumable; progress lives in the ledger)."""
    cfg = _load(config, corpus_globs=glob, batch_size=batch_size)
    if not cfg.runner:
        typer.echo("dredge: no runner configured", err=True)
        raise typer.Exit(2)
    manifest = enumerate_corpus(cfg.corpus_globs, cfg.rewrites)
    result = Sweep(cfg, manifest).run()
    typer.echo(f"sweep complete: +{result.completed} covered, {len(result.unprocessable)} unprocessable")
    if result.unprocessable:
        out = cfg.state_dir / "unprocessable.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(result.unprocessable) + "\n")
        typer.echo(f"unprocessable items written to {out}")
        raise typer.Exit(1)


@app.command()
def status(
    config: Optional[Path] = ConfigOpt,
    glob: Optional[list[str]] = typer.Option(None, "--glob", "-g"),
) -> None:
    """Coverage counts: manifest vs ledger."""
    _coverage_view(config, glob)


@app.command()
def verify(
    config: Optional[Path] = ConfigOpt,
    glob: Optional[list[str]] = typer.Option(None, "--glob", "-g"),
) -> None:
    """Audit: list every corpus item missing from the ledger (exit 1 if any)."""
    cfg = _load(config, corpus_globs=glob)
    manifest = enumerate_corpus(cfg.corpus_globs, cfg.rewrites)
    missing = pending(manifest, cfg.ledger)
    for p in missing:
        typer.echo(p)
    if missing:
        typer.echo(f"MISSING: {len(missing)} of {len(manifest)}", err=True)
        raise typer.Exit(1)
    typer.echo(f"complete: all {len(manifest)} items covered")


@app.command(name="config")
def show_config(config: Optional[Path] = ConfigOpt) -> None:
    """Print resolved configuration and where each value came from."""
    cfg = config_mod.load(config)
    for key, tier in cfg.provenance.items():
        typer.echo(f"{key:12} = {getattr(cfg, key)!r:60}  [{tier}]")


@app.command()
def orphans(
    config: Optional[Path] = ConfigOpt,
    glob: Optional[list[str]] = typer.Option(None, "--glob", "-g"),
) -> None:
    """List ledger entries whose corpus item no longer exists."""
    cfg = _load(config, corpus_globs=glob)
    manifest = set(enumerate_corpus(cfg.corpus_globs, cfg.rewrites))
    for p in sorted(covered(cfg.ledger) - manifest):
        typer.echo(p)
