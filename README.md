# dredge

Coverage-guaranteed batch sweeps of an AI agent over a file corpus. Point it at a set of directories and a runner command; dredge enumerates everything, drives the agent batch by batch, and does not believe a batch succeeded until the coverage ledger says so.

Born from a real problem: asking an agent to "read all 1,600 conversations" produces an agent that skips. Coverage has to be enforced *outside* the model - deterministic enumeration, progress verified by artifact, failures isolated mechanically.

## The model

- **The ledger is the single source of truth.** Your agent appends one line per processed item. `pending = manifest - ledger`, recomputed live. Resume, progress, and audit are all the same set difference - there is no separate state file to drift.
- **Progress beats exit codes.** Runners can exit 0 on provider errors. A batch counts only if the ledger grew to cover it.
- **Completion is a fixpoint, not queue exhaustion.** `run` exits 0 only when a final `manifest - ledger` reconciliation is empty - a ledger that regressed mid-run yields a nonzero exit, never silent false success.
- **Failures bisect.** A batch that exhausts its retries splits in half and re-queues (with a deliberately truncated retry budget, so one poison item cannot compound the full schedule at every level); a single item that still fails is deferred, retried once at the end, and reported as unprocessable.
- **Backoff is provider-shaped.** Default waits (5m, 30m, 2h) are tuned for AI-provider usage windows, not network blips.

## The ledger grammar

The ledger is dredge's wire protocol with your agent. One line per item:

```
- <path> - <disposition>
```

- The line must start with `- ` (dash, space); the disposition is the text after the LAST ` - ` separator, so paths may themselves contain ` - `.
- Any nonempty one-word disposition marks the item COVERED - recording is terminal. If your agent can fail an item, do not write a ledger line for it; an honest "failed" entry would still count as coverage.
- Trailing slashes are normalized; encoding is UTF-8 (BOM tolerated); lines not matching the grammar are ignored.
- One dredge process per ledger. Concurrent sweeps against the same ledger will credit each other's writes and race over reports.

## Usage

```sh
dredge plan      # coverage counts + first-batch preview
dredge run       # sweep to completion; resumable at any time
dredge status    # coverage counts
dredge verify    # audit: list every item missing from the ledger (exit 1 if any)
dredge orphans   # ledger entries whose corpus item no longer exists
dredge config    # resolved configuration and which tier each value came from
```

Exit codes: `0` complete; `1` incomplete coverage or unprocessable items; `2` configuration error; `3` runner executable not found; `130` interrupted (rerun to resume). Records (missing paths, resolved values) go to stdout; narration goes to stderr.

## Configuration

Every value resolves `flag > $DREDGE_* env > dredge.toml > default`; `dredge config` shows the provenance of each. Values are parsed, not coerced - wrong shapes, unknown keys, and empty env vars are hard errors.

| Key | Type | Default | Notes |
|---|---|---|---|
| `corpus_globs` | list[str] | (required) | host globs; `**` recurses. Env: comma-separated |
| `rewrites` | list[str] | `[]` | `hostprefix=agentprefix`; component-boundary, longest-prefix-wins; collisions are errors |
| `runner` | list[str] | (required for run) | argv with one exact `{prompt}` element; no shell. Env: shlex-parsed |
| `ledger` | path | `coverage-ledger.md` | toml-relative (defaults anchor to the config file too) |
| `ledger_hint` | str | derived from `ledger` | the ledger path AS THE AGENT SEES IT (e.g. container path) |
| `prompt_file` | path | built-in template | tokens `{batch_id}`, `{items}`, `{ledger_hint}`; literal braces are safe |
| `batch_size` | int >= 1 | `40` | smaller batches bisect cheaper but cost more runs |
| `backoff` | list[int] | `[300, 1800, 7200]` | seconds between retries; bisection halves use a truncated budget |
| `batch_timeout` | int >= 0 | `0` (unlimited) | seconds per runner invocation; a hung runner counts as a failed attempt |
| `pause` | int >= 0 | `20` | seconds between batches |
| `state_dir` | path | `.dredge` | failure reports land here |

`$DREDGE_CONFIG` selects the config file (default `./dredge.toml`); an explicitly named file that does not exist is an error. Paths from the toml file (and defaults, when a config file is in play) resolve relative to the file; flag/env paths resolve against the cwd.

The runner is executed directly (no shell, no expansion); the rendered prompt replaces the `{prompt}` argv element verbatim. Very large batches produce very large argv - lower `batch_size` if you approach your platform's `ARG_MAX`. POSIX only.

See [examples/openwiki.toml](./examples/openwiki.toml) for a complete real-world setup driving a containerized [OpenWiki](https://github.com/langchain-ai/openwiki) agent, including the namespace `rewrites` a container mount requires. dredge knows nothing about any specific agent - it only enforces coverage.

## Install

```sh
uv tool install dredge
```

## License

MIT - see [LICENSE](https://github.com/InfiniteRoomLabs/dredge/blob/main/LICENSE).
