# Contributing

## Setup

Python 3.12+ and [uv](https://docs.astral.sh/uv/). Then:

```sh
uv sync --locked --all-groups
uv run pre-commit install
```

## The loop

```sh
uv run pytest --cov --cov-fail-under=90   # tests + branch coverage gate
uv run ruff check . && uv run ruff format --check .
uv run pyright                            # strict on src/
uv build                                  # wheel must build
```

CI runs exactly these on 3.12/3.13/3.14; all are required to merge.

## Expectations

- Behavior changes come with tests; user-visible changes add a line under `## [Unreleased]` in CHANGELOG.md.
- The ledger grammar, TOML keys, `$DREDGE_*` names, CLI verbs, stdout records, and exit codes are compatibility surface - changing any is a breaking change and versions accordingly (SemVer).
- Sign off your commits (DCO, `git commit -s`): you certify you have the right to contribute the change under MIT.
- GitHub is canonical; the Gitea remote is a mirror. Releases are cut by maintainers from protected `v*` tags.
