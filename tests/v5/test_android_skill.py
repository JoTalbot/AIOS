from aios_core.v5.skills.android.adb import ADBClient
from aios_core.v5.skills.android.emulator import EmulatorController


def test_adb_client_connect():
    adb = ADBClient()
    assert adb.connect() is True


def test_emulator_state():
    emulator = EmulatorController()
    emulator.start()
    assert emulator.status()["running"] is True
