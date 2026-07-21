"""AIOS OLX Android Agent — periodic collection scheduler."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

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
        collector: Optional[OLXCollector] = None,
        storage: Optional[OLXStorage] = None,
        interval_s: float = 3600.0,
    ):
        self.collector = collector or OLXCollector()
        self.storage = storage or OLXStorage()
        self.interval_s = float(interval_s)
        self.history: List[Dict[str, object]] = []
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._history_lock = threading.Lock()

    @property
    def running(self) -> bool:
        """Whether the background loop is currently active."""
        return self._thread is not None and self._thread.is_alive()

    def _record(self, record: Dict[str, object]) -> None:
        with self._history_lock:
            self.history.append(record)

    def run_once(
        self, queries: List[str], max_cards: int = 100
    ) -> Dict[str, Dict[str, object]]:
        """Collect every query a single time and persist the results.

        Returns:
            Mapping of query → run record (timestamp, parsed/inserted/total).
        """
        summaries: Dict[str, Dict[str, object]] = {}
        for query in queries:
            cards = self.collector.collect(query=query, max_cards=max_cards)
            inserted = self.storage.save_ads(cards)
            record: Dict[str, object] = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "query": query,
                "parsed": len(cards),
                "inserted": inserted,
                "total": self.storage.count(query=query),
            }
            self._record(record)
            summaries[query] = record
        return summaries

    def start(
        self,
        queries: List[str],
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

    def __enter__(self) -> "CollectionScheduler":
        return self

    def __exit__(self, *_exc) -> None:
        self.stop()
