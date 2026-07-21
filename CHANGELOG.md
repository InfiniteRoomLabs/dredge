# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Completion is now a final `manifest - ledger` fixpoint: `run` exits 1 with a `sweep INCOMPLETE` report whenever items remain pending, including after mid-run ledger regression.
- Typed `RetryPolicy`: bisection halves retry on a truncated budget and the final single-item round is one-shot, so a poison item can no longer compound the full backoff schedule at every bisection level.
- Total config parsing: unknown keys, wrong shapes (`backoff = "300"`, booleans as ints), empty env vars, and a runner argv missing the exact `{prompt}` element are hard errors with key + tier in the message; `$DREDGE_RUNNER` is shlex-parsed.
- Path anchoring: toml-provided and defaulted paths resolve relative to the config file; `ledger_hint` defaults to the resolved ledger path.
- Corpus safety: recursive `**` globs, rewrite collision and root-collapse detection, manifest dedupe.
- `--version`, per-command exit-code contract (0/1/2/3/130), stderr narration with stdout reserved for records, `batch_timeout`, SIGINT resume message, stale `unprocessable.txt` cleanup, differentiated `plan` (first-batch preview) vs `status`.
- Packaging and enforcement: MIT `LICENSE`, full project metadata + `py.typed`, ruff + strict-on-src pyright + pytest branch-coverage gate (90%), pre-commit config, SHA-pinned uv-native CI (3.12-3.14 matrix, lock check, wheel smoke test), tag-guarded PyPI Trusted Publishing workflow, `CONTRIBUTING.md`/`SECURITY.md`/issue + PR templates, ledger-grammar and configuration reference docs, `examples/openwiki-prompt.txt`.

## [0.1.0] - 2026-07-21

### Added

- Initial extraction from the openwiki corpus-backfill driver into a standalone CLI: `plan`, `run`, `status`, `verify`, `orphans`, `config` subcommands.
- Ledger-as-source-of-truth sweep engine: pending = manifest minus ledger, progress-verified batches, provider-shaped backoff, bisection of failing batches, deferred-single retry round, unprocessable reporting.
- Layered configuration (flag > `$DREDGE_*` env > `dredge.toml` > defaults) with provenance display.
- Example configuration for the OpenWiki personal-wiki backfill use case.
