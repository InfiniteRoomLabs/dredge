## 1. ARCH

- ARCH-1 [DEFECT][S1] Queue exhaustion is not completion: `run` exits successfully whenever `unprocessable` is empty even if later ledger regression restores pending items; derive success from one final `pending(manifest, ledger)` fixpoint (`src/dredge/engine.py:162-166`, `src/dredge/cli.py:81-89`).
- ARCH-2 [DEFECT][S1] A poison item receives the full 9,300-second backoff at each bisection depth and again during the purported “retried once” final round; define separate initial, bisect, and one-shot-final `RetryPolicy` values (`src/dredge/engine.py:120-130,145-160`, `README.md:11`).
- ARCH-3 [DEFECT][S2] `_run_batch()` computes and returns progress but `_attempt()` discards the verdict and rereads the ledger, while `ok and before == 0` is unreachable after `_attempt()`’s empty guard; consume a typed outcome or make the method effect-only (`src/dredge/engine.py:104-123`).
- ARCH-4 [GAP][S2] Concurrent sweeps can duplicate work, credit each other’s writes, and race over `unprocessable.txt`; enforce one active sweep per ledger with an advisory lock or explicitly reject concurrent ownership (`src/dredge/engine.py:108-160`, `src/dredge/cli.py:83-89`).
- ARCH-5 [GAP][S2] DISPUTED(Analysis 3 ARCH-4): POSIX `O_APPEND` does not establish safety because dredge does not perform or control the agent’s ledger append, and atomic lines would not solve scheduling or report races (`src/dredge/engine.py:91-113`, `src/dredge/cli.py:83-89`).
- ARCH-6 [GAP][S2] `Callable[[list[str]], bool]` erases exit code, signal, timeout, duration, and diagnostics; define `Runner.run(argv: Sequence[str]) -> RunResult` while retaining ledger growth as the success oracle (`src/dredge/engine.py:77-92`).
- ARCH-7 [GAP][S2] `Sweep.run()` interleaves reconciliation, retries, bisection, subprocess effects, sleeping, and reporting; extract pure `plan_batches()` and `transition(state, observation)` functions (`src/dredge/engine.py:115-166`).
- ARCH-8 [GAP][S2] `Sweep` receives the whole mutable CLI `Config` although it uses only runner, prompt, ledger, batching, retry, and pause fields; construct a frozen, engine-focused `SweepPolicy` (`src/dredge/engine.py:77-102`).
- ARCH-9 [GAP][S2] Engine narration is an unstructured string callback defaulting to stdout; emit typed events such as `BatchStarted`, `RetryScheduled`, `Bisected`, and `Deferred` for CLI-owned rendering (`src/dredge/engine.py:83,121-159`).
- ARCH-10 [DEFECT][S3] `SweepResult.deferred` is historical rather than terminal—items remain listed after a successful final retry; rename it `ever_deferred` or model mutually exclusive terminal outcomes (`src/dredge/engine.py:64-68,153-160`).
- ARCH-11 [DEFECT][S3] Batch IDs restart at `batch-000` over each resumed pending list, preventing stable log correlation; derive IDs from manifest ranges or a content hash (`src/dredge/engine.py:134-138`).
- ARCH-12 [GAP][S3] `Config` embeds provenance and forces a special `config` pseudo-key whose path is printed as both value and tier; return `ResolvedConfig` and `Provenance` separately (`src/dredge/config.py:36-48,84-102`, `src/dredge/cli.py:123-125`).
- ARCH-13 [GAP][S3] The manifest is a startup snapshot, so files added during a run are outside the claimed sweep; document snapshot semantics or support explicit reconciliation epochs (`src/dredge/engine.py:132-138`, `README.md:3-10`).

## 2. REPO

- REPO-1 [DEFECT][S1] `README.md` declares MIT but no `LICENSE` or package license metadata exists; add the canonical MIT text plus `license = "MIT"` and `license-files = ["LICENSE"]` (`README.md:37-39`, `pyproject.toml:1-11`, repository root).
- REPO-2 [DEFECT][S2] `CHANGELOG.md` declares 0.1.0 while no loose or packed Git tag exists; under tag-driven publishing, release from a protected `v0.1.0` tag only after the release workflow lands (`CHANGELOG.md:8-15`, `.git/refs/tags/`).
- REPO-3 [DEFECT][S2] The advertised “complete real-world setup” references absent `examples/openwiki-prompt.txt`, causing first prompt rendering to raise `FileNotFoundError`; DISPUTED(Analysis 1 REPO-7): upstream project and image names can legitimately differ—the missing asset is the proven defect (`README.md:27`, `examples/openwiki.toml:14`, `src/dredge/config.py:50-53`).
- REPO-4 [DEFECT][S2] The example labels `/coverage-ledger.md` as the path seen by the agent but mounts the ledger beneath `/home/openwiki/.openwiki/wiki/coverage-ledger.md`; absent a documented symlink or extra mount, these absolute paths disagree (`examples/openwiki.toml:9,13,20`).
- REPO-5 [GAP][S2] `pyproject.toml` lacks `readme`, classifiers, keywords, and `[project.urls]` for source, issues, changelog, and documentation, leaving published metadata incomplete (`pyproject.toml:1-14`).
- REPO-6 [GAP][S2] The annotated package lacks `src/dredge/py.typed`, so PEP 561 consumers cannot rely on the engine’s inline types (`src/dredge/`, `pyproject.toml:20-22`).
- REPO-7 [DEFECT][S3] Installation tracks a floating Git default branch; publish a versioned package or pin the fallback to `git+...@v0.1.0` (`README.md:31-35`).
- REPO-8 [DEFECT][S3] Version is triplicated across project metadata, runtime code, and changelog; derive runtime version with `importlib.metadata.version("dredge")` and gate tag/changelog agreement (`pyproject.toml:3`, `src/dredge/__init__.py:3`, `CHANGELOG.md:8`).
- REPO-9 [GAP][S3] Keep-a-Changelog usage omits `[Unreleased]` and comparison links, leaving future changes without a disciplined landing section (`CHANGELOG.md:1-15`).
- REPO-10 [GAP][S3] `.gitignore` omits `build/`, `dist/`, `.coverage*`, `htmlcov/`, `.ruff_cache/`, `.mypy_cache/`, and `.pyright/`, all produced by the proposed quality workflow (`.gitignore:1-7`).
- REPO-11 [GAP][S3] Python support starts at 3.12 but no `.python-version` pins that floor for local development; pin 3.12 locally and test 3.12–3.14 in CI (`pyproject.toml:8`, repository root).
- REPO-12 [GAP][S3] Canonical GitHub and Gitea mirror remotes exist but their release/mirroring relationship is undocumented; identify GitHub as canonical and describe mirror synchronization in contribution/release docs (`.git/config:6-14`).

## 3. IDIOM

- IDIOM-1 [DEFECT][S1] Generic `list`/`int` coercion accepts invalid TOML shapes: strings become character lists and booleans become integers; replace with shape-checking `parse_str_list()` and `parse_int_not_bool()` (`src/dredge/config.py:87-112`).
- IDIOM-2 [DEFECT][S2] `backoff = "300"` becomes `[3, 0, 0]`, silently defeating retry policy; require `list[int]`, reject strings/booleans, and report the key and source tier (`src/dredge/config.py:112`).
- IDIOM-3 [DEFECT][S2] `glob.glob(g)` omits `recursive=True`, so conventional `**` patterns do not recursively enumerate the corpus; use `glob.iglob(..., recursive=True)` and document hidden-file behavior (`src/dredge/engine.py:31-32`).
- IDIOM-4 [DEFECT][S2] Prompt, TOML, ledger, and report I/O rely on locale-default encodings; use explicit UTF-8 and decide whether ledger reads accept BOM via `utf-8-sig` (`src/dredge/config.py:52,82`, `src/dredge/engine.py:48`, `src/dredge/cli.py:86`).
- IDIOM-5 [GAP][S2] `subprocess.run()` has no timeout, allowing one hung agent to block reconciliation forever; add `batch_timeout: float | None` and handle `subprocess.TimeoutExpired` (`src/dredge/engine.py:91-92`).
- IDIOM-6 [DEFECT][S2] TOML root/table shapes and unknown `[dredge]` keys are unchecked, so malformed tables or typos either crash indirectly or silently fall back to defaults; validate `dict[str, object]` and a known-key set (`src/dredge/config.py:80-100`).
- IDIOM-7 [DEFECT][S3] The comma parser is an E731 lambda that neither trims whitespace nor rejects empty elements; replace it with a named total parser (`src/dredge/config.py:104-112`).
- IDIOM-8 [PRACTICE][S3] Modernize Typer declarations to `Annotated[Path | None, typer.Option(...)]`; DISPUTED(Analysis 3 IDIOM-6): the current syntax is legacy, not evidence of shared option-state corruption (`src/dredge/cli.py:6,19,44,73`).
- IDIOM-9 [PRACTICE][S2] The custom four-tier resolver is justified because Pydantic Settings and Click `ParameterSource` do not natively provide this per-key provenance plus TOML-relative paths; document that decision rather than replacing it reflexively (`src/dredge/config.py:72-123`).
- IDIOM-10 [PRACTICE][S3] Python 3.12 provides `itertools.batched`, but the current step slicing is correct; DISPUTED(Analysis 3 IDIOM-10): this is modernization, not a correctness defect (`src/dredge/engine.py:137-138`, `pyproject.toml:8`).
- IDIOM-11 [DEFECT][S3] Sequential replacement can expand `{items}` introduced by `ledger_hint`; perform one-pass token-regex substitution while leaving unrelated braces untouched (`src/dredge/engine.py:94-102`).
- IDIOM-12 [PRACTICE][S3] DISPUTED(Analysis 3 IDIOM-9): `str.format()` would parse legitimate prompt/path braces already protected by tests; retain explicit token replacement or use a custom-delimiter `string.Template` (`src/dredge/engine.py:94-102`, `tests/test_engine.py:72-78`).

## 4. CICD

- CICD-1 [GAP][S1] No `.github/workflows/` exists; establish one blocking PR/push gate running `uv sync --locked --all-groups`, `uv lock --check`, lint, format, strict typing, and tests (`pyproject.toml:1-25`, `uv.lock:1-7`).
- CICD-2 [GAP][S2] Add `uv run ruff check .` and `uv run ruff format --check .`; DISPUTED(Analysis 2 CICD-2 S1): only the combined baseline gate merits S1 pre-release, while individual implementation jobs are S2 (`src/dredge/config.py:104`, `.github/` absent).
- CICD-3 [GAP][S2] Add strict `uv run pyright` over `src` and `tests`, targeting the untyped resolver callback, `**flags`, test helpers, and `ctx.obj` boundary (`src/dredge/config.py:72-113`, `src/dredge/cli.py:18-26`, `tests/test_engine.py:9-20`).
- CICD-4 [GAP][S2] Test Python 3.12, 3.13, and 3.14 with 3.12 required, because the declared interpreter floor currently has no automated evidence (`pyproject.toml:8`, `.github/` absent).
- CICD-5 [GAP][S2] On protected `v*` tags, run `uv build`, validate metadata, install the wheel in a clean environment, smoke `dredge --help`, and publish only after all checks pass (`pyproject.toml:13-22`).
- CICD-6 [GAP][S2] Use PyPI Trusted Publishing with a protected release environment and job-scoped `id-token: write`, avoiding long-lived package credentials (`pyproject.toml:1-18`, `.github/` absent).
- CICD-7 [GAP][S2] Add `pytest --cov=dredge --cov-branch --cov-fail-under=90` after direct config/CLI tests land; those modules currently have no direct coverage (`tests/test_engine.py`, `src/dredge/config.py`, `src/dredge/cli.py`).
- CICD-8 [GAP][S2] Add an example-fidelity job that parses every `examples/*.toml`, validates referenced local assets, and checks mount/hint consistency without launching Docker (`examples/openwiki.toml:9-22`).
- CICD-9 [GAP][S3] Preserve the existing seven-day dependency gate by asserting `exclude-newer-span = "P7D"` remains in the lockfile and applying the same policy to update jobs (`uv.lock:5-7`).
- CICD-10 [GAP][S3] Use `astral-sh/setup-uv` pinned by commit SHA with uv caching keyed by `uv.lock` and `pyproject.toml`; do not cache `.venv` (`uv.lock`, `.gitignore:1`).
- CICD-11 [GAP][S3] Default workflow permissions to `contents: read`, pin every action by SHA, run `zizmor`, and emit provenance attestations for release artifacts (`.github/` absent).
- CICD-12 [GAP][S3] Declare POSIX-only support and add a macOS smoke job; DISPUTED(Analysis 2’s former Windows-matrix claim): slash-based component matching is not Windows-correct, so Windows should not be promised accidentally (`src/dredge/engine.py:33-38`, `README.md`).

## 5. COVER

- COVER-1 [GAP][S1] `config.load()` has no tests for precedence, provenance, relative paths, malformed TOML, wrong shapes, boolean integers, unknown keys, empty env values, or validation branches (`src/dredge/config.py:56-124`, `tests/test_engine.py`).
- COVER-2 [GAP][S1] No `typer.testing.CliRunner` tests cover help, option parsing, stdout/stderr, exit codes 0/1/2, report creation/removal, or expected operational errors (`src/dredge/cli.py:13-125`, `tests/test_engine.py`).
- COVER-3 [GAP][S1] Add a regression test where a later runner truncates an earlier ledger entry; completion must fail unless final `manifest - ledger` is empty (`src/dredge/engine.py:132-166`).
- COVER-4 [GAP][S1] Ledger tests omit malformed bullets, missing dispositions, unrelated Markdown, duplicates, partial final writes, invalid UTF-8, and unparseable diagnostics at the core trust boundary (`src/dredge/engine.py:43-56`, `tests/test_engine.py:23-27,65-69`).
- COVER-5 [GAP][S2] A wiki-resident ledger can contain unrelated bullets shaped `- x - y`, which all parse as coverage; test and define section scoping or exact manifest-entry validation (`examples/openwiki.toml:9`, `src/dredge/engine.py:48-55`).
- COVER-6 [GAP][S2] Concurrent scheduling, append, truncate, and `unprocessable.txt` races remain untested even though ledger membership is the only success oracle (`src/dredge/engine.py:108-160`, `src/dredge/cli.py:83-89`).
- COVER-7 [GAP][S2] Retry tests force `[0]` but never assert exact waits, attempts, pause placement, bisection order, or distinct initial/bisect/final policies (`src/dredge/engine.py:120-160`, `tests/test_engine.py:9-14`).
- COVER-8 [GAP][S2] Enumeration tests omit recursive/unmatched globs, hidden entries, files versus directories, symlinks, root paths, destination-root rewrites, overlapping rewrites, and deletion after enumeration (`src/dredge/engine.py:22-40`, `tests/test_engine.py:81-87`).
- COVER-9 [GAP][S2] Test `KeyboardInterrupt` during both runner execution and sleeping, including concise diagnostics, child behavior, preserved ledger progress, and successful restart (`src/dredge/engine.py:91-92,120-160`).
- COVER-10 [GAP][S2] Test large prompt transport because all paths are embedded in one argv element and can exceed `ARG_MAX`; pin the failure before adding stdin or prompt-file transport (`src/dredge/engine.py:94-109`).
- COVER-11 [GAP][S3] A UTF-8 BOM silently hides the first ledger line rather than crashing; DISPUTED(Analysis 3 COVER-4 wording): test either explicit rejection or `utf-8-sig` acceptance (`src/dredge/engine.py:48-50`).
- COVER-12 [GAP][S3] Add Hypothesis properties over Unicode normalization, delimiters, braces, whitespace, newlines, and rewrite boundaries (`src/dredge/engine.py:22-61,94-102`).
- COVER-13 [GAP][S3] Add a 100k-entry non-timing scale test: repeated full-ledger reads currently make reconciliation proportional to ledger size times attempts/batches (`src/dredge/engine.py:108,110,117,123,134,142,146,165`).

## 6. ENFORCE

- ENFORCE-1 [GAP][S1] Add `[tool.ruff] target-version = "py312"` and `lint.select = ["E","F","W","I","UP","B","SIM","RET","PTH","PERF","RUF"]`, with only a scoped `B008` exception for current Typer defaults (`pyproject.toml`, `src/dredge/*.py`).
- ENFORCE-2 [GAP][S1] Add `[tool.pyright] typeCheckingMode = "strict"`, `pythonVersion = "3.12"`, and `include = ["src", "tests"]` (`src/dredge/config.py:72-113`, `src/dredge/cli.py:18-26`).
- ENFORCE-3 [GAP][S2] Add `[tool.pytest.ini_options] testpaths = ["tests"]`, `addopts = "-ra --strict-config --strict-markers"`, and `filterwarnings = ["error"]` (`pyproject.toml:24-25`).
- ENFORCE-4 [GAP][S2] Configure branch coverage with `source = ["dredge"]` and `fail_under = 90`, enabling the gate only after config and CLI tests prevent immediate meaningless failure (`tests/test_engine.py`, `src/dredge/config.py`, `src/dredge/cli.py`).
- ENFORCE-5 [GAP][S2] Add pre-commit hooks for `ruff check --fix`, `ruff format`, `uv lock --check`, `check-toml`, `trailing-whitespace`, `end-of-file-fixer`, and `check-added-large-files` (`.pre-commit-config.yaml` absent).
- ENFORCE-6 [GAP][S2] The dev dependency group contains only pytest; add locked `ruff`, `pyright`, `pytest-cov`, and `pre-commit` so every prescribed local/CI command is reproducible (`pyproject.toml:24-25`).
- ENFORCE-7 [GAP][S2] Protect `main` with required lint, format, strict-type, test/coverage, lock, build, and installed-entry-point checks (`.git/config:9-11`, `.github/` absent).
- ENFORCE-8 [GAP][S2] Add an import contract forbidding `dredge.engine` from importing Typer or `dredge.cli`, preserving the current library/CLI boundary (`src/dredge/engine.py:12-19`, `src/dredge/cli.py:8-11`).
- ENFORCE-9 [GAP][S2] Validate packaging with `validate-pyproject` and smoke the installed wheel’s `dredge --help`, `dredge config`, and invalid-config exit 2 (`pyproject.toml:1-22`, `src/dredge/cli.py:24-33`).
- ENFORCE-10 [GAP][S2] Gate release consistency across `vX.Y.Z`, project metadata, installed metadata, and the changelog heading (`pyproject.toml:3`, `src/dredge/__init__.py:3`, `CHANGELOG.md:8`).
- ENFORCE-11 [GAP][S2] Validate every example TOML and referenced local file; this would mechanically reject the absent prompt before release (`examples/openwiki.toml:14`).
- ENFORCE-12 [PRACTICE][S3] Add `.editorconfig` for UTF-8/LF and the organization’s encoding validator; DISPUTED(Analysis 3 ENFORCE-11): blanket Ruff `D` enforcement on private helpers would add noise without protecting a public contract (`src/dredge/*.py`, repository root).

## 7. DOCS

- DOCS-1 [DEFECT][S1] Document the exact ledger grammar: `- ` prefix, rightmost `" - "` split, trimming, trailing-slash normalization, encoding, malformed-line behavior, and section scope (`README.md:9`, `src/dredge/engine.py:43-56`).
- DOCS-2 [DEFECT][S2] Disposition semantics are undefined while every parseable disposition counts as covered, so `- /path - failed` permanently removes the item from pending; define “recorded means never retry” or reserve failure dispositions (`README.md:9`, `src/dredge/config.py:26`, `src/dredge/engine.py:50-55`).
- DOCS-3 [DEFECT][S2] README claims every value supports flag precedence although only `corpus_globs` and `batch_size` have flags; add the missing flags or state that unavailable tiers are skipped (`README.md:27`, `src/dredge/cli.py:44,70-76`).
- DOCS-4 [GAP][S2] Add a reference for all ten keys, TOML types, defaults, exact `$DREDGE_*` names, list encodings, and `$DREDGE_CONFIG` (`src/dredge/config.py:1-9,36-48,74`).
- DOCS-5 [GAP][S2] Document that TOML-relative paths resolve against the config directory while environment and flag paths resolve against the process cwd (`src/dredge/config.py:116-121`).
- DOCS-6 [GAP][S2] Publish the exit-code contract for complete, incomplete, invalid usage/config, launch failure, timeout, and interruption (`src/dredge/cli.py:24-33,81-103`).
- DOCS-7 [DEFECT][S2] `plan` and `status` are byte-identical despite distinct help promises; make `plan` preview batch composition/commands or merge the verbs (`src/dredge/cli.py:47-66`).
- DOCS-8 [GAP][S2] Explain argv-only runner execution, absence of shell expansion, exact-element `{prompt}` replacement, inherited child stdio, command-line limits, and current lack of timeout (`src/dredge/engine.py:91-109`).
- DOCS-9 [DEFECT][S2] Qualify “coverage-guaranteed” as conditional on truthful durable ledger writes, exclusive ownership, stable manifest scope, and final fixpoint verification (`README.md:3-11`, `src/dredge/engine.py:132-166`).
- DOCS-10 [DEFECT][S2] The “complete” OpenWiki example is missing its prompt and identifies an absolute ledger hint not present in its declared mounts (`README.md:27`, `examples/openwiki.toml:9-22`).
- DOCS-11 [DEFECT][S3] `--batch-size` lacks help text, valid range, default, and interaction with retry/bisection cost (`src/dredge/cli.py:73`).
- DOCS-12 [GAP][S3] Add development commands and generated/snapshotted CLI Markdown plus a man page so Typer help, README usage, and releases remain synchronized (`README.md:14-39`, `pyproject.toml:24-25`).

## 8. QUALITY

- QUALITY-1 [DEFECT][S1] Validate that `runner` contains at least one exact `{prompt}` argv element; otherwise dredge launches a promptless command through a finite but potentially 20-hour retry tree (`src/dredge/config.py:60-69`, `src/dredge/engine.py:106-109`).
- QUALITY-2 [DEFECT][S2] Malformed TOML, invalid casts, unreadable prompts/ledgers, missing executables, and permission failures escape as tracebacks rather than concise diagnostics with documented codes (`src/dredge/config.py:50-52,77-112`, `src/dredge/engine.py:91-92`).
- QUALITY-3 [DEFECT][S2] Engine narration and inherited child output contaminate stdout, while even successful `verify` emits a human summary there; reserve stdout for records/structured output and send narration to stderr (`src/dredge/engine.py:83,91-92`, `src/dredge/cli.py:82-87,98-103`).
- QUALITY-4 [DEFECT][S2] Rewrite validation accepts empty sides: `"=x"` matches every absolute path, while `"/=x"` strips its source to empty; parse nonempty root-aware `Rewrite` values (`src/dredge/config.py:67-69`, `src/dredge/engine.py:29,33-38`).
- QUALITY-5 [DEFECT][S2] NEW: enumerating the host root converts `"/"` to the empty string through unconditional `rstrip("/")`, creating an invalid manifest item even without rewrites (`src/dredge/engine.py:32-40`).
- QUALITY-6 [DEFECT][S2] The default `ledger` is cwd-relative while default `ledger_hint` is root-absolute, so zero-config local execution instructs the agent to write a different file from the one dredge reads (`src/dredge/config.py:41-42`).
- QUALITY-7 [DEFECT][S2] Unknown `[dredge]` keys and misspelled programmatic flags silently no-op; reject unknown TOML keys and replace `**flags: object` with a typed overrides boundary (`src/dredge/config.py:72,80-100`).
- QUALITY-8 [DEFECT][S2] Coverage ignores disposition, allowing an honest `failed` record to count as complete; parse typed ledger entries and make pending policy disposition-aware (`src/dredge/engine.py:50-55`).
- QUALITY-9 [DEFECT][S2] `dredge config` prints complete runner argv, potentially exposing inline tokens or credentials; redact secret-like arguments and tell bug reporters never to share raw runner output (`src/dredge/cli.py:115-125`, `src/dredge/config.py:40`).
- QUALITY-10 [DEFECT][S2] `orphans` cannot inspect the important “corpus now empty” case because shared `_manifest()` exits 2 before comparing the ledger against an empty set (`src/dredge/cli.py:36-41,106-112`).
- QUALITY-11 [DEFECT][S3] `run` prints “sweep complete” before final report persistence and on the exit-1 unprocessable path; report `complete` only after final reconciliation and successful output handling (`src/dredge/cli.py:81-89`).
- QUALITY-12 [DEFECT][S3] `covered()` silently discards malformed lines; return parse diagnostics so `verify` can report ignored evidence (`src/dredge/engine.py:48-56`, `src/dredge/cli.py:92-103`).
- QUALITY-13 [DEFECT][S3] `sleep(pause)` runs after the final queue item even though no next batch follows; sleep only between external invocations (`src/dredge/engine.py:140-155`).
- QUALITY-14 [GAP][S2] Add `--version` backed by installed package metadata so diagnostics and scripts can identify the running build (`pyproject.toml:3,13-14`, `src/dredge/cli.py:13`).
- QUALITY-15 [DEFECT][S3] Empty environment values are treated as configured: integers crash while `DREDGE_PROMPT_FILE=""` records misleading environment provenance; consistently treat empty as unset or reject it (`src/dredge/config.py:56-57,93-96,110-113`).
- QUALITY-16 [DEFECT][S3] `Config` and `SweepResult` are mutable dataclasses assembled via `setattr`, allowing post-validation invariant breakage; use frozen slotted values constructed after parsing (`src/dredge/config.py:36-48,84-121`, `src/dredge/engine.py:64-68`).

## 9. CONTRIB

- CONTRIB-1 [GAP][S1] Missing `LICENSE` leaves no clear inbound-equals-outbound basis for external patches; ship MIT terms before accepting contributions (`README.md:37-39`, repository root).
- CONTRIB-2 [GAP][S2] Add `CONTRIBUTING.md` with Python 3.12 setup, `uv sync --locked --all-groups`, lint/type/test/build commands, and example validation (`pyproject.toml:8-25`).
- CONTRIB-3 [GAP][S2] Add `SECURITY.md` with private reporting and a trust-model statement that `dredge.toml` executes arbitrary argv and must be treated like a Makefile (`src/dredge/engine.py:91-107`).
- CONTRIB-4 [GAP][S2] State a DCO or CLA policy before outside work arrives; DCO sign-off is the lighter fit for an intended MIT project (`README.md:37-39`, repository root).
- CONTRIB-5 [GAP][S3] Add a bug template requesting version, OS/Python, redacted config, ledger diagnostics, globs/rewrites, and runner behavior—never raw credential-bearing argv (`src/dredge/cli.py:115-125`).
- CONTRIB-6 [GAP][S3] Add a PR template requiring tests, an `[Unreleased]` entry for user-facing changes, lockfile review, documentation updates, and compatibility notes (`CHANGELOG.md:1-15`, `uv.lock`).
- CONTRIB-7 [GAP][S3] Publish a compatibility policy naming ledger syntax, TOML keys, environment variables, verbs, stdout records, and exit codes as SemVer-governed interfaces (`src/dredge/config.py:20-48`, `src/dredge/cli.py:57-125`).
- CONTRIB-8 [GAP][S3] Define ledger-format migration policy because parser changes affect persistent user state and need compatibility fixtures plus release notes (`src/dredge/engine.py:43-56`).
- CONTRIB-9 [PRACTICE][S3] Seed bounded good-first issues for CLI tests, the missing prompt, `--version`, UTF-8 I/O, root-path handling, strict config shapes, and batch-size help (`tests/test_engine.py`, `examples/openwiki.toml:14`, `src/dredge/cli.py:73`).
- CONTRIB-10 [GAP][S3] State a realistic maintainer response/support contract distinguishing dredge scheduler defects from failures in arbitrary configured runners (`README.md:29`, `src/dredge/engine.py:91-113`).
- CONTRIB-11 [GAP][S3] Document required checks, imperative commits, no shared-history rewriting, signed/protected release tags, and GitHub’s canonical relationship to the Gitea mirror (`.git/config:6-14`, `.github/` absent).

## 10. TBEST

- TBEST-1 [PRACTICE][S1] Parse rather than coerce: resolve sources into `RawConfig`, then construct frozen `ResolvedConfig` through total parsers reporting key, tier, received shape, and expected type (`src/dredge/config.py:36-48,72-124`).
- TBEST-2 [PRACTICE][S1] Encode completion as `Complete` or `Incomplete(remaining: NonEmpty[AgentPath], unprocessable)` from a final ledger fixpoint, making queue-exhausted false success unrepresentable (`src/dredge/engine.py:132-166`).
- TBEST-3 [PRACTICE][S1] Make ledger parsing total: `parse_ledger(text: str) -> LedgerParseResult(entries: frozenset[LedgerEntry], diagnostics: tuple[LedgerDiagnostic, ...])`, never silently discarding evidence (`src/dredge/engine.py:43-56`).
- TBEST-4 [PRACTICE][S1] Isolate effects behind `LedgerReader`, `Runner`, `Clock`, and `Reporter` protocols so reconciliation and scheduling become deterministic logic (`src/dredge/engine.py:71-166`).
- TBEST-5 [PRACTICE][S2] Distinguish `HostPath` and `AgentPath` with `NewType` or validated wrappers, making `enumerate_corpus()` the sole namespace boundary (`src/dredge/engine.py:22-40`).
- TBEST-6 [PRACTICE][S2] Parse rewrites once as `Rewrite(host_prefix: HostPath, agent_prefix: AgentPath)` with nonempty, root-aware invariants (`src/dredge/config.py:39,67-69`, `src/dredge/engine.py:29-38`).
- TBEST-7 [PRACTICE][S2] Replace ignored booleans with a closed outcome union such as `FullyCovered | Progressed(remaining) | Stalled | RunnerFailed(RunResult)` (`src/dredge/engine.py:104-130`).
- TBEST-8 [PRACTICE][S2] Express scheduling as `next_action(state) -> Run | Sleep | Bisect | Defer | Finish`, with distinct typed initial, bisect, and final retry policies (`src/dredge/engine.py:115-160`).
- TBEST-9 [PRACTICE][S2] Use `@dataclass(frozen=True, slots=True)` for resolved configuration, policies, ledger entries, events, and result snapshots (`src/dredge/config.py:36-48`, `src/dredge/engine.py:64-68`).
- TBEST-10 [PRACTICE][S2] Add Hypothesis state-machine tests over manifest changes, ledger growth/regression, interruption, restart, and bisection, asserting `Complete` iff final pending is empty (`src/dredge/engine.py:59-61,132-166`).
- TBEST-11 [PRACTICE][S2] Emit typed engine events rendered by CLI reporters to stderr, text, JSON, or JSON Lines, making parallel workers and Unix consumers additive (`src/dredge/engine.py:83,121-159`, `src/dredge/cli.py:47-125`).
- TBEST-12 [PRACTICE][S2] Model prompt transport as `Arg | Stdin | PromptFile`, avoiding `ARG_MAX` failures while preserving argv-safe runner composition (`src/dredge/engine.py:94-109`).
- TBEST-13 [PRACTICE][S3] Accept `--manifest PATH` and `--manifest -` alongside globs so `fd ... | dredge run --manifest -` is deterministic and genuinely Unix-composable (`src/dredge/cli.py:44-76`, `src/dredge/engine.py:22-40`).
- TBEST-14 [PRACTICE][S3] Ship the typed library boundary with `py.typed`, strict Pyright, and exported runner/event/ledger protocols so integrations do not scrape Typer output (`src/dredge/`, `src/dredge/engine.py:12-19`).