"""PhoneBrainDaemon — единый процесс-«мозг» Android-шлюза AIOS.

Три цикла в одном процессе:
* supervisor_loop — состояние устройства, reconnect с backoff, эскалации;
* worker_loop     — разбор очереди задач (единственный исполнитель — никаких гонок);
* api (поток)     — локальный HTTP для бота/CLI.

Логи — по-русски с эмодзи-маркерами (конвенция AGENTS.md).
Конфигурация: data/android_gateway/phone_brain_config.json (поверх дефолтов).
"""
from __future__ import annotations

import logging
import signal
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from aios_core.android_gateway import AndroidGateway
from aios_core.phone_brain import __version__
from aios_core.phone_brain.api import BrainAPI
from aios_core.phone_brain.device import DeviceSupervisor
from aios_core.phone_brain.events import EventLog
from aios_core.phone_brain.handlers import (Executor, JobContext, planner_handlers,
                                            reaction_handlers, skill_handlers)
from aios_core.phone_brain.common import iso, parse_iso, read_json, utc_now
from aios_core.phone_brain.planner import PhonePlanner
from aios_core.phone_brain.queue_store import JobStore
from aios_core.phone_brain.reactions import ReactionEngine
from aios_core.phone_brain.skills import SkillEngine
from aios_core.phone_brain.vision import VisionLocator

DEFAULT_CONFIG: dict[str, Any] = {
    "poll_interval": 10,
    "worker_interval": 2,
    "defer_seconds": 30,
    "api": {"host": "127.0.0.1", "port": 8790},
    "queue": {"retry_base_seconds": 20, "retry_cap_seconds": 900, "lease_seconds": 300,
              "default_max_attempts": 3, "retention_days": 7, "defer_limit": 20},
    "device": {"min_interval": 30, "max_interval": 900, "escalate_after_seconds": 600},
    "vision": {"enabled": True, "gemini_model": "gemini-2.0-flash",
               "mistral_model": "pixtral-12b-2409",
               "openrouter_model": "google/gemini-2.0-flash-001"},
    "reactions": {"enabled": True, "interval": 30},
}


def load_env_file(root: Path) -> dict:
    """Значения из .env (не экспортируются; нужны Telegram-ключи реакций)."""
    env: dict = {}
    try:
        for line in (root / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def load_config(root: Path) -> dict:
    """Дефолты + неглубокое слияние phone_brain_config.json."""
    config = {key: (dict(value) if isinstance(value, dict) else value)
              for key, value in DEFAULT_CONFIG.items()}
    overrides = read_json(root / "data" / "android_gateway" / "phone_brain_config.json", {})
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    return config


def setup_logging(root: Path) -> logging.Logger:
    """Ротация 3×1 МБ в logs/phone_brain.log + stdout для journald."""
    logger = logging.getLogger("phone_brain")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        file_handler = RotatingFileHandler(root / "logs" / "phone_brain.log", maxBytes=1024 * 1024,
                                           backupCount=3, encoding="utf-8")
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    return logger


class PhoneBrainDaemon:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.config = load_config(self.root)
        self.logger = setup_logging(self.root)
        data_dir = self.root / "data" / "android_gateway"
        queue_cfg = self.config["queue"]
        self.store = JobStore(
            data_dir / "phone_brain.db",
            retry_base_seconds=queue_cfg["retry_base_seconds"],
            retry_cap_seconds=queue_cfg["retry_cap_seconds"],
            lease_seconds=queue_cfg["lease_seconds"],
            default_max_attempts=queue_cfg["default_max_attempts"],
            retention_days=queue_cfg["retention_days"],
            defer_limit=queue_cfg["defer_limit"])
        self.events = EventLog(data_dir / "phone_brain_events.jsonl")
        self.gateway = AndroidGateway(self.root)
        device_cfg = self.config["device"]
        self.supervisor = DeviceSupervisor(
            self.root, gateway=self.gateway, min_interval=device_cfg["min_interval"],
            max_interval=device_cfg["max_interval"],
            escalate_after_seconds=device_cfg["escalate_after_seconds"], events=self.events)
        self.executor = Executor(JobContext(root=self.root, gateway=self.gateway,
                                            supervisor=self.supervisor, events=self.events,
                                            store=self.store))
        # Этап 2: декларативный skill-движок поверх очереди
        vision_cfg = self.config.get("vision") or {}
        self.vision = VisionLocator(
            enabled=bool(vision_cfg.get("enabled", True)),
            gemini_model=str(vision_cfg.get("gemini_model") or "gemini-2.0-flash"),
            mistral_model=str(vision_cfg.get("mistral_model") or "pixtral-12b-2409"),
            openrouter_model=str(vision_cfg.get("openrouter_model") or "google/gemini-2.0-flash-001"))
        self.skills = SkillEngine(self.root, gateway=self.gateway, events=self.events,
                                  vision=self.vision)
        for handler in skill_handlers(self.skills):
            self.executor.register(handler)
        # Этап 3: LLM-планировщик и VLM-тап
        self.planner = PhonePlanner(self.skills)
        for handler in planner_handlers(self.planner, self.vision):
            self.executor.register(handler)
        # Этап 4: reaction engine (правила на уведомления)
        self.reactions = ReactionEngine(self.root, gateway=self.gateway, store=self.store,
                                        events=self.events, env=load_env_file(self.root))
        for handler in reaction_handlers(self.reactions):
            self.executor.register(handler)
        api_cfg = self.config["api"]
        self.api = BrainAPI(self, host=api_cfg["host"], port=api_cfg["port"])
        self.started_at = iso()
        self._stop = threading.Event()
        self._busy_job: int | None = None
        self._counters = {"jobs_done": 0, "jobs_failed": 0, "jobs_retried": 0,
                          "jobs_deferred": 0, "jobs_need_confirm": 0, "leases_expired": 0}

    # -------------------------------------------------------------- loops

    def _worker_loop(self) -> None:
        self.logger.info("🧵 воркер очереди запущен (интервал %ss)", self.config["worker_interval"])
        while not self._stop.is_set():
            try:
                expired = self.store.requeue_expired()
                if expired:
                    self._counters["leases_expired"] += expired
                    self.logger.warning("⚠️ lease истёк у %d задач — возвращены в очередь", expired)
                job = self.store.claim(worker="phone-brain")
                if job is None:
                    self._stop.wait(float(self.config["worker_interval"]))
                    continue
                self._busy_job = int(job["id"])
                started = time.monotonic()
                verdict, payload = self.executor.execute(job)
                elapsed = round(time.monotonic() - started, 2)
                self._apply_verdict(job, verdict, payload, elapsed)
                self._busy_job = None
            except Exception as exc:  # noqa: BLE001 — воркер не должен падать
                self._busy_job = None
                self.logger.exception("❌ ошибка воркера: %s", exc)
                self._stop.wait(2.0)

    def _apply_verdict(self, job: dict, verdict: str, payload: dict, elapsed: float) -> None:
        job_id, token, kind = int(job["id"]), str(job.get("lease_token")), str(job.get("kind"))
        if verdict == "done":
            self.store.complete(job_id, token, payload)
            self._counters["jobs_done"] += 1
            self.logger.info("✅ задача #%d (%s) выполнена за %.2fс", job_id, kind, elapsed)
        elif verdict == "defer":
            outcome = self.store.defer(job_id, token,
                                       run_after_seconds=int(self.config["defer_seconds"]),
                                       reason=str(payload.get("reason") or ""))
            if outcome.get("status") == "failed":
                self._counters["jobs_failed"] += 1
                self._terminal_failure_event(job, outcome.get("reason") or "defer limit")
                self.logger.error("❌ задача #%d (%s): предусловие не выполнено (%s)",
                                  job_id, kind, outcome.get("reason"))
            else:
                self._counters["jobs_deferred"] += 1
                self.logger.info("⏸ задача #%d (%s) отложена: %s", job_id, kind,
                                 payload.get("reason") or "")
        elif verdict == "need_confirm":
            self.store.set_need_confirm(job_id, token, payload)
            self._counters["jobs_need_confirm"] += 1
            self.logger.info("⚠️ задача #%d (%s) ждёт подтверждения: %s", job_id, kind,
                             payload.get("action") or "")
        else:
            outcome = self.store.fail(job_id, token, str(payload.get("error") or "unknown"),
                                      retry=bool(payload.get("retry", True)))
            if outcome.get("retried"):
                self._counters["jobs_retried"] += 1
                self.logger.warning("⚠️ задача #%d (%s): ошибка, повтор через %ss (%s)",
                                    job_id, kind, outcome.get("delay_seconds"),
                                    str(payload.get("error"))[:120])
            else:
                self._counters["jobs_failed"] += 1
                self._terminal_failure_event(job, str(payload.get("error") or "unknown"))
                self.logger.error("❌ задача #%d (%s) провалена окончательно: %s",
                                  job_id, kind, str(payload.get("error"))[:160])

    def _terminal_failure_event(self, job: dict, error: str) -> None:
        self.events.append("job_failed", {"id": int(job["id"]), "kind": str(job.get("kind")),
                                          "attempts": int(job.get("attempts") or 0),
                                          "error": str(error)[:200]})

    def _supervisor_loop(self) -> None:
        self.logger.info("🛰 супервизор устройства запущен (интервал %ss)", self.config["poll_interval"])
        while not self._stop.is_set():
            try:
                health = self.supervisor.poll()
                brain = health.get("brain") or {}
                if health.get("status") == "offline" and brain.get("fail_streak") in (1, 5, 20):
                    self.logger.warning("📵 устройство offline (подряд: %s, backoff %ss): %s",
                                        brain.get("fail_streak"), brain.get("backoff_seconds"),
                                        str(brain.get("last_error") or "")[:120])
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("❌ ошибка супервизора: %s", exc)
            self._stop.wait(float(self.config["poll_interval"]))

    def _reaction_loop(self) -> None:
        interval = float((self.config.get("reactions") or {}).get("interval", 30))
        self.logger.info("⚡ reaction engine запущен (интервал %ss)", int(interval))
        while not self._stop.is_set():
            try:
                result = self.reactions.tick()
                if result.get("status") == "ok" and result.get("matched"):
                    self.logger.info("⚡ реакции: обработано уведомлений %s, срабатываний %s",
                                     result.get("checked"), result.get("matched"))
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("❌ ошибка reaction engine: %s", exc)
            self._stop.wait(interval)

    # ------------------------------------------------------------- public

    def health(self) -> dict:
        started = parse_iso(self.started_at) or utc_now()
        return {"status": "ok", "version": __version__,
                "daemon": {"started_at": self.started_at,
                           "uptime_seconds": int((utc_now() - started).total_seconds()),
                           "busy_job": self._busy_job},
                "device": self.supervisor.health(),
                "queue": self.store.counts()}

    def metrics(self) -> dict:
        metrics = self.store.metrics()
        metrics.update({"status": "ok", "counters": dict(self._counters),
                        "started_at": self.started_at})
        return metrics

    def reactions_info(self) -> dict:
        enabled = bool((self.config.get("reactions") or {}).get("enabled", True))
        return {"status": "ok", "enabled": enabled, "rules": self.reactions.list_rules(),
                "state": self.reactions.state_summary()}

    def run(self) -> int:
        self.logger.info("🧠 Phone Brain v%s запускается (root=%s)", __version__, self.root)
        self.store.requeue_expired()
        purged = self.store.purge()
        if purged:
            self.logger.info("🧹 удалено %d старых задач очереди", purged)
        endpoint = self.api.start()
        self.logger.info("🌐 API слушает %s", endpoint)
        self.events.append("daemon_started", {"version": __version__, "api": endpoint})
        worker = threading.Thread(target=self._worker_loop, name="phone-brain-worker", daemon=True)
        supervisor = threading.Thread(target=self._supervisor_loop, name="phone-brain-supervisor",
                                      daemon=True)
        worker.start()
        supervisor.start()
        if (self.config.get("reactions") or {}).get("enabled", True):
            threading.Thread(target=self._reaction_loop, name="phone-brain-reactions",
                             daemon=True).start()

        def _shutdown(signum: int, _frame: Any) -> None:
            self.logger.info("🛑 сигнал %s — остановка Phone Brain", signum)
            self._stop.set()

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT, _shutdown)
        while not self._stop.is_set():
            self._stop.wait(1.0)
        self.events.append("daemon_stopping", {})
        self.api.stop()
        worker.join(timeout=5)
        supervisor.join(timeout=5)
        self.logger.info("👋 Phone Brain остановлен")
        return 0
