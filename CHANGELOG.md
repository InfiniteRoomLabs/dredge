# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-21

### Added

- Initial extraction from the openwiki corpus-backfill driver into a standalone CLI: `plan`, `run`, `status`, `verify`, `orphans`, `config` subcommands.
- Ledger-as-source-of-truth sweep engine: pending = manifest minus ledger, progress-verified batches, provider-shaped backoff, bisection of failing batches, deferred-single retry round, unprocessable reporting.
- Layered configuration (flag > `$DREDGE_*` env > `dredge.toml` > defaults) with provenance display.
- Example configuration for the OpenWiki personal-wiki backfill use case.
