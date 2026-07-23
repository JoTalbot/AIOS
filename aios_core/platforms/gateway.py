"""ShardGateway + ShardHealthMonitor — шлюз и следящий за здоровьем шардов.

* :class:`ShardGateway` проксирует запросы на хост профиля по маршруту из
  :class:`ShardRouter`. Если маршрут ведёт на собственный узел
  (``AIOS_HOST_ID``), HTTP-хоп не делается — возвращается ``local``
  маркер, и обработка остаётся локальной (избегаем петель).
* :class:`ShardHealthMonitor` периодически проверяет ``/health`` каждого
  хоста и обновляет флаги здоровья в роутере; больные хосты теряют
  маршруты автоматически (см. ShardRouter).

Оба компонента полностью тестируемы без сети — транспорт и probe
инъецируются.
"""

from __future__ import annotations

import os
import threading
from typing import Callable, Dict, List, Optional

from .shards import ShardRouter

DEFAULT_TIMEOUT_S = 5.0


def _default_client_factory():
    import httpx

    return httpx.Client(timeout=DEFAULT_TIMEOUT_S)


class ShardGateway:
    """Шлюз на хост профиля по липкому маршруту ShardRouter."""

    def __init__(
        self,
        router: Optional[ShardRouter] = None,
        host_id: Optional[str] = None,
        client_factory: Optional[Callable] = None,
    ):
        self.router = router or ShardRouter()
        self._owns_router = router is None
        self.host_id = host_id if host_id is not None else os.environ.get("AIOS_HOST_ID", "local")
        self._client_factory = client_factory or _default_client_factory

    def close(self) -> None:
        if self._owns_router:
            self.router.close()

    def resolve(self, profile_key: str) -> Optional[Dict]:
        """Маршрут профиля + флаг local (без изменения состояния)."""
        route = self.router.route_for(profile_key)
        if route is None:
            return None
        route = dict(route)
        route["local"] = route["host"] == self.host_id
        return route

    def proxy(
        self,
        profile_key: str,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
    ) -> Dict:
        """Проксирует вызов на хост профиля.

        Returns:
            {"status": http_status, "payload": json-or-text} при внешнем
            хопе; {"local": True, "route": ...} когда хост — этот узел;
            {"error": ..., "status": 409} когда здоровых хостов нет.
        """
        route = self.resolve(profile_key)
        if route is None:
            return {"error": "no healthy shard hosts", "status": 409}
        if route["local"]:
            return {"local": True, "route": route}

        url = route["base_url"].rstrip("/") + "/" + path.lstrip("/")
        client = self._client_factory()
        try:
            response = client.request(
                method.upper(),
                url,
                params=params,
                json=json_body,
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"text": response.text}
            return {"status": response.status_code, "payload": payload}
        except Exception as exc:  # сеть недоступна / хост упал
            return {"error": f"shard proxy failed: {exc}", "status": 502}
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()


# --------------------------------------------------------------------------- #
# ShardHealthMonitor                                                          #
# --------------------------------------------------------------------------- #


def default_health_probe(host: Dict) -> bool:
    """GET <base_url>/health → 2xx = здоров."""
    import httpx

    try:
        response = httpx.get(host["base_url"].rstrip("/") + "/health", timeout=DEFAULT_TIMEOUT_S)
        return response.status_code < 500
    except Exception:
        return False


class ShardHealthMonitor:
    """Демон health-probe хостов-шардов (как PoolMonitor для устройств)."""

    def __init__(
        self,
        router: Optional[ShardRouter] = None,
        probe: Optional[Callable[[Dict], bool]] = None,
    ):
        self.router = router or ShardRouter()
        self._owns_router = router is None
        self.probe = probe or default_health_probe
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()

    def close(self) -> None:
        self.stop()
        if self._owns_router:
            self.router.close()

    def run_once(self) -> Dict[str, object]:
        """Один цикл: probe → set_healthy; больные теряют маршруты."""
        report: Dict[str, bool] = {}
        for host in self.router.hosts():
            ok = False
            try:
                ok = bool(self.probe(host))
            except Exception:
                ok = False
            self.router.set_healthy(host["host"], ok)
            report[host["host"]] = ok
        sick = [name for name, ok in report.items() if not ok]
        return {"hosts": report, "healthy": len(report) - len(sick), "sick": sick}

    def start(self, interval_s: float = 30.0) -> bool:
        """Фоновый цикл health-probe."""
        if self._thread is not None and self._thread.is_alive():
            return False

        def _loop():
            while not self._stopped.wait(interval_s):
                try:
                    self.run_once()
                except Exception:
                    pass

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        """Останавливает фоновый цикл."""
        thread, self._thread = self._thread, None
        if thread is None:
            return False
        self._stopped.set()
        thread.join(timeout=5)
        self._stopped.clear()
        return True
