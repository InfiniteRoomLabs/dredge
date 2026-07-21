# Executive Summary

1. Strong: The ledger-only reconciliation model is small, resumable, and correctly treats observable ledger growth—not runner exit status—as progress.
2. Strong: `engine.py` is separated from Typer and already exposes runner, sleep, and logging seams suitable for deeper effect isolation.
3. Strong: Deterministic manifest ordering, explicit configuration provenance, `src/` packaging, uv locking, and a minimal dependency set are sound foundations.
4. Fix first: Make completion a final `manifest − ledger` fixpoint; queue exhaustion currently permits false success.
5. Fix second: Replace compounding retry schedules with typed initial, bisection, and one-shot final policies.
6. Fix third: Replace permissive configuration coercion with typed parsers that reject wrong shapes, unknown keys, and missing `{prompt}`.
7. Fix fourth: Specify and validate the ledger grammar and disposition semantics; it is the product’s persistent wire protocol.
8. Fix fifth: Add direct configuration, CLI, malformed-ledger, bisection, regression, interruption, and rewrite-collision tests.
9. Fix sixth: Establish blocking uv-native CI with Ruff, strict Pyright, tests, lock verification, and wheel smoke testing.
10. Fix seventh: Add the MIT license, complete package metadata and example assets, then release exclusively from protected version tags.

## 1. ARCH

- ARCH-1 [DEFECT][S1] Success currently means only “no unprocessable items,” allowing ledger regression to leave pending items while `run` exits 0; perform final `pending(manifest, ledger)` reconciliation and return `Complete | Incomplete` (`src/dredge/engine.py:132-166`, `src/dredge/cli.py:81-89`).
- ARCH-2 [DEFECT][S1] Every bisection level and deferred retry pays the full 9,300-second backoff, turning one poison item into an 18-hour-plus sweep; define separate initial, truncated-bisection, and one-shot-final retry policies (`src/dredge/engine.py:120-160`, `README.md:11`).
- ARCH-3 [DEFECT][S2] `_run_batch()` computes a verdict that `_attempt()` discards, including an unreachable `ok and before == 0` branch, then redundantly rereads the ledger; return and consume one typed batch outcome (`src/dredge/engine.py:104-123`).
- ARCH-4 [GAP][S2] Concurrent sweeps can duplicate work, credit another process’s ledger writes, and race over `unprocessable.txt`; enforce one owner per ledger with an advisory lock or explicitly reject concurrency (`src/dredge/engine.py:108-160`, `src/dredge/cli.py:83-89`).
- ARCH-5 [GAP][S2] `Callable[[list[str]], bool]` erases exit code, signal, timeout, duration, and diagnostics; replace it with a `Runner` protocol returning `RunResult` while retaining ledger growth as the success oracle (`src/dredge/engine.py:77-92`).
- ARCH-6 [GAP][S2] `Sweep.run()` interleaves planning, reconciliation, retry policy, bisection, sleeping, subprocess execution, and reporting; extract a pure `next_action(state, observation)` transition (`src/dredge/engine.py:115-166`).
- ARCH-7 [GAP][S2] Engine narration is an unstructured callback defaulting to stdout; emit typed events such as `BatchStarted`, `RetryScheduled`, `Bisected`, and `Deferred` for CLI-owned rendering (`src/dredge/engine.py:83,121-159`).
- ARCH-8 [GAP][S2] `Sweep` receives the complete mutable CLI `Config` despite using only runner, prompt, ledger, batch, retry, and pause fields; construct a frozen engine-specific `SweepPolicy` (`src/dredge/engine.py:77-102`, `src/dredge/config.py:36-48`).
- ARCH-9 [DEFECT][S3] `SweepResult.deferred` records historical rather than terminal state, so successfully retried items remain listed; rename it `ever_deferred` or model disjoint terminal outcomes (`src/dredge/engine.py:64-68,153-160`).
- ARCH-10 [DEFECT][S3] Batch IDs restart at `batch-000` on every resumed run; derive stable IDs from manifest offsets or content hashes (`src/dredge/engine.py:134-138`).
- ARCH-11 [DEFECT][S3] Embedding provenance inside `Config` causes the config path to be printed as both value and tier; return resolved values and provenance separately (`src/dredge/config.py:36-48,84-102`, `src/dredge/cli.py:123-125`).
- ARCH-12 [PRACTICE][S3] Preserve the current engine/CLI boundary and deterministic ordering with an import-boundary test and manifest determinism test (`src/dredge/engine.py:12-19,31-40,59-61`, `src/dredge/cli.py:8-11`).

## 2. REPO

- REPO-1 [DEFECT][S1] The README claims MIT but the repository has no `LICENSE` and package metadata declares no license; add canonical MIT text plus `license = "MIT"` and `license-files = ["LICENSE"]` (`README.md:37-39`, `pyproject.toml:1-11`, repository root).
- REPO-2 [DEFECT][S2] `CHANGELOG.md` declares 0.1.0 while no Git tag exists; land release automation, then create protected tag `v0.1.0` under the organization’s tag-driven convention (`CHANGELOG.md:8-15`, Git tags).
- REPO-3 [DEFECT][S2] The advertised complete OpenWiki setup references absent `examples/openwiki-prompt.txt`, causing first prompt rendering to fail; ship the prompt and validate all example-local references (`README.md:27`, `examples/openwiki.toml:14`, `src/dredge/config.py:50-53`).
- REPO-4 [GAP][S2] Published metadata lacks `readme`, classifiers, keywords, and source/issues/changelog URLs; complete `[project]` and `[project.urls]` (`pyproject.toml:1-14`).
- REPO-5 [GAP][S2] The annotated package lacks `src/dredge/py.typed`; add the PEP 561 marker and include it in built wheels (`src/dredge/`, `pyproject.toml:20-22`).
- REPO-6 [DEFECT][S3] Version is triplicated across metadata, runtime code, and changelog; derive runtime version through `importlib.metadata.version("dredge")` and gate release agreement (`pyproject.toml:3`, `src/dredge/__init__.py:3`, `CHANGELOG.md:8`).
- REPO-7 [DEFECT][S3] Installation follows a floating Git default branch; publish to PyPI or pin the fallback URL to `@v0.1.0` (`README.md:31-35`).
- REPO-8 [GAP][S3] Keep-a-Changelog usage omits `[Unreleased]` and comparison links; add both before accepting the next change (`CHANGELOG.md:1-15`).
- REPO-9 [GAP][S3] `.gitignore` omits `build/`, `dist/`, `.coverage*`, `htmlcov/`, `.ruff_cache/`, `.mypy_cache/`, and `.pyright/`; ignore outputs created by the proposed workflow (`.gitignore:1-7`).
- REPO-10 [GAP][S3] The declared Python floor is 3.12 but no `.python-version` pins it locally; pin 3.12 and let CI cover 3.12–3.14 (`pyproject.toml:8`, repository root).
- REPO-11 [GAP][S3] GitHub and Gitea remotes exist without a documented canonical/mirror relationship; identify GitHub as canonical and document synchronization and release ownership (`.git/config:6-14`).

### Contested

- Position A: `ledger_hint = "/coverage-ledger.md"` conflicts with the declared OpenWiki mount and requires a corrected path or explicit mount (`examples/openwiki.toml:9,13,20`).
- Position B: `ledger_hint` is documented as the path visible to the agent and may be resolved by OpenWiki relative to its wiki namespace; the mismatch is unproven, so document semantics rather than changing the value (`examples/openwiki.toml:13`, `src/dredge/engine.py:94-102`).

## 3. IDIOM

- IDIOM-1 [DEFECT][S1] Generic `list` and `int` coercions accept invalid TOML shapes—strings become character lists, booleans become integers, and floats truncate; replace them with shape-checking per-field parsers (`src/dredge/config.py:87-112`).
- IDIOM-2 [DEFECT][S2] `backoff = "300"` becomes `[3, 0, 0]`, silently defeating retry policy; require `list[int]`, reject booleans and strings, and report key plus source tier (`src/dredge/config.py:112`).
- IDIOM-3 [DEFECT][S2] `glob.glob()` omits `recursive=True`, so conventional `**` patterns under-enumerate a supposedly coverage-guaranteed corpus; use recursive iteration and define hidden-file behavior (`src/dredge/engine.py:31-32`).
- IDIOM-4 [DEFECT][S2] TOML, prompt, ledger, and report I/O use locale-default encodings; use UTF-8 explicitly and `utf-8-sig` for BOM-tolerant ledger reads (`src/dredge/config.py:52,82`, `src/dredge/engine.py:48`, `src/dredge/cli.py:86`).
- IDIOM-5 [GAP][S2] `subprocess.run()` has no timeout, allowing a hung runner to block reconciliation forever; add `batch_timeout` and handle `subprocess.TimeoutExpired` (`src/dredge/engine.py:91-92`).
- IDIOM-6 [DEFECT][S2] TOML table shape and key set are unchecked, so typos silently use defaults and `dredge = "x"` triggers substring membership behavior; require a mapping and reject unknown keys (`src/dredge/config.py:80-100`).
- IDIOM-7 [PRACTICE][S2] Retain the custom four-tier resolver: Pydantic Settings and Click `ParameterSource` do not directly provide per-key provenance plus TOML-relative paths; document this design decision (`src/dredge/config.py:72-123`).
- IDIOM-8 [DEFECT][S3] The comma parser is an E731 lambda that preserves spaces and empty elements; replace it with a named parser that strips and rejects empties (`src/dredge/config.py:104-112`).
- IDIOM-9 [PRACTICE][S3] Modernize Typer declarations to `Annotated[T | None, typer.Option(...)]` rather than legacy `Optional` and positional defaults (`src/dredge/cli.py:6,19,44,73`).
- IDIOM-10 [PRACTICE][S3] Replace manual step slicing with Python 3.12’s `itertools.batched` only as a readability modernization; current slicing is correct (`src/dredge/engine.py:137-138`, `pyproject.toml:8`).
- IDIOM-11 [DEFECT][S3] Sequential token replacement can expand `{items}` introduced through `ledger_hint`; perform one-pass token substitution while retaining literal-brace safety instead of using `str.format()` (`src/dredge/engine.py:94-102`, `tests/test_engine.py:72-78`).
- IDIOM-12 [PRACTICE][S3] Keep the dependency-free ledger parser, but move its grammar into named parse/format functions with documented behavior (`src/dredge/engine.py:43-56`).

## 4. CICD

- CICD-1 [GAP][S1] No CI exists; add a blocking push/PR gate running `uv sync --locked --all-groups`, Ruff check/format, strict Pyright, and pytest (`pyproject.toml:1-25`, `.github/workflows/` absent).
- CICD-2 [GAP][S2] Matrix-test Python 3.12, 3.13, and 3.14 with 3.12 required because the declared floor has no automated evidence (`pyproject.toml:8`).
- CICD-3 [GAP][S2] Run `uv lock --check` separately so dependency or metadata changes cannot leave the committed lock stale (`uv.lock`, `pyproject.toml`).
- CICD-4 [GAP][S2] Add branch coverage with `pytest --cov=dredge --cov-branch --cov-fail-under=90` after direct config and CLI tests land (`tests/test_engine.py`, `src/dredge/config.py`, `src/dredge/cli.py`).
- CICD-5 [GAP][S2] On protected `v*` tags, run checks, `uv build`, metadata validation, clean-wheel installation, and `dredge --help` smoke testing before publication (`pyproject.toml:13-22`).
- CICD-6 [GAP][S2] Publish through PyPI Trusted Publishing with a protected environment and job-scoped `id-token: write`; store no long-lived package credential (`.github/workflows/` absent).
- CICD-7 [GAP][S2] Validate every `examples/*.toml` and all referenced local assets without launching Docker, mechanically preventing the missing-prompt defect (`examples/openwiki.toml:14`).
- CICD-8 [GAP][S3] Preserve the seven-day dependency gate by asserting `exclude-newer-span = "P7D"` and applying `UV_EXCLUDE_NEWER` to update jobs (`uv.lock:5-7`).
- CICD-9 [GAP][S3] Use SHA-pinned `astral-sh/setup-uv` with uv caching keyed by `uv.lock` and `pyproject.toml`, never caching `.venv` (`uv.lock`, `.gitignore:1`).
- CICD-10 [GAP][S3] Default permissions to `contents: read`, pin all actions by SHA, run `zizmor`, and generate release attestations (`.github/workflows/` absent).
- CICD-11 [GAP][S3] Declare POSIX-only support and add a macOS smoke job; slash-based rewrite semantics are not Windows-safe (`src/dredge/engine.py:33-38`, `README.md`).

### Contested

- Position A: Ruff, Pyright, and pytest should each be S1 because all are absent and the repository has no automated protection (`.github/workflows/` absent).
- Position B: For an unpublished 0.1.0, only the combined baseline PR gate is S1; matrix, standalone typechecking, and coverage expansion are S2 sequencing work (`pyproject.toml:1-25`).
- Position A: Add Windows to the interpreter matrix to validate cross-platform Python behavior (`pyproject.toml:8`).
- Position B: Declare POSIX-only support instead; hard-coded slash rewriting makes Windows an unsupported semantic contract, not merely an untested platform (`src/dredge/engine.py:33-38`).

## 5. COVER

- COVER-1 [GAP][S1] `config.py` has no direct tests for precedence, provenance, relative paths, malformed TOML, wrong shapes, unknown keys, empty environment values, or validation branches (`src/dredge/config.py:56-124`, `tests/test_engine.py`).
- COVER-2 [GAP][S1] The ledger trust boundary lacks malformed-input tests for wrong bullets, missing dispositions, unrelated Markdown, duplicates, partial writes, BOM, invalid UTF-8, and parse diagnostics (`src/dredge/engine.py:43-56`, `tests/test_engine.py:23-27,65-69`).
- COVER-3 [GAP][S1] No regression test removes an earlier ledger entry during a later batch; completion must fail whenever final `manifest − ledger` is nonempty (`src/dredge/engine.py:132-166`).
- COVER-4 [GAP][S2] No `CliRunner` tests cover help, options, stdout/stderr, exit codes 0/1/2, and `unprocessable.txt` creation/removal (`src/dredge/cli.py:13-125`, `tests/test_engine.py`).
- COVER-5 [GAP][S2] Existing tests do not exercise an actual multi-item bisection or multiple poison items; pin split order, depth-first queueing, and terminal isolation (`src/dredge/engine.py:145-151`, `tests/test_engine.py`).
- COVER-6 [GAP][S2] Wiki-resident ledger content can contain unrelated `- x - y` bullets that parse as coverage; test and define exact manifest validation or section scoping (`examples/openwiki.toml:9`, `src/dredge/engine.py:48-55`).
- COVER-7 [GAP][S2] Retry tests force `[0]` and never assert waits, attempt counts, pause placement, or distinct initial/bisection/final budgets (`src/dredge/engine.py:120-160`, `tests/test_engine.py:9-14`).
- COVER-8 [GAP][S2] Enumeration tests omit recursion, hidden files, files versus directories, symlinks, root paths, overlapping rewrites, rewrite collisions, and deletion after enumeration (`src/dredge/engine.py:22-40`, `tests/test_engine.py:81-87`).
- COVER-9 [GAP][S2] Interruptions during runner execution and sleeping are untested; assert concise diagnostics, preserved ledger progress, and successful restart (`src/dredge/engine.py:91-92,120-160`).
- COVER-10 [GAP][S2] Large corpora place every path in one argv element and can exceed `ARG_MAX`; pin `E2BIG` behavior before adding stdin or prompt-file transport (`src/dredge/engine.py:94-109`).
- COVER-11 [GAP][S3] Add Hypothesis round-trip properties over Unicode, braces, delimiters, whitespace, trailing slashes, and rewrite boundaries (`src/dredge/engine.py:22-61,94-102`).
- COVER-12 [GAP][S3] Add a 100k-entry non-timing scale test; repeated full-ledger reads currently scale with ledger size multiplied by batches and attempts (`src/dredge/engine.py:108,110,117,123,134,142,146,165`).
- COVER-13 [GAP][S3] Test `orphans` against an entirely vanished corpus and test files deleted after manifest enumeration (`src/dredge/cli.py:36-40,106-112`, `src/dredge/engine.py:134`).

## 6. ENFORCE

- ENFORCE-1 [GAP][S1] Add Ruff targeting Python 3.12 with `E,F,W,I,B,UP,PTH,SIM,RET,PERF,RUF`, retaining only a scoped `B008` exception for Typer defaults (`pyproject.toml`, `src/dredge/config.py:104`).
- ENFORCE-2 [GAP][S1] Add strict Pyright with `pythonVersion = "3.12"` and `include = ["src", "tests"]` to expose unchecked callbacks, `**flags`, and `ctx.obj` (`src/dredge/config.py:72-113`, `src/dredge/cli.py:18-26`).
- ENFORCE-3 [GAP][S2] Configure pytest with `testpaths = ["tests"]`, strict markers/config, and warnings-as-errors (`pyproject.toml:24-25`).
- ENFORCE-4 [GAP][S2] Add pre-commit hooks for Ruff fix/format, `uv lock --check`, TOML validation, trailing whitespace, EOF fixing, and large-file checks (`.pre-commit-config.yaml` absent).
- ENFORCE-5 [GAP][S2] Add locked `ruff`, `pyright`, `pytest-cov`, and `pre-commit` development dependencies so local and CI commands resolve identically (`pyproject.toml:24-25`).
- ENFORCE-6 [GAP][S2] Protect `main` with required lint, format, strict-type, test/coverage, lock, build, and installed-entry-point checks (`.github/workflows/` absent).
- ENFORCE-7 [GAP][S2] Add an import contract forbidding `dredge.engine` from importing Typer or `dredge.cli` (`src/dredge/engine.py:12-19`, `src/dredge/cli.py:8-11`).
- ENFORCE-8 [GAP][S2] Validate package metadata and smoke the installed wheel’s help, config, and invalid-config exit behavior (`pyproject.toml:1-22`, `src/dredge/cli.py:24-33`).
- ENFORCE-9 [GAP][S2] Gate release consistency across the Git tag, project metadata, installed metadata, and changelog heading (`pyproject.toml:3`, `src/dredge/__init__.py:3`, `CHANGELOG.md:8`).
- ENFORCE-10 [GAP][S3] Add branch-coverage configuration with a 90% floor only after config and CLI tests prevent a meaningless immediately-red gate (`tests/test_engine.py`, `src/dredge/config.py`, `src/dredge/cli.py`).
- ENFORCE-11 [PRACTICE][S3] Add `.editorconfig` for UTF-8/LF and enforce docstrings only on public boundaries rather than private helpers (`src/dredge/*.py`, repository root).

### Contested

- Position A: Enable Ruff `D` rules broadly so every function’s contract is machine-enforced (`src/dredge/*.py`).
- Position B: Enforce docstrings only on public APIs; blanket private-helper documentation adds noise without protecting this tool’s external contracts (`src/dredge/engine.py`, `src/dredge/config.py`).
- Position A: Add `deptry` immediately to enforce dependency hygiene (`pyproject.toml:9-11`).
- Position B: With one runtime dependency, `deptry` is low-yield S3 work; lockfile and import-boundary checks provide greater leverage (`pyproject.toml:9-11`).

## 7. DOCS

- DOCS-1 [DEFECT][S1] The ledger grammar is documented only as a loose example; specify prefix, rightmost delimiter split, trimming, trailing-slash normalization, encoding, malformed-line handling, and section scope (`README.md:9`, `src/dredge/engine.py:43-56`).
- DOCS-2 [DEFECT][S2] Every disposition counts as covered, so `- /path - failed` permanently removes an item; define “recorded means terminal” or reserve failure dispositions (`src/dredge/config.py:26`, `src/dredge/engine.py:50-55`).
- DOCS-3 [DEFECT][S2] README claims flag-first precedence for every value although only globs and batch size have flags; add options or document skipped tiers per key (`README.md:27`, `src/dredge/cli.py:44,70-76`).
- DOCS-4 [GAP][S2] Add a reference for all ten keys, TOML types, defaults, exact `$DREDGE_*` variables, list encodings, and `$DREDGE_CONFIG` (`src/dredge/config.py:1-9,36-48,74`).
- DOCS-5 [GAP][S2] Document that TOML paths resolve relative to the configuration file while environment and flag paths resolve against the process cwd (`src/dredge/config.py:116-121`).
- DOCS-6 [GAP][S2] Publish the exit contract for complete, incomplete, invalid configuration, launch failure, timeout, and interruption (`src/dredge/cli.py:24-33,81-103`).
- DOCS-7 [DEFECT][S2] `plan` and `status` produce identical output despite different promises; make `plan` show batches/rendered prompt information or merge the verbs (`src/dredge/cli.py:47-66`).
- DOCS-8 [GAP][S2] Explain argv-only execution, no shell expansion, exact-element `{prompt}` replacement, inherited child streams, timeout behavior, and command-line limits (`src/dredge/engine.py:91-109`).
- DOCS-9 [DEFECT][S2] Qualify “coverage-guaranteed” as conditional on truthful durable appends, exclusive ledger ownership, stable manifest scope, and final fixpoint verification (`README.md:3-11`, `src/dredge/engine.py:132-166`).
- DOCS-10 [DEFECT][S3] `--batch-size` lacks help text, valid range, default, and its relationship to bisection cost (`src/dredge/cli.py:73`).
- DOCS-11 [GAP][S3] Document the one-process-per-ledger concurrency stance and the derived role of `unprocessable.txt` (`README.md:7-12`, `src/dredge/cli.py:83-89`).
- DOCS-12 [GAP][S3] Generate and snapshot CLI Markdown/man-page reference so Typer help and published documentation remain synchronized (`src/dredge/cli.py:13-125`).
- DOCS-13 [GAP][S3] Failure artifacts contain agent-namespace paths users may not be able to open; document inverse rewrites or add an `--unrewrite` display (`src/dredge/cli.py:86,98-101`, `src/dredge/engine.py:29-40`).

## 8. QUALITY

- QUALITY-1 [DEFECT][S1] A runner without an exact `{prompt}` argv element executes promptless through the full retry tree; reject it during configuration loading (`src/dredge/config.py:60-69`, `src/dredge/engine.py:106-109`).
- QUALITY-2 [DEFECT][S2] Invalid TOML, casts, unreadable files, missing executables, permissions, and timeout failures escape as tracebacks; normalize them into concise diagnostics and documented exit codes (`src/dredge/config.py:50-52,77-112`, `src/dredge/engine.py:91-92`).
- QUALITY-3 [DEFECT][S2] Narration and child output contaminate stdout, and successful `verify` also prints a human summary there; reserve stdout for records and route diagnostics to stderr (`src/dredge/engine.py:83,91-92`, `src/dredge/cli.py:82-103`).
- QUALITY-4 [DEFECT][S2] Rewrite validation accepts empty sides, and root enumeration can collapse `/` to an empty manifest item; parse nonempty root-aware rewrites and preserve root explicitly (`src/dredge/config.py:67-69`, `src/dredge/engine.py:29-40`).
- QUALITY-5 [DEFECT][S2] Default `ledger` is cwd-relative while `ledger_hint` is root-absolute, directing a zero-config agent to a different file; derive the default hint from the resolved ledger (`src/dredge/config.py:41-42`).
- QUALITY-6 [DEFECT][S2] Unknown TOML keys, non-table roots, and misspelled `**flags` silently no-op or misbehave; use a known-key check and typed overrides (`src/dredge/config.py:72,80-100`).
- QUALITY-7 [DEFECT][S2] Coverage ignores disposition, allowing an honest `failed` record to count as complete; parse typed entries and define disposition-aware pending policy (`src/dredge/engine.py:50-55`).
- QUALITY-8 [DEFECT][S2] Distinct host paths can rewrite to the same agent path and collapse in the manifest set; detect non-injective rewrite mappings and report both sources (`src/dredge/engine.py:29-40`).
- QUALITY-9 [DEFECT][S2] `orphans` cannot inspect a completely vanished corpus because shared `_manifest()` exits before comparing against an empty set; give `orphans` an empty-manifest path (`src/dredge/cli.py:36-41,106-112`).
- QUALITY-10 [GAP][S2] Add `--version` backed by installed package metadata (`pyproject.toml:3,13-14`, `src/dredge/cli.py:13-21`).
- QUALITY-11 [DEFECT][S2] No SIGINT handling exists during runner execution or long sleeps; exit cleanly with covered/pending counts and a resume instruction (`src/dredge/engine.py:91-92,129`).
- QUALITY-12 [DEFECT][S3] `run` prints “sweep complete” even on the exit-1 path; render complete/incomplete only after final reconciliation and report persistence (`src/dredge/cli.py:81-89`).
- QUALITY-13 [DEFECT][S3] `covered()` silently drops malformed lines; return parse diagnostics for `verify` to report (`src/dredge/engine.py:48-56`, `src/dredge/cli.py:92-103`).
- QUALITY-14 [DEFECT][S3] Pause occurs after the final queue item; sleep only between external invocations (`src/dredge/engine.py:140-155`).
- QUALITY-15 [DEFECT][S3] Empty environment values count as configured and either crash casts or produce misleading provenance; treat empty as unset or reject it consistently (`src/dredge/config.py:56-57,93-96,110-113`).
- QUALITY-16 [DEFECT][S3] Resolved configuration and results remain mutable and are assembled with `setattr`; construct frozen slotted values after parsing (`src/dredge/config.py:36-48,84-121`, `src/dredge/engine.py:64-68`).
- QUALITY-17 [DEFECT][S3] `dredge config` prints runner argv verbatim, potentially including inline credentials; add redaction guidance and optionally a `--redact` mode (`src/dredge/cli.py:115-125`).

### Contested

- Position A: Printing complete runner argv is an S2 credential-exposure defect requiring automatic redaction (`src/dredge/cli.py:115-125`).
- Position B: Local full-value display is intentional and exposure occurs only when output is shared; retain behavior, rank S3, and require redaction guidance in bug reports (`src/dredge/cli.py:115-125`).

## 9. CONTRIB

- CONTRIB-1 [GAP][S1] Missing MIT terms leave no clear inbound-equals-outbound basis for patches; add `LICENSE` before accepting outside contributions (`README.md:37-39`, repository root).
- CONTRIB-2 [GAP][S2] Add `CONTRIBUTING.md` with Python 3.12 setup, locked uv synchronization, lint/type/test/build commands, and example validation (`pyproject.toml:8-25`).
- CONTRIB-3 [GAP][S2] Add `SECURITY.md` with private reporting and the trust statement that `dredge.toml` executes arbitrary argv and must be treated like a Makefile (`src/dredge/engine.py:91-107`).
- CONTRIB-4 [GAP][S2] Establish DCO sign-off before external commits; it is the lightweight inbound policy for an MIT project (`README.md:37-39`, repository root).
- CONTRIB-5 [GAP][S3] Add a bug template requesting version, OS/Python, redacted configuration, ledger diagnostics, rewrites, and runner behavior—never raw credential-bearing argv (`src/dredge/cli.py:115-125`).
- CONTRIB-6 [GAP][S3] Add a PR template requiring tests, an `[Unreleased]` entry for user-visible changes, lockfile review, docs, and compatibility notes (`CHANGELOG.md:1-15`, `uv.lock`).
- CONTRIB-7 [GAP][S3] Publish a SemVer compatibility policy covering ledger grammar, TOML keys, environment names, verbs, stdout records, and exit codes (`src/dredge/config.py:20-48`, `src/dredge/cli.py:57-125`).
- CONTRIB-8 [GAP][S3] Define ledger-format migration rules and compatibility fixtures because parser changes alter persistent user state (`src/dredge/engine.py:43-56`).
- CONTRIB-9 [PRACTICE][S3] Seed bounded good-first issues for CLI tests, missing prompt, `--version`, UTF-8 I/O, root-path handling, config shapes, and batch-size help (`tests/test_engine.py`, `examples/openwiki.toml:14`, `src/dredge/cli.py:73`).
- CONTRIB-10 [GAP][S3] State a realistic maintainer response contract distinguishing scheduler defects from failures in arbitrary configured runners (`README.md:29`, `src/dredge/engine.py:91-113`).
- CONTRIB-11 [GAP][S3] Document required checks, commit expectations, protected release tags, and GitHub’s canonical relationship to the Gitea mirror (`.git/config:6-14`, `.github/workflows/` absent).

## 10. TBEST

- TBEST-1 [PRACTICE][S1] Parse instead of coercing: resolve sources into raw values, then construct `ResolvedConfig` through total parsers reporting key, tier, received shape, and expected type (`src/dredge/config.py:36-48,72-124`).
- TBEST-2 [PRACTICE][S1] Encode completion as `Complete` or `Incomplete(remaining: NonEmpty[AgentPath], unprocessable)` from final reconciliation, making queue-exhausted false success unrepresentable (`src/dredge/engine.py:132-166`).
- TBEST-3 [PRACTICE][S1] Isolate subprocess, clock, ledger I/O, and reporting behind typed protocols so scheduling becomes deterministic logic over observations (`src/dredge/engine.py:71-166`).
- TBEST-4 [PRACTICE][S1] Make ledger parsing total: return typed entries plus diagnostics instead of silently discarding evidence (`src/dredge/engine.py:43-56`).
- TBEST-5 [PRACTICE][S2] Distinguish `HostPath` and `AgentPath` with validated wrappers and make enumeration the sole namespace boundary (`src/dredge/engine.py:22-40`).
- TBEST-6 [PRACTICE][S2] Parse rewrites once as `Rewrite(host_prefix, agent_prefix)` with nonempty, root-aware, injective invariants (`src/dredge/config.py:39,67-69`, `src/dredge/engine.py:29-40`).
- TBEST-7 [PRACTICE][S2] Replace ignored booleans with a closed outcome union: `FullyCovered | Progressed | Stalled | RunnerFailed(RunResult)` (`src/dredge/engine.py:104-130`).
- TBEST-8 [PRACTICE][S2] Express scheduling as `next_action(state) -> Run | Sleep | Bisect | Defer | Finish` with typed initial, bisection, and final retry policies (`src/dredge/engine.py:115-160`).
- TBEST-9 [PRACTICE][S2] Use frozen slotted dataclasses for resolved configuration, policies, ledger entries, events, and result snapshots (`src/dredge/config.py:36-48`, `src/dredge/engine.py:64-68`).
- TBEST-10 [PRACTICE][S2] Add Hypothesis state-machine tests over manifest changes, ledger growth/regression, interruption, restart, rewrites, and bisection; assert `Complete` iff final pending is empty (`src/dredge/engine.py:59-61,132-166`).
- TBEST-11 [PRACTICE][S2] Model prompt transport as `Arg | Stdin | PromptFile` to avoid `ARG_MAX` while preserving safe argv composition (`src/dredge/engine.py:94-109`).
- TBEST-12 [PRACTICE][S3] Emit typed events rendered as stderr text, JSON, or JSON Lines so quiet mode and future parallel workers remain additive (`src/dredge/engine.py:83,121-159`, `src/dredge/cli.py:47-125`).
- TBEST-13 [PRACTICE][S3] Accept `--manifest PATH` and `--manifest -` alongside globs so `fd … | dredge run --manifest -` is deterministic and Unix-composable (`src/dredge/cli.py:44-76`, `src/dredge/engine.py:22-40`).
- TBEST-14 [PRACTICE][S3] Ship `py.typed` and exported runner, event, ledger, and world protocols so integrations consume a strict library boundary rather than scraping Typer output (`src/dredge/`, `src/dredge/engine.py:12-19`).

# First PR

1. Add canonical `LICENSE`, complete package metadata, `[Unreleased]`, `.python-version`, and missing ignore patterns.
2. Add the missing `examples/openwiki-prompt.txt` and an example-reference validation test.
3. Introduce `ConfigError`, known-key/table validation, and total parsers for strings, positive integers, string lists, integer lists, rewrites, and empty environment values.
4. Validate that runner argv contains an exact `{prompt}` element and that rewrite mappings have nonempty sides.
5. Make default `ledger_hint` derive from the resolved ledger path.
6. Add explicit UTF-8 I/O and BOM-tolerant ledger reading.
7. Detect root-path corruption and post-rewrite collisions during manifest enumeration; enable recursive globs.
8. Add typed `RetryPolicy` values for initial, bisection, and final attempts; remove trailing pause.
9. Add final fixpoint reconciliation and return complete/incomplete status from the engine.
10. Normalize configuration, filesystem, subprocess, timeout, and SIGINT failures into concise stderr diagnostics with documented exit codes.
11. Add config, malformed-ledger, real-bisection, regression, rewrite-collision, interruption, and `CliRunner` tests.
12. Add Ruff, strict Pyright, pytest strictness, pytest-cov, and matching locked development dependencies.
13. Add pre-commit and a SHA-pinned uv-native CI workflow for lock, lint, format, type, tests, examples, build, and wheel smoke checks.
14. Rewrite README sections for ledger grammar, dispositions, configuration tiers, runner semantics, concurrency, guarantees, streams, and exit codes.
15. Add `CONTRIBUTING.md`, `SECURITY.md`, issue/PR templates, DCO policy, and protected tag-driven Trusted Publishing.