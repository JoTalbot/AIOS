"""AIOS OLX Android Agent — periodic collection scheduler."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from .collector import OLXCollector
from .storage import OLXStorage


class CollectionScheduler:
    """Runs :class:`OLXCollector` for a list of queries on a fixed interval.

    Thread-based, daemonic, and safe to embed in the REST API, the CLI or a
    standalone cron-like daemon. Every run is recorded in :attr:`history`
    with parsed/inserted counters and the resulting storage total.
    """

    def __init__(
        self,
        collector: OLXCollector | None = None,
        storage: OLXStorage | None = None,
        interval_s: float = 3600.0,
    ):
        """Initialize CollectionScheduler."""
        self.collector = collector or OLXCollector()
        self.storage = storage or OLXStorage()
        self.interval_s = float(interval_s)
        self.history: list[dict[str, object]] = []
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._history_lock = threading.Lock()

    @property
    def running(self) -> bool:
        """Whether the background loop is currently active."""
        return self._thread is not None and self._thread.is_alive()

    def _record(self, record: dict[str, object]) -> None:
        with self._history_lock:
            self.history.append(record)

    def run_once(
        self, queries: list[str], max_cards: int = 100
    ) -> dict[str, dict[str, object]]:
        """Collect every query a single time and persist the results.

        Returns:
            Mapping of query → run record (timestamp, parsed/inserted/total).
        """
        summaries: dict[str, dict[str, object]] = {}
        for query in queries:
            cards = self.collector.collect(query=query, max_cards=max_cards)
            inserted = self.storage.save_ads(cards)
            deactivated = self.storage.sync_activity(
                query, [card.fingerprint for card in cards]
            )
            record: dict[str, object] = {
                "ts": datetime.now(UTC).isoformat(),
                "query": query,
                "parsed": len(cards),
                "inserted": inserted,
                "deactivated": deactivated,
                "total": self.storage.count(query=query),
                "active": self.storage.count(query=query, active_only=True),
            }
            self._record(record)
            summaries[query] = record
        return summaries

    def start(
        self,
        queries: list[str],
        max_cards: int = 100,
        run_immediately: bool = True,
    ) -> bool:
        """Start the periodic collection loop. Returns False if already running."""
        if self.running:
            return False
        self._stop.clear()

        def _loop() -> None:
            if run_immediately:
                self.run_once(queries, max_cards=max_cards)
            while not self._stop.wait(self.interval_s):
                self.run_once(queries, max_cards=max_cards)

        self._thread = threading.Thread(
            target=_loop, name="aios-olx-scheduler", daemon=True
        )
        self._thread.start()
        return True

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the loop to exit and join the thread."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def __enter__(self) -> CollectionScheduler:
        return self

    def __exit__(self, *_exc) -> None:
        self.stop()
