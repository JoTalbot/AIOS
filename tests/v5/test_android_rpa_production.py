from aios_core.v5.skills.android.adb import ADBClient
from aios_core.v5.skills.android.appium import AppiumController


def test_adb_execution_flow():
    adb = ADBClient(device="AIOS_OLX")
    adb.connect()
    result = adb.execute("shell getprop")
    assert result["status"] == "queued"


def test_appium_session():
    appium = AppiumController()
    appium.start_session()
    assert appium.status()["session_active"] is True
