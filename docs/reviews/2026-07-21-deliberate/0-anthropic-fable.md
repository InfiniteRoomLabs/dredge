**[Context: dredge review — round 5/5 final deliberation. All disputes re-verified by direct read of engine.py/config.py/cli.py/tests/examples/pyproject/git state.]**

## Round-5 adjudications

- SUSTAINED(A1 vs A2 REPO-4/DOCS-9): the hint↔mount "mismatch" remains unprovable — `ledger_hint` is only interpolated into prompt text (`engine.py:100`); the toml's own comment "ledger path as the agent sees it" (`examples/openwiki.toml:13`) delegates resolution semantics to the openwiki agent (plausibly wiki-root-relative). Provable defects stay: missing prompt file, undocumented hint semantics. A2's claim does not survive as stated.
- DISPUTED(A2 QUALITY-7 severity): `dredge config` printing runner argv is intended local behavior; secrets exposure only bites when output is shared into bug reports — re-ranked S2→S3, fixed by redaction guidance in the issue template (CONTRIB-5).
- DISPUTED(A2 CICD-1..4 blanket S1): sustained from round 4 — for an unpublished zero-user 0.1.0, only the base lint+test gate is S1; matrix/typecheck are S2.
- MERGED(A2 IDIOM-6 into QUALITY-7): unknown-key silence and unchecked `[dredge]` root shape are one defect class; A2's sharpening kept — `dredge = "string"` at TOML root makes `key in file_cfg` do *substring* matching (`config.py:98`), a genuinely weird failure mode.
- CONFIRMED by trace: `ok and before == 0` arm unreachable from `_attempt` (`engine.py:113` vs `117-119`); "sweep complete" printed on the exit-1 path (`cli.py:82,88`); config path printed twice (`cli.py:124-125`); `orphans` exit-2s via `_manifest` exactly when the whole corpus vanished (`cli.py:38-40,110`); scalar-explosion casts all reproduce as claimed (`config.py:105-112`).
- A3's analysis arrived truncated mid-REPO; its Part-1 disputes align with the round-4 consensus and are absorbed; no unseen A3 items can be contested.
- **New this round (panel missed):** rewrite-collision coverage loss (QUALITY-18), agent-namespace-only failure reports (DOCS-13).

---

# Final Merged Review

## ARCH

- ARCH-1 [DEFECT][S1] `run` exits 0 with items pending: success keys solely off `unprocessable` (`cli.py:84-89`), so ledger regression after a batch's pass goes unreported — add a final `pending(manifest, ledger)` fixpoint check before the summary and exit 1 on residue.
- ARCH-2 [DEFECT][S1] Backoff compounds across bisection levels and the deferred round: one poison item in a 40-batch pays the full ~2.6h schedule per `_attempt` (`engine.py:120-130`) × ~6 bisect levels × the final round (`engine.py:158-159`) ≈ 18h+ of sleeps; bisected/deferred re-attempts need a truncated `RetryPolicy`, and `engine.py:7`'s "retried once at the end" is false.
- ARCH-3 [DEFECT][S2] `_run_batch`'s verdict is dead code three ways: discarded at `engine.py:122`, its `ok and before == 0` arm unreachable given `_attempt`'s empty-guard (`engine.py:117-119`), and `_attempt` re-derives progress with redundant full ledger parses (`engine.py:108,110` vs `117,123`).
- ARCH-4 [GAP][S2] Concurrency protocol undefined: queue materialized once (`engine.py:136-138`), progress credited to any ledger writer (`engine.py:165`), `unprocessable.txt` write/unlink race (`cli.py:84-89`) — document "one sweep per ledger" or add a ledger-scoped lock file; POSIX `O_APPEND` atomicity alone does not resolve the logical races.
- ARCH-5 [GAP][S2] Runner seam is a bare `Callable[[list[str]], bool]` (`engine.py:81`) erasing exit code, signal, duration, timeout — a `Runner` protocol returning a typed `RunResult` is the minimal growth path for API runners and timeout policy.
- ARCH-6 [GAP][S2] `Sweep.run` fuses planning, retry/bisect policy, and effects in one loop (`engine.py:132-166`) — extract a pure `plan()`/`next_action(state)` transition so policy is table-testable without a fake runner.
- ARCH-7 [GAP][S2] Engine narrates via `log: Callable[[str], None] = print` on stdout (`engine.py:83`) — typed events (`BatchStarted/Bisected/Deferred`) rendered by the CLI buy `--json`, quiet mode, and stderr separation at once.
- ARCH-8 [DEFECT][S3] `SweepResult.deferred` means "ever deferred," not terminal state — a final-retry success stays listed (`engine.py:154,158-160`) and the CLI never surfaces it; model terminal outcomes disjointly or rename `ever_deferred`.
- ARCH-9 [DEFECT][S3] Batch ids restart at `batch-000` every resume (positional over the shrinking todo, `engine.py:137`), so logs across resumed runs don't correlate — key on manifest offset or first-item hash.
- ARCH-10 [DEFECT][S3] `provenance: dict[str, str]` lives inside `Config` (`config.py:48`), forcing the `key != "config"` special-case whose symptom is the path printed twice on the `config` row (`cli.py:124-125`) — return `(Config, Provenance)` from `load()`.
- ARCH-11 [GAP][S3] `state_dir` is configured and tier-tracked for exactly one derived report file (`cli.py:83`), and `unprocessable.txt` is a second state artifact the "ledger is the only state" claim papers over — give it a job (lock, run journal) or delete the knob.
- ARCH-12 [PRACTICE][S3] The engine/CLI split (typer confined to `cli.py`, injectable seams `engine.py:77-89`) and deterministic manifest (sorted `engine.py:40`, order-preserving `pending` `engine.py:61`) are genuine strengths — lock in with ENFORCE-9's boundary test and a determinism test; queue front-pop cost stays refuted as a non-issue at real queue sizes (≤~50 entries).

## REPO

- REPO-1 [DEFECT][S1] No `LICENSE` file while `README.md:39` declares "MIT." — legally void for downstreams and a contribution blocker; add MIT text plus `license = "MIT"` / `license-files = ["LICENSE"]` in `pyproject.toml`.
- REPO-2 [DEFECT][S2] `CHANGELOG.md:8` records `[0.1.0] - 2026-07-21` but `git tag -l` is empty (verified this round) — under the org's tag-driven publish convention the release doesn't exist; tag `v0.1.0` once CICD-5 lands.
- REPO-3 [DEFECT][S2] `examples/openwiki.toml:14` references `openwiki-prompt.txt` which does not ship (`ls examples/` = one file) — the README's "complete real-world setup" (`README.md:27`) dies with `FileNotFoundError` mid-sweep on first batch (`config.py:52`, resolved toml-relative to `examples/`).
- REPO-4 [GAP][S2] `pyproject.toml:1-11` lacks `license`, `readme`, `classifiers`, `keywords`, `[project.urls]` — published artifacts would be metadata-blind on any index.
- REPO-5 [GAP][S2] No `src/dredge/py.typed` despite full annotations — PEP 561 consumers get nothing from the typed engine API.
- REPO-6 [DEFECT][S3] Version triplicated (`pyproject.toml:3`, `__init__.py:3`, `CHANGELOG.md:8`) — derive `__version__` from `importlib.metadata.version("dredge")` and gate agreement at release (ENFORCE-11).
- REPO-7 [DEFECT][S3] `README.md:27` attributes OpenWiki to `github.com/langchain-ai/openwiki` while the example runs `deathnerd/openwiki:latest` (`examples/openwiki.toml:21`) — both *can* be valid (dispute sustained per A3), but verify the upstream link and document image provenance before public ship.
- REPO-8 [DEFECT][S3] `README.md:34` installs from the unpinned default branch (`git+https://...`) — pin to the tag once REPO-2 exists, or publish to PyPI and make git the fallback.
- REPO-9 [GAP][S3] `.gitignore` (verified: `.venv/ __pycache__/ *.egg-info/ .pytest_cache/ .dredge/ .claude/ .idea/`) omits `dist/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage*`, `htmlcov/` — artifacts the recommended toolchain will create.
- REPO-10 [GAP][S3] `CHANGELOG.md` lacks the `[Unreleased]` section and comparison links that Keep-a-Changelog (cited at line 5) prescribes — the next PR has nowhere to log itself.
- REPO-11 [GAP][S3] `requires-python = ">=3.12"` (`pyproject.toml:8`) but only a 3.14 venv has ever executed this code and no `.python-version` exists — pin the 3.12 floor locally, let CI cover the rest.
- REPO-12 [PRACTICE][S3] Dual remotes (`origin` github canonical, `gitea` homelab mirror) — document the relationship in CONTRIBUTING; `.venv/` presence stays refuted as a repo defect (explicitly ignored).

## IDIOM

- IDIOM-1 [DEFECT][S1] Bare `list` as the toml cast (`config.py:105-107`): a scalar `corpus_globs = "/data/*"` silently explodes into characters, and booleans/floats reach `int()` (`pause = 1.5` → 1) — exactly the class typed per-field parsers exist to kill.
- IDIOM-2 [DEFECT][S2] Same class, worse instance: `backoff = "300"` in toml hits `[int(x) for x in v]` (`config.py:112`) and becomes `[3, 0, 0]` — three near-zero waits silently defeating the product's headline backoff feature.
- IDIOM-3 [DEFECT][S2] `glob.glob(g)` without `recursive=True` (`engine.py:32`) silently under-enumerates `**` patterns — the one failure a "coverage-guaranteed" tool cannot afford; pass `recursive=True` and decide `include_hidden`.
- IDIOM-4 [DEFECT][S2] All `read_text()` calls omit `encoding=` (`engine.py:48`, `config.py:52,82`; write at `cli.py:86`) — locale-dependent decode of the source of truth; use `encoding="utf-8"` (`utf-8-sig` for the ledger, COVER-4).
- IDIOM-5 [DEFECT][S2] `_exec` has no `timeout=` (`engine.py:91-92`) — a hung docker/agent runner stalls the sweep forever with no diagnostic, and the ledger-growth check can't fire on a process that never returns; add a `batch_timeout` key and `subprocess.run(..., timeout=...)`.
- IDIOM-6 [PRACTICE][S3] Hand-rolled chunking at `engine.py:137-138` — `itertools.batched` is stdlib at the exact 3.12 floor; modernization, not a defect (panel consensus sustained).
- IDIOM-7 [DEFECT][S3] `comma = lambda raw: …` (`config.py:104`) is the textbook E731 violation and doesn't strip — `DREDGE_CORPUS_GLOBS="a, b"` yields a leading-space glob matching nothing; `def` it, `.strip()` elements, reject empties.
- IDIOM-8 [DEFECT][S3] `Optional[X]` + positional `typer.Option(None, …)` (`cli.py:6,19,44,73`) is pre-0.12 style — migrate to `Annotated[X | None, typer.Option(...)]`; shared-`GlobOpt` contamination stays refuted, and `Annotated` obsoletes the shared-instance pattern anyway.
- IDIOM-9 [PRACTICE][S2] The four-tier layering is a justified hand-roll — pydantic-settings can't express per-key provenance or toml-relative paths without `settings_customise_sources` contortions, and Click's `Context.get_parameter_source` covers only the flag tier — but record the decision in a comment at `config.py:72` or the next maintainer ports it.
- IDIOM-10 [PRACTICE][S3] Token-`.replace()` over `str.format` is right for brace-bearing paths (`engine.py:94-102`, pinned at `tests/test_engine.py:72-78`); `string.Template` with a custom delimiter would add defined escaping and kill the `{items}`-inside-`ledger_hint` re-expansion edge (hint replaced at line 100, before items at 101).
- IDIOM-11 [DEFECT][S3] `Path(self.prompt_file)` re-wraps an already-`Path` field (`config.py:52`) — the boundary cast isn't trusted; fix the field at parse time (TBEST-1).
- IDIOM-12 [PRACTICE][S3] Ledger parsing correctly avoids a markdown-parser dependency, but the grammar deserves a named module-level function/regex with a docstring, not inline slicing (`engine.py:48-56`).

## CICD

- CICD-1 [GAP][S1] No CI at all — minimum gate on push/PR: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run pytest`; the ledger-parsing trust boundary (`engine.py:43-56`) is currently guarded only by locally-run pytest.
- CICD-2 [GAP][S2] Matrix 3.12/3.13/3.14 via `astral-sh/setup-uv` + `uv run --python` — the declared 3.12 floor has never executed this code (REPO-11). DISPUTED(A2 blanket-S1): no users yet, S2.
- CICD-3 [GAP][S2] `uv lock --check` as its own step so lockfile drift fails loudly, matching the org's lockfile posture.
- CICD-4 [GAP][S2] Typecheck gate: `uv run pyright` strict (ENFORCE-2) — the `**flags: object` seam (`config.py:72,87`) is exactly what a checker keeps honest.
- CICD-5 [GAP][S2] Release automation: on `v*` tag → `uv build` → install wheel in a clean env → smoke `dredge --help` → publish via PyPI Trusted Publishing (OIDC, `id-token: write` only), changelog section attached.
- CICD-6 [GAP][S3] The org's 7-day gate is already encoded — `uv.lock:7` carries `exclude-newer-span = "P7D"` (verified) — so CI's job is to *preserve* it: assert the key's presence and set `UV_EXCLUDE_NEWER` on any dependency-update job.
- CICD-7 [GAP][S3] uv-native caching (`enable-cache: true` keyed on `uv.lock` + `pyproject.toml`, never caching `.venv`) — sub-30s CI keeps the gate politically survivable.
- CICD-8 [GAP][S3] Coverage job `pytest --cov=dredge --cov-branch --cov-fail-under=90` — immediately exposes `config.py`/`cli.py` at 0% (COVER-1/-5); set the floor after those tests land or it's red on day one.
- CICD-9 [GAP][S3] Example-fidelity job: parse every `examples/*.toml`, assert each referenced local file exists — mechanically catches REPO-3 without Docker.
- CICD-10 [GAP][S3] Supply-chain hygiene: `permissions: contents: read` default, actions pinned by SHA, artifact attestations on release, `zizmor` over workflows — cheap and aligned with the org's post-Shai-Hulud stance.
- CICD-11 [GAP][S3] Cross-OS: macOS smoke job + POSIX-only declaration in README — DISPUTED(A2's Windows matrix, sustained): `/`-hard-coded rewrite logic (`engine.py:33-38`) makes Windows a platform the design doesn't support; declare it, don't gate on it.

## COVER

- COVER-1 [GAP][S1] `config.py` — whose entire job is "harden config layering" — has zero tests: precedence, provenance, env casts, toml-relative resolution (`config.py:116-121`), every `_validate` branch, both scalar-explosion cases (IDIOM-1/2), and the explicit-config-missing exit-2 path (`config.py:75-78`).
- COVER-2 [GAP][S1] No test feeds `covered()` a malformed ledger (wrong bullet, missing disposition, garbage, BOM, duplicates, non-ledger markdown) — silent line-dropping is the core product risk and entirely unexercised (`engine.py:48-56`).
- COVER-3 [GAP][S2] False-positive space untested: the example ledger lives inside a live wiki (`examples/openwiki.toml:9`), and *any* markdown bullet of shape `- x - y` in that file parses as a coverage entry (`engine.py:50-55`); nothing pins what non-ledger content does to `covered()`.
- COVER-4 [DEFECT][S3] UTF-8-BOM ledger makes line 1 silently invisible: `read_text()` keeps `\ufeff` so `startswith("- ")` fails (`engine.py:50`) and that item burns the full backoff×bisect tree — silent stall, not a crash (A3's wording stays corrected); `encoding="utf-8-sig"` plus a test.
- COVER-5 [GAP][S2] No CLI tests: `typer.testing.CliRunner` would cover the 0/1/2 exit contract, the `unprocessable.txt` write/unlink dance (`cli.py:83-89`), and `verify`'s stream split in ~40 lines.
- COVER-6 [GAP][S2] Ledger-regression untested: entries disappearing after a batch passes should flip `run` to exit 1 (ARCH-1) — currently unpinned anywhere (`engine.py:132-166`).
- COVER-7 [GAP][S2] Backoff untested: nothing asserts injected `sleep` receives the schedule or that attempts = `len(backoff)+1` (`engine.py:120-130`) — the README's headline feature; the suite only ever runs `backoff=[0]` (`tests/test_engine.py:12`).
- COVER-8 [GAP][S2] Interrupted-run space unexplored: `KeyboardInterrupt` mid-batch or mid-2h-sleep gives a raw traceback, the deferred list dies with the process, no resume hint printed (`engine.py:129,140-160`).
- COVER-9 [GAP][S3] Scale behavior: `covered()` re-parses the whole ledger at ~8 call sites per batch cycle (`engine.py:108,110,117,123,134,142,146,165`) — O(ledger × batches × attempts) with no scale test; fix inside a single reconciliation pass, not an mtime cache.
- COVER-10 [GAP][S2] Prompt-transport limits untested: hundreds of long paths render into one argv element (`engine.py:101,107`) and can hit OS `E2BIG` — cover the failure mode and a stdin/file transport (pairs TBEST-12); kept from A2, the panel's best scale-realism item.
- COVER-11 [GAP][S3] `orphans` and manifest-shrink-mid-run (file deleted after enumeration → eternally pending → full backoff burn) untested (`cli.py:107-112`, `engine.py:134`).
- COVER-12 [GAP][S3] Property-based round-trip is begging: hypothesis over path text → `append_ledger` → `covered()` recovers exactly — finds the " - ", BOM, and newline edges mechanically (`tests/test_engine.py:17-20` has the helper).
- COVER-13 [GAP][S3] Bisection queue discipline (`.a` before `.b`, depth-first via `insert(0)`, `engine.py:150-151`) and the multi-poison case are pinned by no test — a breadth-first refactor would pass the suite while changing isolation latency.

## ENFORCE

- ENFORCE-1 [GAP][S1] No ruff config: `[tool.ruff]` `target-version = "py312"`, `lint.select = ["E","F","W","I","B","UP","PTH","SIM","RUF"]` — `UP` flags the `Optional` idiom (`cli.py:6`), `E731` the lambda (`config.py:104`); consciously ignore `B008` for Typer defaults.
- ENFORCE-2 [GAP][S1] No type checker: `[tool.pyright]` `typeCheckingMode = "strict"`, `pythonVersion = "3.12"`, `include = ["src", "tests"]` — immediately flags untyped `cast`/`env_cast` (`config.py:87`) and untyped `ctx.obj` (`cli.py:21`).
- ENFORCE-3 [GAP][S2] No `.pre-commit-config.yaml`: `ruff check --fix`, `ruff format`, `uv lock --check`, `check-toml`, `end-of-file-fixer` — all local, no network, org-policy-consistent.
- ENFORCE-4 [GAP][S2] No pytest config: `[tool.pytest.ini_options]` `testpaths = ["tests"]`, `addopts = "-q --strict-markers --strict-config"`, `filterwarnings = ["error"]` so Typer API churn fails instead of whispering.
- ENFORCE-5 [GAP][S2] No formatter enforced anywhere — `ruff format` in pre-commit + CI ends the question before the second contributor's first diff.
- ENFORCE-6 [GAP][S2] The dev group is pytest-only (`pyproject.toml:24-25`) — none of the gates this panel prescribes are runnable via `uv sync`; add pinned `ruff`, `pyright`, `pytest-cov` to `[dependency-groups].dev` so local and CI tooling resolve from the same lock.
- ENFORCE-7 [GAP][S3] Coverage floor as a gate (`--cov-fail-under=90`, branch on) makes COVER-1 a red build, not a review comment — sequence after COVER-1/-5 land.
- ENFORCE-8 [GAP][S3] Installed-entry-point smoke gate: `dredge --help`, `dredge config`, exit-2 from an invalid config — tests the console-script wiring (`pyproject.toml:13-14`) unit tests never touch.
- ENFORCE-9 [GAP][S3] Architectural lint: `tests/test_boundaries.py` asserting `"typer" not in sys.modules` after `import dredge.engine` mechanically enforces ARCH-12.
- ENFORCE-10 [GAP][S3] `deptry` in CI keeps the dependency set honest at exactly one runtime dep (`pyproject.toml:9-11`) — A2's low-yield objection noted; kept S3-optional at the cost of one CI line.
- ENFORCE-11 [GAP][S3] Release-consistency check: assert tag == `pyproject.toml:3` == `__init__.py:3` == changelog heading before publish — kills REPO-6's drift class at the gate.
- ENFORCE-12 [GAP][S3] Org UTF-8/LF convention: `.editorconfig` + encoding validator as a hook — no current violations found; DISPUTED(A3's blanket docstring-`D` rules, sustained): enforce docstrings on public boundaries only, not private helpers in a 400-line tool.

## DOCS

- DOCS-1 [DEFECT][S1] The ledger line grammar — dredge's only wire protocol with the agent — exists as one README clause (`README.md:9`) that omits the actual parse rules (`- ` prefix, rightmost `" - "` split, trailing-`/` strip, silent skip of everything else per `engine.py:50-55`); an agent emitting `* path — done` (em-dash) silently fails coverage forever.
- DOCS-2 [DEFECT][S2] Disposition semantics undefined and dangerous: `covered()` accepts *any* disposition (`engine.py:53-55`), so an honest agent appending `- /path - failed` permanently marks the item covered; document "a ledger line means processed, never retry" or reserve failure dispositions — `DEFAULT_PROMPT`'s "one-word disposition" (`config.py:26`) actively invites failure records.
- DOCS-3 [GAP][S2] Exit-code contract (0 complete / 1 incomplete / 2 config error) implemented (`cli.py:29,88,102`) but documented nowhere — the most load-bearing missing table for a pipeline tool.
- DOCS-4 [DEFECT][S2] README claims full flag-tier precedence for every value (`README.md:27`) but only `--glob`/`--batch-size` exist (`cli.py:44,73`) — one docs-contract fix (add flags or narrow the claim), not eight defects.
- DOCS-5 [GAP][S2] No config reference: ten keys, types, defaults, env names exist only as code (`config.py:36-48`); `DEFAULT_PROMPT`'s existence and `DREDGE_CONFIG` (`config.py:74`) are documented nowhere.
- DOCS-6 [GAP][S2] Runner execution semantics undocumented: argv-only, no shell, `{prompt}` must be an exact whole argv element (`engine.py:107`), inherited stdio, no timeout, argv-length limits — users will wrongly quote and shell-escape.
- DOCS-7 [DEFECT][S3] `plan` and `status` produce byte-identical output (`cli.py:57-66`, both delegate to `_coverage_view`) while their docstrings promise different things — make `plan` preview batch composition/rendered prompt, or merge the verbs.
- DOCS-8 [DEFECT][S3] `--batch-size` is the only option with no help text (`cli.py:73`).
- DOCS-9 [DEFECT][S3] Example fidelity: `examples/openwiki.toml` is "complete" (`README.md:27`) but unrunnable — missing prompt file (REPO-3) and the `ledger_hint`↔mount relationship unexplained; DISPUTED(A2, sustained): the hint value itself is not provably wrong, and the `/home/you` placeholders *are* flagged at `examples/openwiki.toml:3`.
- DOCS-10 [GAP][S3] Relative-path semantics differ by tier — toml paths resolve against the file (`config.py:116-121`), env/flag paths against cwd — stated only in a module docstring users never see.
- DOCS-11 [GAP][S3] No development section in README (`uv sync`, `uv run pytest`) and no generated CLI reference (`typer … utils docs` wired into release keeps `--help` and docs from diverging).
- DOCS-12 [GAP][S3] The concurrency stance ("one dredge per ledger") and the qualifier on "coverage-guaranteed" (conditional on honest, durable, exclusive ledger appends plus the ARCH-1 fixpoint) belong in the README model section (`README.md:7-12`).
- DOCS-13 [GAP][S3] NEW: every user-facing failure artifact speaks the *agent* namespace — `unprocessable.txt` (`cli.py:86`), `verify` output (`cli.py:99`), engine logs — with no documented way to invert rewrites back to host paths the user can actually open; document the mapping or add an `--unrewrite` view.

## QUALITY

- QUALITY-1 [DEFECT][S1] No validation that `runner` contains a `{prompt}` element (`config.py:60-69`, `cli.py:77-79`): a placeholder-less runner executes promptless and grinds the full (finite, ~20h) backoff × bisection tree before reporting everything unprocessable; require ≥1 whole-element occurrence at load time.
- QUALITY-2 [DEFECT][S2] Uncaught exceptions violate the exit-2 contract: invalid TOML (`config.py:82`), `PermissionError`, non-integer `DREDGE_BATCH_SIZE` (`config.py:111`), missing `prompt_file` thrown mid-sweep after hours (`config.py:52`), missing runner executable (`engine.py:92` → `FileNotFoundError`) — all traceback with exit 1 instead of a `dredge: …` message.
- QUALITY-3 [DEFECT][S2] No `--version` flag (`cli.py:13-21`) — table stakes, trivially wired via `importlib.metadata`.
- QUALITY-4 [DEFECT][S2] Empty-prefix rewrite `"=x"` passes `_validate` (`config.py:67-69`) then rewrites every absolute path (`engine.py:36` with `src=""`), and a glob matching `/` rstrips to the empty manifest entry — require non-empty host and agent sides, root-aware.
- QUALITY-5 [GAP][S2] Stream discipline half-broken everywhere: `run` narrates on stdout (`engine.py:83`), and even `verify` prints its success summary to stdout (`cli.py:103`) while only the failure summary goes to stderr (`cli.py:101`); route all human narration to stderr, reserve stdout for records.
- QUALITY-6 [GAP][S2] No SIGINT handling: Ctrl-C during a 30-minute sleep (`engine.py:129`) dumps a traceback instead of "interrupted; N covered; `dredge run` resumes" — the resume story is the product's best feature and the interrupt path hides it.
- QUALITY-7 [DEFECT][S2] Unknown keys in `[dredge]` are silently ignored (`config.py:82,98` — lookup-only, no key-set check), keys outside the table vanish (`.get("dredge", {})`), and a non-table `dredge = "x"` root value turns `key in file_cfg` into *substring* matching — reject unknown keys and non-table roots with a `ConfigError` naming them, in the tool whose selling point is explainable configuration (absorbs A2 IDIOM-6).
- QUALITY-8 [DEFECT][S2] Out-of-box defaults are mutually incoherent — `ledger = "coverage-ledger.md"` (cwd-relative) but `ledger_hint = "/coverage-ledger.md"` (absolute, `config.py:41-42`), so a zero-config run's DEFAULT_PROMPT instructs the agent to write filesystem root while dredge reads cwd: zero progress and a full backoff burn; default the hint to the resolved ledger path.
- QUALITY-9 [DEFECT][S2] Coverage conflates "recorded" with "succeeded" — any disposition counts (`engine.py:53`), so `- /path - failed` removes the item from pending forever with no audit trail; define the disposition vocabulary or surface dispositions in `verify` (pairs DOCS-2).
- QUALITY-10 [DEFECT][S3] `**flags: object` + `flags.get(key)` (`config.py:72,88`) silently no-ops misspelled keys — `_load(ctx, batchsize=…)` typechecks and does nothing; keyword-only typed params or an `Overrides` TypedDict makes the seam total (caller-side twin of QUALITY-7).
- QUALITY-11 [DEFECT][S3] `orphans` exits 0 when orphans exist (`cli.py:107-112`) while sibling audit verb `verify` exits 1 on findings (`cli.py:102`); worse, `_manifest`'s exit-2-on-empty (`cli.py:38-40`) fires precisely when the whole corpus vanished — the one case `orphans` most needs to report (merges A2's variant).
- QUALITY-12 [DEFECT][S3] `self.sleep(self.cfg.pause)` runs after the final queue item and between bisection re-attempts (`engine.py:155`) — pure wasted wall-clock at defaults.
- QUALITY-13 [DEFECT][S3] `covered()` silently drops unparseable lines (`engine.py:50-55`) — return `(covered, unparsed)` so `verify` can warn "3 ledger lines parse as nothing," closing the DOCS-1 failure loop.
- QUALITY-14 [DEFECT][S3] `DEFAULT_PROMPT` says "directories" (`config.py:24-26`) but `enumerate_corpus` admits any globbed entry including files (`engine.py:31-40`) — filter by type, add a knob, or fix the wording.
- QUALITY-15 [DEFECT][S3] `Config` and `SweepResult` are mutable dataclasses (`config.py:37`, `engine.py:64`) built by `setattr` (`config.py:90-99`) — `frozen=True, slots=True` post-parse makes "resolved once" structural (the mutation protocol is why IDIOM-1 typechecks; `tests/test_engine.py:10-13` depends on it today).
- QUALITY-16 [DEFECT][S3] Empty-string env vars are treated as set (`config.py:56-57`): `DREDGE_BATCH_SIZE=""` tracebacks on `int("")`, `DREDGE_PROMPT_FILE=""` silently resolves to None with provenance "env" — treat empty as unset, the near-universal CLI convention.
- QUALITY-17 [DEFECT][S3] `run` prints "sweep complete: …" unconditionally (`cli.py:82`) — including on the exit-1 unprocessable path, contradicting the exit code in the one line pipelines will grep; print "sweep incomplete" on residue.
- QUALITY-18 [DEFECT][S2] NEW: rewrite collisions silently merge coverage — two distinct host paths mapping to the same agent path collapse into one manifest entry via `items.add(p)` (`engine.py:39`), so one ledger line "covers" multiple host items and the coverage guarantee is silently weakened; detect duplicate post-rewrite paths during enumeration and error with both host sources.
- QUALITY-19 [DEFECT][S3] `dredge config` prints full runner argv verbatim (`cli.py:123-125`), which may embed API tokens (`-e KEY=…` docker args) — DISPUTED(A2's S2, re-ranked S3): local print is intended behavior; add a redaction warning where the output is solicited (CONTRIB-5).

## CONTRIB

- CONTRIB-1 [GAP][S2] No `CONTRIBUTING.md` — dev setup (`uv sync`, `uv run pytest`), test expectations, and the tag-driven release ritual live only in the maintainer's head.
- CONTRIB-2 [GAP][S2] License ambiguity blocks contribution outright: with no LICENSE file (REPO-1) there is nothing for contributed work to be licensed under — a legal gate, not polish.
- CONTRIB-3 [GAP][S3] Ledger-format evolution policy undefined: the grammar (`engine.py:50-55`) is a public contract with users' existing ledgers and prompt templates; declare it semver-major-frozen before anyone "improves" the parse and orphans existing state.
- CONTRIB-4 [GAP][S3] No `SECURITY.md`: a tool that execs arbitrary configured argv (`engine.py:92`) should state the trust model ("dredge.toml is code — treat it like a Makefile") and a private report route.
- CONTRIB-5 [GAP][S3] No issue templates; a bug template demanding *redacted* `dredge config` output (provenance exists precisely for this, `cli.py:115-125`; redaction per QUALITY-19) plus ledger head/tail makes most reports self-diagnosing.
- CONTRIB-6 [GAP][S3] No PR template; two checkboxes ("`uv run pytest` passes", "CHANGELOG Unreleased updated") encode the entire current bar.
- CONTRIB-7 [GAP][S3] No DCO/CLA statement — DCO sign-off is the lightweight choice and must predate external commits.
- CONTRIB-8 [GAP][S3] No compatibility policy naming what's semver-stable: CLI verbs/exit codes, TOML keys, env names, ledger grammar, the Python engine API (`config.py:20-48`, `engine.py:22-61`).
- CONTRIB-9 [GAP][S3] No maintainer response contract (even "solo, best-effort, days-to-weeks") — cheapest burnout insurance; it should distinguish dredge scheduling defects from failures inside users' arbitrary runners.
- CONTRIB-10 [GAP][S3] No good-first-issue surface, though this review teems with scoped candidates (`--version`, `--batch-size` help, `orphans` exit code, explicit encodings, empty-env fix, unknown-key rejection, `itertools.batched`).
- CONTRIB-11 [GAP][S3] Canonical home verified (`origin` = `github.com/InfiniteRoomLabs/dredge`, `gitea` mirror) — document the mirror relationship in CONTRIBUTING; no per-repo `CLAUDE.md` needed for a 400-line tool (A3-refutation sustained).

## TBEST

- TBEST-1 [PRACTICE][S1] Parse, don't validate, at the config boundary: replace blind `cast(...)` (`config.py:87-102`) with per-type total parsers (`parse_str_list`, `parse_positive_int`, `parse_int_list`) that name key and tier in errors, plus a known-key check — kills the IDIOM-1/IDIOM-2 *and* QUALITY-7 classes outright.
- TBEST-2 [PRACTICE][S1] Isolate effects behind one seam: `Sweep` reaches the world via subprocess, `time.sleep`, `print`, and implicit ledger reads (`engine.py:83,89-92,108,155`) — a `World` protocol (`run_argv`, `sleep`, `read_ledger`, `emit`) makes the whole retry/bisect machine a pure function testable with a scripted world.
- TBEST-3 [PRACTICE][S1] Define completion as a final fixpoint over `manifest − ledger`, not queue exhaustion (`engine.py:132-166`) — a `Complete | Incomplete(remaining: NonEmpty[AgentPath], unprocessable)` result type makes ARCH-1's bug unrepresentable.
- TBEST-4 [PRACTICE][S2] Make the host/agent namespace distinction typecheck: `NewType("HostPath", str)` / `NewType("AgentPath", str)` with `enumerate_corpus` the only producer of `AgentPath` (`engine.py:22-40`) — and keep agent paths as protocol strings, not `Path` (host OS semantics don't apply post-rewrite); an injective-mapping invariant here also makes QUALITY-18 unrepresentable.
- TBEST-5 [PRACTICE][S2] Promote the ledger to a typed value object: `Ledger.parse(text) -> (frozenset[AgentPath], tuple[UnparsedLine, ...])` plus `format_entry()` — one module owning both directions enables the hypothesis round-trip (COVER-12), the verify-warning path (QUALITY-13), and a home for disposition semantics (QUALITY-9).
- TBEST-6 [PRACTICE][S2] Batch outcome as a consumed closed sum: `Covered | Progressed | Stalled | RunnerFailed(RunResult)` returned by `_run_batch` and *used* by `_attempt` — makes ARCH-3's computed-but-ignored verdict (and its unreachable arm) unrepresentable.
- TBEST-7 [PRACTICE][S2] Scheduling as a pure transition: `next_action(QueueState) -> RunBatch | Bisect | Defer | Done` replacing the interleaved while/insert loop (`engine.py:140-160`), with a typed `RetryPolicy` distinguishing initial/bisect/final budgets — gives ARCH-2's fix exactly one home.
- TBEST-8 [PRACTICE][S2] Parse rewrites once as `Rewrite(host_prefix, agent_prefix)` with non-empty, root-aware invariants (`config.py:39,67-69`) instead of re-splitting strings during every enumeration (`engine.py:29-38`) — makes QUALITY-4 unrepresentable.
- TBEST-9 [PRACTICE][S2] Freeze the value objects: `@dataclass(frozen=True, slots=True)` for post-parse `Config` and `SweepResult`, built by constructor not `setattr` (`config.py:84-121`).
- TBEST-10 [PRACTICE][S2] Property-based invariants with hypothesis: (a) ledger round-trip, (b) `pending ⊆ manifest` disjoint from `covered`, (c) rewrite idempotence, injectivity, and boundary-safety over generated trees (`engine.py:29-40`) — three properties subsume half the current example tests.
- TBEST-11 [PRACTICE][S3] Structured events over strings (typed engine events, CLI-owned rendering to stderr/text/JSON) — the knowability seam that makes `-o json`, quiet CI mode, and future parallel workers additive (pairs ARCH-7/QUALITY-5).
- TBEST-12 [PRACTICE][S2] Prompt transport as a typed choice — `Arg | Stdin | PromptFile` (`engine.py:94-109`) — so large corpora don't fail at OS argv limits (COVER-10) and runners stay composable; promoted to S2 alongside COVER-10.
- TBEST-13 [PRACTICE][S3] Manifest as stdin-composable input: accept `-`/file-of-paths alongside globs (`cli.py:44`) so `fd -t d … | dredge run -` works — unix composability means the enumerator is replaceable, not just the runner.
- TBEST-14 [PRACTICE][S3] Ship the types: `py.typed` + pyright strict + exported `Runner`/`World` protocols so the engine doubles as a library ("bring your own runner, keep the guarantee") — the composability endgame `README.md:29` already promises.

---

**Round-5 net changes:** 1 dispute sustained against A2 (hint↔mount — the toml comment's delegation to agent semantics verified by direct read), 1 A2 severity re-ranked down (config-prints-secrets S2→S3 as QUALITY-19), A2's TOML-root-shape sharpening absorbed into QUALITY-7 (the substring-matching failure mode is real and nasty), A2's argv-`E2BIG` items kept and TBEST-12 promoted to S2 to match, 2 genuinely new items added (QUALITY-18 rewrite-collision coverage loss — a direct hole in the product's core guarantee nobody in four rounds caught; DOCS-13 agent-namespace-only failure reports). A3's truncated list contributed no uncontested new material. The S1 set is stable across the panel and I consider it final: ARCH-1, ARCH-2, REPO-1, IDIOM-1, CICD-1, COVER-1, COVER-2, ENFORCE-1, ENFORCE-2, DOCS-1, QUALITY-1, TBEST-1..3.