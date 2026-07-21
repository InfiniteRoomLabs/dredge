"""Sweep engine: the ledger is the single source of truth.

pending = manifest - ledger, recomputed after every run. There is no
done-file to drift out of sync; resume, verification, and progress are all
the same set difference. A batch whose items are still pending after a run
made no progress: back off, retry, and finally bisect until the failure is
isolated to single items, which are deferred and retried once at the end.
"""

from __future__ import annotations

import glob as globlib
import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config


def enumerate_corpus(globs: Iterable[str], rewrites: Iterable[str] = ()) -> list[str]:
    """Expand globs on the host, then rewrite into the namespace the agent
    sees (e.g. container mount paths) so manifest and ledger agree.

    Rewrites match on path-component boundaries, longest prefix first, so
    /data=/x never captures /database.
    """
    pairs = sorted((r.split("=", 1) for r in rewrites), key=lambda p: -len(p[0]))
    items: set[str] = set()
    for g in globs:
        for p in globlib.glob(g):
            p = p.rstrip("/")
            for src, dst in pairs:
                src = src.rstrip("/")
                if p == src or p.startswith(src + "/"):
                    p = dst.rstrip("/") + p[len(src):]
                    break
            items.add(p)
    return sorted(items)


def covered(ledger: Path) -> set[str]:
    """Paths already recorded in the coverage ledger."""
    done: set[str] = set()
    if not ledger.is_file():
        return done
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if line.startswith("- ") and " - " in line[2:]:
            # Disposition is the last " - " field; the path itself may
            # contain " - ", so split from the right.
            path = line[2:].rsplit(" - ", 1)[0].strip()
            if path:
                done.add(path.rstrip("/"))
    return done


def pending(manifest: Iterable[str], ledger: Path) -> list[str]:
    done = covered(ledger)
    return [p for p in manifest if p not in done]


@dataclass
class SweepResult:
    completed: int = 0
    deferred: list[str] = field(default_factory=list)
    unprocessable: list[str] = field(default_factory=list)


class Sweep:
    """Drives runner invocations until the manifest is covered.

    `run_cmd` and `sleep` are injectable for tests.
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
        self.manifest = manifest
        self.sleep = sleep
        self.log = log
        self.run_cmd = run_cmd or self._exec

    def _exec(self, argv: list[str]) -> bool:
        return subprocess.run(argv, check=False).returncode == 0

    def _render_prompt(self, batch_id: str, items: list[str]) -> str:
        # Token replacement, not str.format(): user templates and item paths
        # may legitimately contain braces.
        return (
            self.cfg.prompt_template()
            .replace("{batch_id}", batch_id)
            .replace("{ledger_hint}", self.cfg.ledger_hint)
            .replace("{items}", "\n".join(items))
        )

    def _run_batch(self, batch_id: str, items: list[str]) -> bool:
        """One runner invocation; success = every item newly covered or batch shrank."""
        prompt = self._render_prompt(batch_id, items)
        argv = [prompt if a == "{prompt}" else a for a in self.cfg.runner]
        before = len(pending(items, self.cfg.ledger))
        ok = self.run_cmd(argv)
        after = len(pending(items, self.cfg.ledger))
        # Progress, not exit code, is the ground truth (runners can exit 0
        # on provider errors).
        return after < before or (ok and before == 0)

    def _attempt(self, batch_id: str, items: list[str]) -> bool:
        """Retry one batch through the backoff schedule. True if fully covered."""
        items = pending(items, self.cfg.ledger)
        if not items:
            return True
        for i in range(len(self.cfg.backoff) + 1):
            self.log(f"=== {batch_id} attempt {i + 1} ({len(items)} items)")
            self._run_batch(batch_id, items)
            items = pending(items, self.cfg.ledger)
            if not items:
                return True
            if i < len(self.cfg.backoff):
                wait = self.cfg.backoff[i]
                self.log(f"{batch_id}: {len(items)} items still pending; retrying in {wait}s")
                self.sleep(wait)
        return False

    def run(self) -> SweepResult:
        result = SweepResult()
        todo = pending(self.manifest, self.cfg.ledger)
        initial_pending = set(todo)
        queue: list[tuple[str, list[str]]] = []
        for n, i in enumerate(range(0, len(todo), self.cfg.batch_size)):
            queue.append((f"batch-{n:03d}", todo[i : i + self.cfg.batch_size]))

        while queue:
            batch_id, items = queue.pop(0)
            items = pending(items, self.cfg.ledger)
            if not items:
                continue
            if not self._attempt(batch_id, items):
                remaining = pending(items, self.cfg.ledger)
                if len(remaining) > 1:
                    mid = (len(remaining) + 1) // 2
                    self.log(f"{batch_id}: bisecting {len(remaining)} items")
                    queue.insert(0, (f"{batch_id}.b", remaining[mid:]))
                    queue.insert(0, (f"{batch_id}.a", remaining[:mid]))
                else:
                    self.log(f"{batch_id}: single item failed; deferring")
                    result.deferred.extend(remaining)
            self.sleep(self.cfg.pause)

        # Final retry round for deferred singles.
        for i, item in enumerate(result.deferred):
            if not self._attempt(f"retry-{i:03d}", [item]):
                result.unprocessable.append(item)

        # Completed is derived from the ledger, the only honest counter -
        # items covered inside otherwise-failed batches still count, and
        # set arithmetic stays correct even if the ledger was edited mid-run.
        result.completed = len(initial_pending - set(pending(self.manifest, self.cfg.ledger)))
        return result
