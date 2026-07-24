"""Fleet — связка DevicePool × bootstrap и монитор живости устройств.

* :func:`ensure_device` — гарантирует профилю устройство: сначала аренда
  из пула; при нехватке — создание нового AVD и запуск эмулятора через
  инъецируемые executor-функции (по умолчанию — реальный ``avdmanager`` /
  ``emulator`` / ``adb`` из Android SDK).
* :class:`PoolMonitor` — демон heartbeats: опрашивает ``adb devices``,
  шлёт heartbeats за живые serial-ы и периодически reap-ает молчащих.

Оба компонента тестируемы без Android SDK: все побочные эффекты —
через параметры-функции.
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
from typing import Callable, Dict, List, Optional

from .devices import DevicePool

DEFAULT_MAX_AVDS = 8  # защитный потолок auto-создаваемых AVD на пул

# --------------------------------------------------------------------------- #
# реальные executor-функции (используются по умолчанию)                        #
# --------------------------------------------------------------------------- #


def _run(cmd: str, timeout: int = 300) -> Dict:
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def default_create_avd(
    avd_name: str, package: str = "system-images;android-34;google_apis;x86_64"
) -> bool:
    """Создаёт AVD через avdmanager (без интерактива)."""
    result = _run(f"echo no | avdmanager create avd -n {avd_name} -k '{package}' --force")
    return result["code"] == 0


def default_start_emulator(avd_name: str) -> None:
    """Запускает headless-эмулятор в фоне."""
    subprocess.Popen(
        f"emulator @{avd_name} -no-window -no-audio " f"-gpu swiftshader_indirect",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def default_wait_serial(known_serials: list[str], timeout_s: int = 180) -> str | None:
    """Ждёт появления НОВОГО serial в `adb devices` и его загрузки."""
    known = set(known_serials)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = _run("adb devices")
        serials = [
            line.split("\t")[0]
            for line in result["stdout"].splitlines()[1:]
            if line.strip().endswith("device")
        ]
        new = [s for s in serials if s not in known]
        if new:
            serial = new[0]
            boot = _run(f"adb -s {serial} shell getprop sys.boot_completed")
            if boot["stdout"].strip() == "1":
                return serial
        time.sleep(2)
    return None


def default_list_devices() -> list[str]:
    """Serial-ы всех устройств в состоянии `device`."""
    result = _run("adb devices")
    return [
        line.split("\t")[0]
        for line in result["stdout"].splitlines()[1:]
        if line.strip().endswith("device")
    ]


# --------------------------------------------------------------------------- #
# ensure_device                                                               #
# --------------------------------------------------------------------------- #


def _avd_name(prefix: str, profile_key: str) -> str:
    """Имя AVD из ключа профиля: olx:work → aios-olx-work."""
    slug = re.sub(r"[^a-z0-9]+", "-", profile_key.lower()).strip("-")
    return f"{prefix}-{slug}"


def ensure_device(
    profile_key: str,
    pool: Optional[DevicePool] = None,
    profile_store=None,
    avd_prefix: str = "aios",
    create_avd: Optional[Callable[[str], bool]] = None,
    start_emulator: Optional[Callable[[str], None]] = None,
    wait_serial: Optional[Callable[[list[str]], str | None]] = None,
    list_devices: Callable[[], list[str]] = default_list_devices,
) -> Optional[Dict]:
    """Гарантирует профилю арендованное устройство.

    Сначала пробует аренду из пула; если свободных устройств нет —
    создаёт и запускает новый AVD, регистрирует его в пуле и арендует.

    Returns:
        Запись устройства (словарь DevicePool) или None при неудаче
        создания.
    """
    owns_pool = pool is None
    pool = pool or DevicePool()
    create_avd = create_avd or default_create_avd
    start_emulator = start_emulator or default_start_emulator
    wait_serial = wait_serial or default_wait_serial
    try:
        record = pool.lease(profile_key, profile_store=profile_store)
        if record is not None:
            return record

        # Квота auto-созданных AVD — защита от бесконтрольного бутстрапа.
        max_avds = pool.limit("max_avds", DEFAULT_MAX_AVDS)
        if max_avds is not None and pool.count_avds() >= max_avds:
            return None

        avd = _avd_name(avd_prefix, profile_key)
        known = list_devices()
        if not create_avd(avd):
            return None
        start_emulator(avd)
        serial = wait_serial(known)
        if not serial:
            return None
        pool.register(serial, avd_name=avd)
        return pool.lease(profile_key, serial=serial, profile_store=profile_store)
    finally:
        if owns_pool:
            pool.close()


# --------------------------------------------------------------------------- #
# PoolMonitor                                                                 #
# --------------------------------------------------------------------------- #


class PoolMonitor:
    """Демон heartbeats: adb-опрос → heartbeat, молчащие → offline."""

    def __init__(
        self,
        pool: Optional[DevicePool] = None,
        probe: Callable[[], list[str]] = default_list_devices,
        reap_after_s: float = 900.0,
    ):
        """Initialize PoolMonitor."""
        self.pool = pool or DevicePool()
        self._owns_pool = pool is None
        self.probe = probe
        self.reap_after_s = reap_after_s
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()

    def close(self) -> None:
        """Clean up resources."""
        self.stop()
        if self._owns_pool:
            self.pool.close()

    def run_once(self) -> Dict[str, object]:
        """Один цикл: heartbeats за живые устройства + reap молчащих."""
        alive = self.probe()
        seen = 0
        for serial in alive:
            seen += int(self.pool.heartbeat(serial))
        reaped = self.pool.reap_stale(self.reap_after_s)
        return {"alive_devices": len(alive), "heartbeats": seen, "reaped": reaped}

    def start(self, interval_s: float = 30.0) -> bool:
        """Фоновый цикл мониторинга с периодом interval_s."""
        if self._thread is not None and self._thread.is_alive():
            return False

        def _loop():
            while not self._stopped.wait(interval_s):
                try:
                    self.run_once()
                except Exception:
                    pass  # монитор не должен падать из-за разового сбоя adb

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
