"""dredge - coverage-guaranteed agent sweeps over a file corpus."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import config as config_mod
from .engine import Sweep, covered, enumerate_corpus, pending

app = typer.Typer(help=__doc__, no_args_is_help=True, add_completion=True)


@app.callback()
def main(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to dredge.toml"),
) -> None:
    ctx.obj = config


def _load(ctx: typer.Context, **flags: object) -> config_mod.Config:
    try:
        cfg = config_mod.load(ctx.obj, **{k: v for k, v in flags.items() if v is not None})
    except config_mod.ConfigError as e:
        typer.echo(f"dredge: {e}", err=True)
        raise typer.Exit(2)
    if not cfg.corpus_globs:
        typer.echo("dredge: no corpus_globs configured (dredge.toml, $DREDGE_CORPUS_GLOBS, or --glob)", err=True)
        raise typer.Exit(2)
    return cfg


def _manifest(cfg: config_mod.Config) -> list[str]:
    manifest = enumerate_corpus(cfg.corpus_globs, cfg.rewrites)
    if not manifest:
        typer.echo("dredge: corpus globs matched nothing - check paths/rewrites", err=True)
        raise typer.Exit(2)
    return manifest


GlobOpt = typer.Option(None, "--glob", "-g", help="Corpus glob (repeatable)")


def _coverage_view(ctx: typer.Context, glob: Optional[list[str]]) -> None:
    cfg = _load(ctx, corpus_globs=glob)
    manifest = _manifest(cfg)
    todo = pending(manifest, cfg.ledger)
    batches = (len(todo) + cfg.batch_size - 1) // cfg.batch_size
    typer.echo(f"corpus:  {len(manifest)} items")
    typer.echo(f"covered: {len(manifest) - len(todo)}")
    typer.echo(f"pending: {len(todo)}  ({batches} batches of <= {cfg.batch_size})")


@app.command()
def plan(ctx: typer.Context, glob: Optional[list[str]] = GlobOpt) -> None:
    """Enumerate the corpus and show what a sweep would cover."""
    _coverage_view(ctx, glob)


@app.command()
def status(ctx: typer.Context, glob: Optional[list[str]] = GlobOpt) -> None:
    """Coverage counts: manifest vs ledger."""
    _coverage_view(ctx, glob)


@app.command()
def run(
    ctx: typer.Context,
    glob: Optional[list[str]] = GlobOpt,
    batch_size: Optional[int] = typer.Option(None, "--batch-size", "-b"),
) -> None:
    """Run the sweep to completion (resumable; progress lives in the ledger)."""
    cfg = _load(ctx, corpus_globs=glob, batch_size=batch_size)
    if not cfg.runner:
        typer.echo("dredge: no runner configured", err=True)
        raise typer.Exit(2)
    manifest = _manifest(cfg)
    result = Sweep(cfg, manifest).run()
    typer.echo(f"sweep complete: +{result.completed} covered, {len(result.unprocessable)} unprocessable")
    out = cfg.state_dir / "unprocessable.txt"
    if result.unprocessable:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(result.unprocessable) + "\n")
        typer.echo(f"unprocessable items written to {out}")
        raise typer.Exit(1)
    out.unlink(missing_ok=True)  # don't let a stale report imply failure


@app.command()
def verify(ctx: typer.Context, glob: Optional[list[str]] = GlobOpt) -> None:
    """Audit: list every corpus item missing from the ledger (exit 1 if any)."""
    cfg = _load(ctx, corpus_globs=glob)
    manifest = _manifest(cfg)
    missing = pending(manifest, cfg.ledger)
    for p in missing:
        typer.echo(p)
    if missing:
        typer.echo(f"MISSING: {len(missing)} of {len(manifest)}", err=True)
        raise typer.Exit(1)
    typer.echo(f"complete: all {len(manifest)} items covered")


@app.command()
def orphans(ctx: typer.Context, glob: Optional[list[str]] = GlobOpt) -> None:
    """List ledger entries whose corpus item no longer exists."""
    cfg = _load(ctx, corpus_globs=glob)
    manifest = set(_manifest(cfg))
    for p in sorted(covered(cfg.ledger) - manifest):
        typer.echo(p)


@app.command(name="config")
def show_config(ctx: typer.Context) -> None:
    """Print resolved configuration and where each value came from."""
    try:
        cfg = config_mod.load(ctx.obj)
    except config_mod.ConfigError as e:
        typer.echo(f"dredge: {e}", err=True)
        raise typer.Exit(2)
    for key, tier in cfg.provenance.items():
        value = getattr(cfg, key, "-") if key != "config" else tier
        typer.echo(f"{key:12} = {value!r:60}  [{tier}]")
