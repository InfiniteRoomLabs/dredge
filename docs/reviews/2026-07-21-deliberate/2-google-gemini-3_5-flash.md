# Round 5 Peer Review Deliberation: `dredge`

As the staff-level Python/CLI/typed-design reviewer, I have evaluated all surviving peer analyses. Below is the final deliberation, beginning with the contested and refuted peer claims, followed by the fully consolidated, sharpened, and prioritized technical review spanning all 10 topics.

---

## Part 1: Contested and Refuted Peer Claims (CONTEST)

Upon exhaustive, line-by-line verification against the `dredge` codebase, the following peer claims are refuted and have been corrected or dropped:

1. **DISPUTED(Analysis 1 REPO-3 / Analysis 3 REPO-11):** The claim that the local virtual environment `.venv/` is partially untracked or checked in is incorrect. Line 1 of `.gitignore` explicitly ignores `.venv/`. Its physical presence in the workspace is expected.
2. **DISPUTED(Analysis 3 IDIOM-10):** Suggesting that step-slicing `todo[i : i + batch_size]` at `src/dredge/engine.py:137-138` is a correctness defect because it doesn't use `itertools.batched` is incorrect. Step-slicing is simple, robust, works perfectly, and carries zero operational risk. Transitioning to `itertools.batched` is an S3 style modernization, not a defect.
3. **DISPUTED(Analysis 3 IDIOM-9):** Suggesting that prompt-token replacement at `src/dredge/engine.py:94-102` should use standard `str.format()` or `string.Formatter` is a severe misreading of the domain. AI prompts and code paths inside the corpus are highly likely to contain literal braces `{` and `}` (as pinned by tests in `tests/test_engine.py:72-78`). Standard formatters would parse these as placeholders and throw a `KeyError`. Using token-level `.replace()` (or a custom delimiter `string.Template`) is the correct architectural decision.
4. **DISPUTED(Analysis 2 IDIOM-8):** Suggesting that Click's `Context.get_parameter_source()` can replace dredge's custom config layering is incorrect. Click only tracks CLI options, but 8 out of 10 configuration keys are not CLI options, and environment/TOML tiers cannot be parsed by Click. Custom layering is necessary, and Click is no substitute.
5. **DISPUTED(Analysis 1 ARCH-1):** The claim that parallel sweeps are "impossible" or "structurally broken" is overstated. Under POSIX `O_APPEND` file semantics, concurrent ledger writes are atomic. The true gap is the lack of a coordination protocol (e.g., file locks) to prevent concurrent instances from executing duplicate work or racing over `unprocessable.txt`.
6. **DISPUTED(Analysis 3 ENFORCE-11):** Demanding Ruff `D` docstrings on all private helper methods is overly noisy for a small 400-line CLI; docstrings should be selectively enforced on public boundaries.
7. **DISPUTED(Analysis 1 REPO-7 / Analysis 2 REPO-12):** Claiming that the OpenWiki attribution in `README.md:27` is a defect because it differs from the Docker image name `deathnerd/openwiki:latest` is incorrect. The upstream project link and the specific container registry tag can both be valid.
8. **DISPUTED(Analysis 2 ARCH-12 / Analysis 3 ARCH-12):** The assertion that list-backed front-pop operations (`queue.pop(0)` and `queue.insert(0)`) at `src/dredge/engine.py:141,150-151` present an S1/S2 architectural risk due to $O(N^2)$ queue movement is incorrect. For a typical corpus, the queue length never exceeds 50 items. A list pop of this size takes less than 1 microsecond, whereas runner executions and backoff sleeps take minutes to hours. This is an S3 cosmetic polish/style modernization, not an S1/S2 defect.

---

## Part 2: Updated, Consolidated, and Sharpened Review

### ARCH - Architecture

- ARCH-1 [DEFECT][S1] `run` exits 0 with items pending if they are not marked unprocessable (e.g., due to mid-sweep ledger regression): success keys solely off `unprocessable` (`src/dredge/cli.py:84-88`), so any failure to cover manifest items that didn't get deferred or written to `unprocessable` goes unreported — exit 1 on final non-empty `pending` fixpoint.
- ARCH-2 [DEFECT][S1] Backoff compounds across bisection levels and the deferred round: one poison item in a 40-item batch pays the full retry schedule per `_attempt` (`src/dredge/engine.py:120-130`) at each bisection level and again in the final retry, which wastes hours of sleep time — bisections and final retries must use a truncated retry schedule.
- ARCH-3 [DEFECT][S2] `_run_batch`'s return value and computed progress (`before`, `after`, `ok`) are dead code: discarded at `src/dredge/engine.py:122` while `_attempt` re-parses the ledger to track progress, causing two redundant ledger I/O operations per attempt (`src/dredge/engine.py:104-113`).
- ARCH-4 [GAP][S2] Concurrent sweeps lack coordination: queue materialized once (`src/dredge/engine.py:136-138`), progress credited to any ledger writer, `unprocessable.txt` write/unlink race (`src/dredge/cli.py:83-89`) — implement a ledger-scoped advisory file lock. DISPUTED(Analysis 1 ARCH-1): parallel sweeps are not "impossible" due to filesystem corruption (POSIX `O_APPEND` makes writes atomic), but rather logically uncoordinated.
- ARCH-5 [GAP][S2] Runner seam is a bare `Callable[[list[str]], bool]` (`src/dredge/engine.py:81`), discarding runner exit codes, timeout status, stderr, and run durations — replace with a typed `Runner` protocol returning a rich `RunResult`.
- ARCH-6 [GAP][S2] `Sweep` fuses pure planning, retry/bisect scheduling, and side effects (subprocess run, sleep, printing) in one class (`src/dredge/engine.py:132-166`) — extract a pure generator `plan_batches()` and outcome-fold state machine.
- ARCH-7 [GAP][S2] Engine narrates progress directly to stdout using `print` (`src/dredge/engine.py:83,121,128,149,153`), mixing operational logs with stdout records — emit strongly-typed events to a CLI-owned reporter stream.
- ARCH-8 [DEFECT][S3] DISPUTED(Analysis 2 ARCH-11): `SweepResult.deferred` records a historical "ever deferred" state; if a deferred item's final retry succeeds, it remains listed in `deferred` (`src/dredge/engine.py:154,157-160`) — make terminal outcomes disjoint or rename to `ever_deferred`.
- ARCH-9 [DEFECT][S3] Batch IDs restart at `batch-000` on resumed runs because they are generated positionally over the remaining `todo` list (`src/dredge/engine.py:137-138`), preventing run-to-run log correlation — use stable identifiers like manifest offsets.
- ARCH-10 [DEFECT][S3] DISPUTED(Analysis 2 ARCH-10): `unprocessable.txt` is disposable derived output and never participates in `pending`, but `Config` mixes configuration with metadata by storing `provenance: dict[str, str]` inline (`src/dredge/config.py:48`), forcing custom-case exclusions at `src/dredge/cli.py:124`.
- ARCH-11 [GAP][S3] `state_dir` is defined as a directory (`src/dredge/config.py:47`) but is configured and resolved for exactly one file (`src/dredge/cli.py:83`), making the "ledger is the only state" claim slightly untruthful — document `state_dir`'s purpose or write the report to stdout.
- ARCH-12 [PRACTICE][S3] DISPUTED(Analysis 2 ARCH-12 / Analysis 3 ARCH-12): Front-pop quadratic complexity in bisection list operations (`queue.pop(0)`) is an S3 cosmetic style issue rather than an S2 architectural risk, as bisection queues at defaults never exceed 50 items.

### REPO - Repository Practices

- REPO-1 [DEFECT][S1] `README.md:37-39` claims the project is licensed under "MIT", but no `LICENSE` file exists in the repository root and no package license metadata is declared in `pyproject.toml:1-11`, leaving downstream use legally ambiguous.
- REPO-2 [DEFECT][S2] `CHANGELOG.md:8` declares release `0.1.0` but `git tag` is empty, violating the parent organization's tag-driven publish convention — tag `v0.1.0` at the release commit.
- REPO-3 [DEFECT][S2] The complete real-world example resolves `prompt_file` but `examples/openwiki-prompt.txt` is missing (`examples/openwiki.toml:14`), crashing copy-paste runs with `FileNotFoundError` (`src/dredge/config.py:52`).
- REPO-4 [DEFECT][S2] Docker mount mismatch in `examples/openwiki.toml:9,13,20`: mounts `/home/you/.openwiki` to `/home/openwiki/.openwiki` but sets `ledger_hint` to `/coverage-ledger.md`, preventing containerized agents from locating the ledger. DISPUTED(Analysis 1 REPO-4): an absolute `/coverage-ledger.md` is not plausibly wiki-root-relative without an undocumented image symlink.
- REPO-5 [GAP][S2] Package metadata in `pyproject.toml:1-11` is missing `license`, `readme`, `classifiers`, `keywords`, and `project.urls` tables, making published packages metadata-blind on package indexes.
- REPO-6 [GAP][S2] Package lacks `src/dredge/py.typed` PEP 561 marker, preventing external type checkers from utilizing inline type annotations.
- REPO-7 [GAP][S3] `README.md:34` recommends installation from a floating default branch (`git+https://...`), violating reproducibility — pin to a tag or publish to PyPI. DISPUTED(Analysis 1 REPO-7 / Analysis 2 REPO-12): Claiming that the OpenWiki attribution in `README.md:27` is a defect because it differs from the Docker image name `deathnerd/openwiki:latest` is incorrect. The upstream project link and the specific container registry tag can both be valid.
- REPO-8 [DEFECT][S3] Version is triplicated across `pyproject.toml:3`, `src/dredge/__init__.py:3`, and `CHANGELOG.md:8` — derive the package version dynamically at runtime using `importlib.metadata.version`.
- REPO-9 [GAP][S3] Keep-a-Changelog usage lacks `[Unreleased]` and comparison links, leaving subsequent changes without a disciplined landing section (`CHANGELOG.md:1-15`).
- REPO-10 [GAP][S3] `.gitignore` omits `dist/`, `build/`, `.coverage*`, `htmlcov/`, `.ruff_cache/`, `.mypy_cache/`, and `.pyright/`, all produced by standard development workflows.
- REPO-11 [GAP][S3] The Python floor is 3.12 (`pyproject.toml:8`) but repository artifacts only evidence a 3.14 local virtual environment (`.venv/pyvenv.cfg`); pin `.python-version` to 3.12 and test newer interpreters in CI. DISPUTED(Analysis 1 REPO-3 / Analysis 3 REPO-11): The claim that the virtual environment `.venv/` is partially untracked or checked in is a misreading of the repository's configuration. Line 1 of `.gitignore` explicitly ignores `.venv/`.

### IDIOM - Library/Framework Usage

- IDIOM-1 [DEFECT][S1] TOML parsing cast error: calling `resolve("backoff", lambda v: [int(x) for x in v], ...)` (`src/dredge/config.py:112`) on an integer from TOML (e.g., `backoff = 300`) throws a raw `TypeError: 'int' object is not iterable`, rather than a clean configuration error.
- IDIOM-2 [DEFECT][S1] String TOML values silently explode into character lists: calling `resolve("corpus_globs", list, ...)` or `resolve("runner", list, ...)` (`src/dredge/config.py:105-107`) on a scalar string (e.g. `corpus_globs = "/data/*"`) results in a list of characters `['/', 'd', 'a', ...]`, rather than a validation failure.
- IDIOM-3 [DEFECT][S2] `glob.glob(g)` omits `recursive=True` (`src/dredge/engine.py:32`), preventing `**` globs from matching recursively down the directory tree — use `glob.glob(g, recursive=True)`.
- IDIOM-4 [DEFECT][S2] Prompt, TOML, ledger, and report I/O use locale defaults; specify UTF-8 explicitly and choose `utf-8-sig` only for ledger reads if BOM tolerance is intended (`src/dredge/config.py:52,82`, `src/dredge/engine.py:48`, `src/dredge/cli.py:86`).
- IDIOM-5 [GAP][S2] `subprocess.run()` lacks a timeout; add an optional `batch_timeout` config key and call `subprocess.run(..., timeout=...)` (`src/dredge/engine.py:91-92`).
- IDIOM-6 [DEFECT][S2] TOML root shape is unchecked: `[dredge]` can be a scalar/list and unknown keys are silently ignored, turning typos into defaults; validate `dict[str, object]` and reject unsupported keys before resolution (`src/dredge/config.py:80-100`).
- IDIOM-7 [DEFECT][S3] The comma parser neither trims whitespace nor rejects empty elements, so `DREDGE_CORPUS_GLOBS="a, b"` silently creates `" b"`; replace the E731 lambda with a validating function (`src/dredge/config.py:104-112`).
- IDIOM-8 [PRACTICE][S3] Modernize Typer option declarations to `Annotated[Path | None, typer.Option(...)]` to avoid legacy positional options (`src/dredge/cli.py:6,19,44,73`).
- IDIOM-9 [PRACTICE][S2] Hand-written layering is justified because provenance and TOML-relative paths are first-class; Pydantic Settings or Click `ParameterSource` would still need custom sources and provenance, so document rather than replace this design (`src/dredge/config.py:72-123`). DISPUTED(Analysis 2 IDIOM-8): Click's `Context.get_parameter_source()` is not a viable substitute because it cannot parse TOML files or map non-CLI environment variables.
- IDIOM-10 [PRACTICE][S3] Step slicing `todo[i : i + batch_size]` at `src/dredge/engine.py:137-138` is correct and robust, but standardizing to `itertools.batched` is a nice Python 3.12 style modernization. DISPUTED(Analysis 3 IDIOM-10): step slicing is not a correctness defect and carries no operational risk.
- IDIOM-11 [PRACTICE][S3] Sequential prompt replacement can expand `{items}` introduced by `ledger_hint`; use one-pass token-regex substitution while preserving literal braces (`src/dredge/engine.py:94-102`). DISPUTED(Analysis 3 IDIOM-9): standard `str.format()` or `string.Formatter` would fail on legitimate braces in prompts/code paths; token replacement is correct.
- IDIOM-12 [PRACTICE][S3] Ledger parsing correctly avoids a markdown-parser dependency, but the grammar deserves a named module-level regex with a docstring, not inline slicing (`src/dredge/engine.py:50-55`).

### CICD - CI/CD Stance

- CICD-1 [GAP][S1] No CI configuration exists (`.github/workflows/`); implement a base gate running `uv sync --locked` and `uv run pytest` on push/PR (`pyproject.toml:24-25`).
- CICD-2 [GAP][S1] Add blocking `uv run ruff check .` and `uv run ruff format --check .` to enforce standards and reject style or import drift in CI.
- CICD-3 [GAP][S1] Add blocking `uv run pyright` in strict mode over `src` and `tests` to catch untyped arguments and return types.
- CICD-4 [GAP][S2] Matrix-test across Python 3.12, 3.13, and 3.14 to ensure compatibility with the advertised `>=3.12` floor (`pyproject.toml:8`).
- CICD-5 [GAP][S2] Release automation on tag `v*`: run `uv build`, verify package metadata, install the built wheel in a clean virtual environment, and smoke-test `dredge --help`.
- CICD-6 [GAP][S2] Publish built artifacts to PyPI via Trusted Publishing OIDC with a scoped release environment (`pyproject.toml:13-22`).
- CICD-7 [GAP][S2] Enforce the organization's 7-day dependency gate by asserting that `uv.lock` retains `exclude-newer-span = "P7D"` and setting `UV_EXCLUDE_NEWER` on update workflows.
- CICD-8 [GAP][S2] Configure code coverage tracking with `pytest-cov` to fail if coverage falls below 90%, highlighting untested `config.py` and `cli.py` files.
- CICD-9 [GAP][S2] Add an example-validation job that loads and parses `examples/openwiki.toml` in CI to ensure its path references and structure are valid without launching Docker.
- CICD-10 [GAP][S3] Use `astral-sh/setup-uv` pinned by full commit SHA with `enable-cache: true` on GitHub Actions to keep CI run times sub-30 seconds.
- CICD-11 [GAP][S3] Declare POSIX-only support and matrix-test Linux and macOS only, explicitly avoiding Windows CI testing due to hardcoded `/` path separators in rewrite logic (`src/dredge/engine.py:33-38`). DISPUTED(Analysis 2 CICD-10): Windows CI matrix is not required since Windows is an unsupported platform.

### COVER - Test Coverage and Gaps

- COVER-1 [GAP][S1] `src/dredge/config.py` has literally zero tests, leaving precedence, environment casts, TOML-relative resolution, validation branches, and missing-config-file paths completely unexercised.
- COVER-2 [GAP][S1] `src/dredge/cli.py` has zero tests: no test exercises `CliRunner` for help menus, command-line arguments, stdout/stderr streams, or exit codes 0/1/2.
- COVER-3 [GAP][S1] Bisection logic in `engine.py:147-151` is completely untested! `test_exit_zero_without_ledger_growth_is_failure_then_bisected` is named "then_bisected" but actually writes three out of four items to the ledger on attempt 1, leaving only one pending item (`["/c/poison"]`) for attempt 2 and subsequent failure, which bypasses the `len(remaining) > 1` bisection check entirely and goes straight to deferring. No other test triggers bisection.
- COVER-4 [GAP][S1] Path with trailing/leading spaces triggers infinite retry loop: because `covered()` strips trailing and leading spaces from ledger paths (`engine.py:53`) but `enumerate_corpus` does not, `pending()` will always evaluate `/data/foo ` as not in `done` (which has the stripped `"/data/foo"`), but no test exercises this whitespace discrepancy.
- COVER-5 [GAP][S1] Ledger-regression remains untested: no test verifies that an already-covered item disappearing from the ledger mid-run triggers a failure or final incompleteness.
- COVER-6 [GAP][S2] Ledger parsing of non-ledger lines is untested: the example ledger resides inside a live wiki where arbitrary markdown prose lines might start with `- ` and contain ` - `, causing false positives in `covered()` (`src/dredge/engine.py:50-55`).
- COVER-7 [GAP][S2] Backoff sleeps and attempts are untested: the tests force `backoff = [0]` (`tests/test_engine.py:12`) and never assert that the proper backoff wait times are passed to the sleep callable.
- COVER-8 [GAP][S2] Test `KeyboardInterrupt` mid-batch or mid-backoff sleep to verify clean interruptions, partial ledger persistence, and resume instructions.
- COVER-9 [GAP][S3] Large corpus/prompt scale test: no test asserts behavior under very large path counts, which can exceed operating system command-line limits (`E2BIG`) when passed as a single `{prompt}` argument.
- COVER-10 [GAP][S3] Property-based round-trip: no Hypothesis tests assert that any arbitrary path string successfully round-trips through `append_ledger` and `covered()`.
- COVER-11 [GAP][S3] Unicode normalization behavior: no test checks whether NFD paths in the corpus match NFC paths in the ledger or vice-versa.
- COVER-12 [GAP][S3] DISPUTED(Analysis 3 COVER-4): a UTF-8 BOM ledger does not "crash" the sweep; it simply fails the `startswith("- ")` check at `engine.py:50` and silently skips the first line, which eventually results in retry/bisection on that item. Pin this behavior via a test.

### ENFORCE - Enforcement of Standards

- ENFORCE-1 [GAP][S1] Add `[tool.ruff] target-version = "py312"` and `lint.select = ["E","F","W","I","UP","B","SIM","RET","PTH","PERF","RUF"]` with a scoped `B008` override for Typer defaults to enforce standard code-quality patterns.
- ENFORCE-2 [GAP][S1] Add `[tool.pyright] typeCheckingMode = "strict"` and `pythonVersion = "3.12"` to prevent type drift, untyped casts, and unchecked callbacks (`src/dredge/config.py:72-113`).
- ENFORCE-3 [GAP][S1] Configure `[tool.pytest.ini_options] testpaths = ["tests"]`, `addopts = "-ra --strict-config --strict-markers"`, and `filterwarnings = ["error"]` to catch Typer or dependency warnings early.
- ENFORCE-4 [GAP][S2] Configure code coverage enforcement in `pyproject.toml` using `fail_under = 90` with branch measurement.
- ENFORCE-5 [GAP][S2] Add pre-commit hooks for `ruff check --fix`, `ruff format`, `uv lock --check`, `check-toml`, `trailing-whitespace`, and `end-of-file-fixer` in `.pre-commit-config.yaml`.
- ENFORCE-6 [GAP][S2] Add ruff and pyright to `[dependency-groups].dev` in `pyproject.toml` so all contributors use matching, pinned linters and type checkers.
- ENFORCE-7 [GAP][S2] Implement an architectural linting test (e.g., using `import-linter` or a unit test checking `sys.modules`) to forbid `src/dredge/engine.py` from importing `typer` or `src/dredge/cli.py`.
- ENFORCE-8 [GAP][S2] Validate packaging with `validate-pyproject` and smoke-test the built wheel to ensure the entrypoint `dredge` is runnable.
- ENFORCE-9 [GAP][S2] Add release consistency validation in CI to ensure the tag version matches `pyproject.toml:3`, `src/dredge/__init__.py:3`, and the latest `CHANGELOG.md` heading.
- ENFORCE-10 [GAP][S3] Implement example verification that dynamically parses `examples/openwiki.toml` and validates that its target paths exist.
- ENFORCE-11 [PRACTICE][S3] Enforce UTF-8/LF with `.editorconfig` to align files across environments. DISPUTED(Analysis 3 ENFORCE-11): forcing Ruff docstring rules `D` on all private helper methods is overly noisy; selectively enforce docstrings on public API entry points.
- ENFORCE-12 [PRACTICE][S3] DISPUTED(Analysis 3 ENFORCE-9): `deptry` has low current yield for a single runtime dependency; prioritizing lock file and import-boundary checks is a better use of resources.

### DOCS - Documentation

- DOCS-1 [DEFECT][S1] The ledger grammar is barely documented (`README.md:9`), omitting essential parse details such as the `- ` prefix, the rightmost `" - "` split, the rstripping of trailing slashes, and the silent skipping of non-matching lines (`src/dredge/engine.py:43-56`).
- DOCS-2 [DEFECT][S2] Disposition semantics are completely undefined while any nonempty disposition counts as covered, meaning `- /path - failed` permanently skips the path; document whether any write indicates terminal processing or reserve failure dispositions (`src/dredge/config.py:26`, `src/dredge/engine.py:50-55`).
- DOCS-3 [DEFECT][S2] README claims full flag precedence for all values (`README.md:27`), but only `corpus_globs` and `batch_size` have CLI flags (`src/dredge/cli.py:44,70-76`); correct the document to specify which keys are CLI-configurable.
- DOCS-4 [GAP][S2] Add a comprehensive configuration reference documenting all ten config keys, their TOML types, defaults, corresponding `$DREDGE_*` environment variable names, and relative path resolution rules (`src/dredge/config.py:36-48`).
- DOCS-5 [GAP][S2] Document the CLI exit-code contract: 0 for complete success, 1 for incomplete sweeps/unprocessable items, and 2 for configuration or initialization errors (`src/dredge/cli.py:24-33,81-103`).
- DOCS-6 [DEFECT][S2] `plan` and `status` commands produce identical outputs (`src/dredge/cli.py:57-66`) despite promising different functionality; make `plan` show a preview of generated batches/rendered prompts or merge the commands.
- DOCS-7 [GAP][S2] Document runner execution constraints: arguments are passed directly (no shell expansion), `{prompt}` must be a whole argv element, and child processes inherit stdin/stdout/stderr (`src/dredge/engine.py:91-109`).
- DOCS-8 [DEFECT][S2] Qualify "coverage-guaranteed" in the README as conditional on exclusive ledger ownership, honest agent writes, stable corpus manifests, and final fixpoint verification (`README.md:3-11`).
- DOCS-9 [DEFECT][S2] The "complete" OpenWiki example is unrunnable: it references a missing `openwiki-prompt.txt` and points the agent at `/coverage-ledger.md` which maps to container root (`examples/openwiki.toml:9-22`).
- DOCS-10 [DEFECT][S3] `--batch-size` CLI option lacks any help text or default range explanation (`src/dredge/cli.py:73`).
- DOCS-11 [GAP][S3] Document the concurrency stance ("one dredge process per ledger") and the role of `unprocessable.txt` in the model section of the README (`README.md:7-12`).
- DOCS-12 [GAP][S3] Generate and snapshot CLI reference documentation in Markdown to ensure that `--help` descriptions and docs never diverge (`src/dredge/cli.py:13-22`).

### QUALITY - Code Quality and Contracts

- QUALITY-1 [DEFECT][S1] Missing `{prompt}` validation: loading a runner without `{prompt}` (`src/dredge/config.py:60-69`) executes the command promptless and consumes the full backoff and bisection schedule before failing, rather than fast-failing with exit code 2.
- QUALITY-2 [DEFECT][S1] Environment-variable cast failures (e.g., `DREDGE_BATCH_SIZE="invalid"` or `DREDGE_PAUSE="invalid"`) raise a raw `ValueError` from `int()` instead of `ConfigError` (`src/dredge/config.py:111-113`), leading to python tracebacks with exit code 1.
- QUALITY-3 [DEFECT][S2] Uncaught file and process exceptions: invalid TOML (`src/dredge/config.py:82`), missing `prompt_file` (`src/dredge/config.py:52`), or missing runner executable (`src/dredge/engine.py:92`) raise tracebacks mid-sweep instead of clean stderr diagnostics with exit code 2.
- QUALITY-4 [DEFECT][S2] Stream discipline violation: `dredge verify` prints success summaries to stdout (`src/dredge/cli.py:103`), polluting stdout and breaking downstream pipes like `dredge verify | xargs ...`; route all non-record diagnostics to stderr.
- QUALITY-5 [DEFECT][S2] Empty env-vars treated as configured: setting `DREDGE_PROMPT_FILE=""` records its provenance as `"env"` and resolves to `None` with errors during sweep, instead of treating empty as unset (`src/dredge/config.py:56-57,93-96`).
- QUALITY-6 [DEFECT][S2] Rewrite validation allows empty host or agent prefixes (e.g., `rewrites = ["="]`), causing root-level prefix replacements on any path (`src/dredge/config.py:67-69`).
- QUALITY-7 [DEFECT][S2] Unknown keys in the `[dredge]` TOML section are silently ignored (`src/dredge/config.py:82,98`), turning typos (e.g. `batchsize = 20`) into silent fallback defaults with no feedback.
- QUALITY-8 [DEFECT][S2] Out-of-the-box defaults are mutually incoherent: `ledger` defaults to `"coverage-ledger.md"` (cwd-relative) while `ledger_hint` defaults to `"/coverage-ledger.md"` (absolute root), guaranteeing a failed run with zero-config defaults (`src/dredge/config.py:41-42`).
- QUALITY-9 [DEFECT][S2] `orphans` command cannot audit an entirely deleted or moved corpus: `_manifest` exits with code 2 if the corpus globs expand to an empty set (`src/dredge/cli.py:38-41,106-112`), which is the exact scenario where auditing orphans is most critical.
- QUALITY-10 [DEFECT][S3] Missing `--version` CLI flag to inspect the installed package version (`src/dredge/cli.py:13-21`).
- QUALITY-11 [DEFECT][S3] No SIGINT/Ctrl-C handling: interrupting a sweep during a long backoff sleep or runner execution dumps a raw traceback instead of a clean "interrupted; sweep can be resumed" diagnostic (`src/dredge/engine.py:87,129`).
- QUALITY-12 [DEFECT][S3] Wasteful trailing sleep: `self.sleep(self.cfg.pause)` executes after processing the final batch and after bisections are scheduled (`src/dredge/engine.py:155`), adding unnecessary delay before termination.
- QUALITY-13 [DEFECT][S3] `covered()` silently drops unparseable lines (`src/dredge/engine.py:48-56`); return diagnostics so that `verify` can report corrupt ledger lines.
- QUALITY-14 [DEFECT][S3] `Config` and `SweepResult` are mutable and built via `setattr` loop (`src/dredge/config.py:90-101`); using frozen slotted dataclasses would make resolved config structurally immutable.

### CONTRIB - Contributing Workflows

- CONTRIB-1 [GAP][S1] Missing `LICENSE` file in the repo root prevents any legal framework for contributions under the MIT license claimed by the README (`README.md:37-39`).
- CONTRIB-2 [GAP][S2] No `CONTRIBUTING.md` exists: developers have no documentation on setting up the workspace (`uv sync`), running tests (`uv run pytest`), or executing the linters/type checkers.
- CONTRIB-3 [GAP][S2] No `SECURITY.md` file: the tool executes arbitrary commands defined in TOML/env (`src/dredge/engine.py:91-102`), so a statement defining the trust model and a private vulnerability report path is necessary.
- CONTRIB-4 [GAP][S2] State a clear DCO (Developer Certificate of Origin) sign-off policy for all inbound PR commits to prevent downstream license taint.
- CONTRIB-5 [GAP][S3] Define a ledger-format compatibility policy: since `covered()` parses persistent ledger files, any changes to the parse grammar must be explicitly documented and version-gated.
- CONTRIB-6 [GAP][S3] No Bug Report issue template; add a template that requests a redacted `dredge config` output and ledger diagnostics while explicitly warning against sharing raw runner command tokens.
- CONTRIB-7 [GAP][S3] No Pull Request template; add a lightweight PR checklist verifying that local pytest was run and the CHANGELOG has been updated.
- CONTRIB-8 [GAP][S3] No compatibility policy naming what public interfaces are SemVer-stable (such as CLI verbs, TOML keys, environment variables, or the ledger format).
- CONTRIB-9 [GAP][S3] Document the dual-remote git mirror setup: explain that GitHub is the canonical public upstream repository and the Gitea instance is a homelab mirror (`.git/config:6-14`).
- CONTRIB-10 [GAP][S3] No maintainer response contract; define a realistic response expectation for PR reviews and issues to prevent maintainer burnout.
- CONTRIB-11 [PRACTICE][S3] Seed scoped "good first issues" based on this review, such as adding the `--version` flag, adding `--batch-size` help, or catching TOML-parsing `ValueError`s.

### TBEST - Practices T<? in Best<composeable+testable+knowable+strictly-typed code&architecture>>

- TBEST-1 [PRACTICE][S1] Parse, do not validate/coerce: replace blind `setattr` coercion in `load()` with per-type total parsers (e.g., `parse_positive_int`, `parse_int_list`, `parse_str_list`) that validate shapes and raise explicit `ConfigError` with the config key and tier (`src/dredge/config.py:87-102`).
- TBEST-2 [PRACTICE][S1] Isolate side-effects: replace direct dependencies on `subprocess.run`, `time.sleep`, `print`, and file reads inside `Sweep` with a clean `World` dependency injection protocol, making the entire retry/bisect machine pure and deterministic (`src/dredge/engine.py:77-89`).
- TBEST-3 [PRACTICE][S1] Encode completion as a final fixpoint over `manifest - ledger` returning a `Complete` or `Incomplete` variant, making the ARCH-1 silent success bug structurally impossible to represent.
- TBEST-4 [PRACTICE][S2] Establish a strong type boundary between host paths and agent paths with `NewType("HostPath", str)` and `NewType("AgentPath", str)` so that path conversions only happen at the `enumerate_corpus` boundary.
- TBEST-5 [PRACTICE][S2] Elevate the ledger to a strongly-typed value object with total parsing: `Ledger.parse(text: str) -> tuple[frozenset[AgentPath], list[ParseError]]` to provide rich diagnostics for corrupt ledger lines.
- TBEST-6 [PRACTICE][S2] Return a closed sum variant from batch execution: `_run_batch` should return `FullyCovered | Progressed(remaining) | Stalled` to allow bisection and retry schedulers to make optimal decisions on disjoint outcomes.
- TBEST-7 [PRACTICE][S2] Express scheduling as a pure transition over `QueueState` (`next_action(state) -> RunBatch | Bisect | Defer | Done`), utilizing a dedicated `RetryPolicy` configuration for initial, bisections, and final retries.
- TBEST-8 [PRACTICE][S2] Parse path rewrites once as structured `Rewrite(host_prefix, agent_prefix)` objects with nonempty, root-aware invariants instead of splitting strings at each loop iteration (`src/dredge/config.py:39,67-69`, `src/dredge/engine.py:29-38`).
- TBEST-9 [PRACTICE][S2] Ensure configuration and sweep result structures are structurally immutable by applying `@dataclass(frozen=True, slots=True)` after validation.
- TBEST-10 [PRACTICE][S2] Implement property-based testing using Hypothesis to assert invariants over random directories, Unicode path strings, and artificial bisections.
- TBEST-11 [PRACTICE][S3] Emit structured engine events (like `BatchStarted`, `Bisected`, `Deferred`) instead of stdout strings, allowing clean CLI rendering (stderr / JSON / quiet) and future parallel runners.
- TBEST-12 [PRACTICE][S3] Support stdin composability: accept `-` as a glob or a new `--manifest` flag to read a file list directly, allowing `dredge` to compose cleanly with Unix utilities like `fd` or `find`.
- TBEST-13 [PRACTICE][S3] Ship the library boundary: export clean typed interfaces with a `py.typed` marker so external Python systems can integrate `dredge` as a library with custom runners.