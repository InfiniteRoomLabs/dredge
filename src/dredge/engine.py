"""Sweep engine: the ledger is the single source of truth.

pending = manifest - ledger, recomputed after every run. There is no
done-file to drift out of sync; resume, verification, and progress are all
the same set difference. A batch whose items are still pending after a run
made no progress: back off, retry, and finally bisect until the failure is
isolated to single items, which are deferred and retried once at the end.

Completion is a FIXPOINT, not queue exhaustion: the sweep is complete only
when a final `manifest - ledger` reconciliation comes back empty. A ledger
that regressed mid-run therefore yields Incomplete, never a false success.

Retry budgets are typed and role-specific (RetryPolicy): full patience for
initial batches, truncated for bisection halves (so one poison item cannot
compound the schedule at every level), one shot for the final round.
"""

from __future__ import annotations

import glob as globlib
import subprocess
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config


class CorpusError(Exception):
    """The corpus enumeration is unusable (rewrite collision, root collapse)."""


def enumerate_corpus(globs: Iterable[str], rewrites: Iterable[str] = ()) -> list[str]:
    """Expand globs on the host (``**`` recurses), then rewrite into the
    namespace the agent sees (e.g. container mount paths) so manifest and
    ledger agree.

    Rewrites match on path-component boundaries, longest prefix first, so
    /data=/x never captures /database. A rewrite that collapses distinct
    host paths onto one agent path, or produces an empty item, raises
    CorpusError - both silently corrupt coverage accounting.
    """
    pairs = sorted((r.split("=", 1) for r in rewrites), key=lambda p: -len(p[0]))
    sources: dict[str, str] = {}
    for g in globs:
        for host in globlib.glob(g, recursive=True):  # noqa: PTH207 - glob on full pattern strings
            host = host.rstrip("/")
            item = host
            for src, dst in pairs:
                src = src.rstrip("/")
                if item == src or item.startswith(src + "/"):
                    item = dst.rstrip("/") + item[len(src) :]
                    break
            if not item or item == "/":
                raise CorpusError(f"rewrite collapsed {host!r} to {item!r}")
            if item in sources and sources[item] != host:
                raise CorpusError(f"rewrite collision: {sources[item]!r} and {host!r} both map to {item!r}")
            sources[item] = host
    return sorted(sources)


def covered(ledger: Path) -> set[str]:
    """Paths already recorded in the coverage ledger.

    Grammar per line: ``- <path> - <disposition>``. The disposition is the
    LAST " - " field (paths may themselves contain " - "). Reads are UTF-8
    with BOM tolerance; lines that don't match the grammar are ignored.
    """
    done: set[str] = set()
    if not ledger.is_file():
        return done
    for line in ledger.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("- ") and " - " in line[2:]:
            path = line[2:].rsplit(" - ", 1)[0].strip()
            if path:
                done.add(path.rstrip("/"))
    return done


def pending(manifest: Iterable[str], ledger: Path) -> list[str]:
    done = covered(ledger)
    return [p for p in manifest if p not in done]


@dataclass(frozen=True)
class RetryPolicy:
    """Backoff schedules (seconds between attempts) per batch role."""

    initial: tuple[int, ...]
    bisection: tuple[int, ...]
    final: tuple[int, ...]

    @classmethod
    def from_backoff(cls, backoff: Sequence[int]) -> RetryPolicy:
        b = tuple(backoff)
        # Bisection halves descend with a truncated budget so a poison item
        # costs O(log n * short) instead of O(log n * full); the final
        # single-item round gets one unretried shot.
        return cls(initial=b, bisection=b[:1], final=())


@dataclass
class SweepResult:
    completed: int = 0
    complete: bool = False
    remaining: list[str] = field(default_factory=list[str])
    deferred: list[str] = field(default_factory=list[str])  # ever deferred, historical
    unprocessable: list[str] = field(default_factory=list[str])


class Sweep:
    """Drives runner invocations until the manifest is covered.

    `run_cmd` and `sleep` are injectable for tests. `log` receives progress
    narration and should go to stderr in CLI contexts - stdout belongs to
    records.
    """

    def __init__(
        self,
        cfg: Config,
        manifest: list[str],
        run_cmd: Callable[[list[str]], bool] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] = print,
    ) -> None:
        self.cfg = cfg
        self.manifest = list(dict.fromkeys(manifest))  # dedupe, keep order
        self.policy = RetryPolicy.from_backoff(cfg.backoff)
        self.sleep = sleep
        self.log = log
        self.run_cmd = run_cmd or self._exec

    def _exec(self, argv: list[str]) -> bool:
        timeout = self.cfg.batch_timeout or None
        try:
            return subprocess.run(argv, check=False, timeout=timeout).returncode == 0
        except subprocess.TimeoutExpired:
            self.log(f"runner timed out after {timeout}s")
            return False
        except FileNotFoundError as e:
            raise RunnerNotFound(str(e)) from e

    def _render_prompt(self, batch_id: str, items: list[str]) -> str:
        # Single-pass token replacement, not str.format(): user templates and
        # item paths may legitimately contain braces, and values must never
        # be re-expanded as tokens.
        out: list[str] = []
        rest = self.cfg.prompt_template()
        tokens = {
            "{batch_id}": batch_id,
            "{ledger_hint}": self.cfg.ledger_hint,
            "{items}": "\n".join(items),
        }
        while rest:
            idx, tok = min(
                ((rest.find(t), t) for t in tokens if rest.find(t) != -1),
                default=(-1, ""),
            )
            if idx == -1:
                out.append(rest)
                break
            out.append(rest[:idx])
            out.append(tokens[tok])
            rest = rest[idx + len(tok) :]
        return "".join(out)

    def _run_batch(self, batch_id: str, items: list[str]) -> None:
        prompt = self._render_prompt(batch_id, items)
        argv = [prompt if a == "{prompt}" else a for a in self.cfg.runner]
        self.run_cmd(argv)

    def _attempt(self, batch_id: str, items: list[str], schedule: tuple[int, ...]) -> bool:
        """Retry one batch through a backoff schedule. True if fully covered.

        Progress, not exit code, is the ground truth - runners can exit 0 on
        provider errors, so success means the ledger now covers the items.
        """
        items = pending(items, self.cfg.ledger)
        if not items:
            return True
        for i in range(len(schedule) + 1):
            self.log(f"=== {batch_id} attempt {i + 1} ({len(items)} items)")
            self._run_batch(batch_id, items)
            items = pending(items, self.cfg.ledger)
            if not items:
                return True
            if i < len(schedule):
                self.log(f"{batch_id}: {len(items)} items still pending; retrying in {schedule[i]}s")
                self.sleep(schedule[i])
        return False

    def run(self) -> SweepResult:
        result = SweepResult()
        todo = pending(self.manifest, self.cfg.ledger)
        initial_pending = set(todo)
        queue: list[tuple[str, list[str], tuple[int, ...]]] = []
        for n, i in enumerate(range(0, len(todo), self.cfg.batch_size)):
            queue.append((f"batch-{n:03d}", todo[i : i + self.cfg.batch_size], self.policy.initial))

        while queue:
            batch_id, items, schedule = queue.pop(0)
            items = pending(items, self.cfg.ledger)
            if not items:
                continue
            if not self._attempt(batch_id, items, schedule):
                remaining = pending(items, self.cfg.ledger)
                if len(remaining) > 1:
                    mid = (len(remaining) + 1) // 2
                    self.log(f"{batch_id}: bisecting {len(remaining)} items")
                    queue.insert(0, (f"{batch_id}.b", remaining[mid:], self.policy.bisection))
                    queue.insert(0, (f"{batch_id}.a", remaining[:mid], self.policy.bisection))
                else:
                    self.log(f"{batch_id}: single item failed; deferring")
                    result.deferred.extend(remaining)
            if queue:
                self.sleep(self.cfg.pause)

        # Final one-shot round for deferred singles.
        for i, item in enumerate(result.deferred):
            if not self._attempt(f"retry-{i:03d}", [item], self.policy.final):
                result.unprocessable.append(item)

        # Completion is the final fixpoint, never queue exhaustion: a ledger
        # regression mid-run must surface as Incomplete.
        result.remaining = pending(self.manifest, self.cfg.ledger)
        result.complete = not result.remaining
        result.completed = len(initial_pending - set(result.remaining))
        return result


class RunnerNotFound(Exception):
    """The configured runner executable does not exist; CLI maps to exit 3."""
