# dredge

Coverage-guaranteed batch sweeps of an AI agent over a file corpus. Point it at a set of directories and a runner command; dredge enumerates everything, drives the agent batch by batch, and does not believe a batch succeeded until the coverage ledger says so.

Born from a real problem: asking an agent to "read all 1,600 conversations" produces an agent that skips. Coverage has to be enforced *outside* the model - deterministic enumeration, progress verified by artifact, failures isolated mechanically.

## The model

- **The ledger is the single source of truth.** Your agent appends one line per processed item (`- <path> - <disposition>`). `pending = manifest - ledger`, recomputed live. Resume, progress, and audit are all the same set difference - there is no separate state file to drift.
- **Progress beats exit codes.** Runners can exit 0 on provider errors. A batch counts only if the ledger grew to cover it.
- **Failures bisect.** A batch that exhausts its retries splits in half and re-queues; a single item that still fails is deferred, retried once at the end, and finally reported as unprocessable. One poison item can never stall the sweep.
- **Backoff is provider-shaped.** Default waits (5m, 30m, 2h) are tuned for AI-provider usage windows, not network blips. Configure your own.

## Usage

```sh
dredge plan      # what would be swept, what is already covered
dredge run       # sweep to completion; resumable at any time
dredge status    # coverage counts
dredge verify    # audit - list every item missing from the ledger (exit 1 if any)
dredge orphans   # ledger entries whose corpus item no longer exists
dredge config    # resolved configuration and which tier each value came from
```

## Configuration

Every value resolves `flag > $DREDGE_* env > dredge.toml > default` (12-factor; `dredge config` shows the provenance of each). See [examples/openwiki.toml](./examples/openwiki.toml) for a complete real-world setup driving a containerized [OpenWiki](https://github.com/langchain-ai/openwiki) agent.

The runner is any argv with a `{prompt}` placeholder; the prompt template is yours (`prompt_file`), with `{batch_id}`, `{items}`, and `{ledger_hint}` interpolated. dredge knows nothing about any specific agent - it only enforces coverage.

## Install

```sh
uv tool install dredge --from git+https://github.com/InfiniteRoomLabs/dredge
```

## License

MIT.
