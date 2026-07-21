"""dredge - coverage-guaranteed agent sweeps over a file corpus.

Exit codes: 0 sweep/audit complete; 1 incomplete coverage or unprocessable
items; 2 configuration error; 3 runner executable not found; 130 interrupted.
Records (paths, resolved values) go to stdout; narration goes to stderr.
"""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from typing import Annotated

import typer

from . import config as config_mod
from .engine import CorpusError, RunnerNotFound, Sweep, covered, enumerate_corpus, pending

app = typer.Typer(help=__doc__, no_args_is_help=True, add_completion=True)


def _version(value: bool) -> None:
    if value:
        typer.echo(importlib.metadata.version("dredge"))
        raise typer.Exit(0)


@app.callback()
def main(
    ctx: typer.Context,
    config: Annotated[Path | None, typer.Option("--config", "-c", help="Path to dredge.toml")] = None,
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Print version and exit")
    ] = False,
) -> None:
    ctx.obj = config


Globs = Annotated[list[str] | None, typer.Option("--glob", "-g", help="Corpus glob (repeatable; ** recurses)")]


def _load(ctx: typer.Context, **flags: object) -> config_mod.Config:
    try:
        cfg = config_mod.load(ctx.obj, **{k: v for k, v in flags.items() if v is not None})
    except config_mod.ConfigError as e:
        typer.echo(f"dredge: {e}", err=True)
        raise typer.Exit(2) from e
    if not cfg.corpus_globs:
        typer.echo("dredge: no corpus_globs configured (dredge.toml, $DREDGE_CORPUS_GLOBS, or --glob)", err=True)
        raise typer.Exit(2)
    return cfg


def _manifest(cfg: config_mod.Config, allow_empty: bool = False) -> list[str]:
    try:
        manifest = enumerate_corpus(cfg.corpus_globs, cfg.rewrites)
    except CorpusError as e:
        typer.echo(f"dredge: {e}", err=True)
        raise typer.Exit(2) from e
    if not manifest and not allow_empty:
        typer.echo("dredge: corpus globs matched nothing - check paths/rewrites", err=True)
        raise typer.Exit(2)
    return manifest


def _counts(cfg: config_mod.Config, manifest: list[str]) -> list[str]:
    todo = pending(manifest, cfg.ledger)
    batches = (len(todo) + cfg.batch_size - 1) // cfg.batch_size
    return [
        f"corpus:  {len(manifest)} items",
        f"covered: {len(manifest) - len(todo)}",
        f"pending: {len(todo)}  ({batches} batches of <= {cfg.batch_size})",
    ]


@app.command()
def plan(ctx: typer.Context, glob: Globs = None) -> None:
    """Show what a sweep would do: coverage counts plus the first batch preview."""
    cfg = _load(ctx, corpus_globs=glob)
    manifest = _manifest(cfg)
    for line in _counts(cfg, manifest):
        typer.echo(line)
    todo = pending(manifest, cfg.ledger)
    if todo:
        head = todo[: cfg.batch_size]
        typer.echo(f"first batch ({len(head)} items):")
        for p in head[:10]:
            typer.echo(f"  {p}")
        if len(head) > 10:
            typer.echo(f"  ... and {len(head) - 10} more")


@app.command()
def status(ctx: typer.Context, glob: Globs = None) -> None:
    """Coverage counts: manifest vs ledger."""
    cfg = _load(ctx, corpus_globs=glob)
    for line in _counts(cfg, _manifest(cfg)):
        typer.echo(line)


@app.command()
def run(
    ctx: typer.Context,
    glob: Globs = None,
    batch_size: Annotated[
        int | None,
        typer.Option(
            "--batch-size",
            "-b",
            min=1,
            help="Items per runner invocation (default 40; smaller batches bisect cheaper, cost more runs)",
        ),
    ] = None,
) -> None:
    """Run the sweep to completion (resumable; progress lives in the ledger)."""
    cfg = _load(ctx, corpus_globs=glob, batch_size=batch_size)
    if not cfg.runner:
        typer.echo("dredge: no runner configured", err=True)
        raise typer.Exit(2)
    manifest = _manifest(cfg)
    sweep = Sweep(cfg, manifest, log=lambda m: typer.echo(m, err=True))
    try:
        result = sweep.run()
    except RunnerNotFound as e:
        typer.echo(f"dredge: runner not found: {e}", err=True)
        raise typer.Exit(3) from e
    except KeyboardInterrupt:
        left = pending(manifest, cfg.ledger)
        typer.echo(
            f"dredge: interrupted; {len(manifest) - len(left)} covered, {len(left)} pending - rerun to resume",
            err=True,
        )
        raise typer.Exit(130) from None

    out = cfg.state_dir / "unprocessable.txt"
    if result.unprocessable:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(result.unprocessable) + "\n", encoding="utf-8")
        typer.echo(f"unprocessable items written to {out}", err=True)
    else:
        out.unlink(missing_ok=True)  # don't let a stale report imply failure

    if result.complete:
        typer.echo(f"sweep complete: +{result.completed} covered")
    else:
        typer.echo(
            f"sweep INCOMPLETE: +{result.completed} covered, {len(result.remaining)} still pending "
            f"({len(result.unprocessable)} unprocessable)",
            err=True,
        )
        raise typer.Exit(1)


@app.command()
def verify(ctx: typer.Context, glob: Globs = None) -> None:
    """Audit: list every corpus item missing from the ledger (exit 1 if any)."""
    cfg = _load(ctx, corpus_globs=glob)
    manifest = _manifest(cfg)
    missing = pending(manifest, cfg.ledger)
    for p in missing:
        typer.echo(p)
    if missing:
        typer.echo(f"MISSING: {len(missing)} of {len(manifest)}", err=True)
        raise typer.Exit(1)
    typer.echo(f"complete: all {len(manifest)} items covered", err=True)


@app.command()
def orphans(ctx: typer.Context, glob: Globs = None) -> None:
    """List ledger entries whose corpus item no longer exists."""
    cfg = _load(ctx, corpus_globs=glob)
    manifest = set(_manifest(cfg, allow_empty=True))
    for p in sorted(covered(cfg.ledger) - manifest):
        typer.echo(p)


@app.command(name="config")
def show_config(ctx: typer.Context) -> None:
    """Print resolved configuration and where each value came from.

    Note: runner argv is printed verbatim - redact before pasting publicly.
    """
    try:
        cfg = config_mod.load(ctx.obj)
    except config_mod.ConfigError as e:
        typer.echo(f"dredge: {e}", err=True)
        raise typer.Exit(2) from e
    for key, tier in cfg.provenance.items():
        value = getattr(cfg, key, "-") if key != "config" else tier
        typer.echo(f"{key:13} = {value!r:60}  [{tier}]")
