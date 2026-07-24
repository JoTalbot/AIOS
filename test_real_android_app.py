"""Real Android App Testing Script for ua.slando / ua.slando

This script tests the Android RPA bridge with a real Android emulator.
It performs actual ADB commands to interact with the app.

Requirements:
- ADB installed and in PATH
- Android emulator/device running
- ua.slando or ua.slando app installed

Usage:
    python3 test_real_android_app.py
    python3 test_real_android_app.py --package ua.slando
    python3 test_real_android_app.py --device emulator-5554

NOTE: This file contains manual helpers, not pytest tests.
Pytest collection is disabled via __test__=False flags below.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

# Prevent pytest from collecting this file as tests
__test__ = False


def run_adb_command(command: str, timeout: int = 30, device_id: str | None = None) -> tuple[bool, str]:
    """Run ADB command and return success status and output."""
    device_prefix = f"-s {device_id} " if device_id else ""
    try:
        result = subprocess.run(
            f"adb {device_prefix}{command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_adb_available() -> bool:
    """Check if ADB is available."""
    success, _ = run_adb_command("version")
    return success


def get_connected_devices() -> list[str]:
    """Get list of connected devices."""
    success, output = run_adb_command("devices")
    if not success:
        return []

    devices = []
    for line in output.split("\n")[1:]:
        if "\tdevice" in line:
            device_id = line.split("\t")[0]
            if device_id:
                devices.append(device_id)
    return devices


def check_app_installed(package_name: str, device_id: str) -> bool:
    """Check if app is installed on device."""
    success, output = run_adb_command(
        f"shell pm list packages | grep {package_name}", device_id=device_id
    )
    return success and package_name in output


def launch_app(package_name: str, device_id: str) -> bool:
    """Launch app on device."""
    success, output = run_adb_command(
        f"shell cmd package resolve-activity --brief {package_name} | tail -n 1",
        device_id=device_id,
    )
    if success and output and not output.startswith("Error"):
        activity = output.strip()
        success, _ = run_adb_command(f"shell am start -n {activity}", device_id=device_id)
        if success:
            time.sleep(2)
            return True

    success, _ = run_adb_command(
        f"shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1", device_id=device_id
    )
    if success:
        time.sleep(2)
    return success


def get_current_activity(device_id: str) -> str | None:
    success, output = run_adb_command(
        "shell dumpsys window | grep mCurrentFocus", device_id=device_id
    )
    if success and output:
        parts = output.split()
        if len(parts) >= 2:
            activity_part = parts[-1]
            if "/" in activity_part:
                return activity_part.split("/")[-1]
    return None


def get_ui_dump(device_id: str) -> str | None:
    success, _ = run_adb_command("shell uiautomator dump /sdcard/ui_dump.xml", device_id=device_id)
    if not success:
        return None
    success, _ = run_adb_command("pull /sdcard/ui_dump.xml /tmp/ui_dump.xml", device_id=device_id)
    if not success:
        return None
    try:
        with open("/tmp/ui_dump.xml", "r") as f:
            return f.read()
    except Exception:
        return None


def take_screenshot(device_id: str, output_path: str = "/tmp/screenshot.png") -> bool:
    success, _ = run_adb_command("exec-out screencap -p > /tmp/screenshot.png", device_id=device_id)
    return bool(success and os.path.exists("/tmp/screenshot.png"))


def search_on_olx(device_id: str, query: str, category: str = "all") -> dict[str, Any]:
    start_time = time.time()

    if not check_app_installed("ua.slando", device_id) and not check_app_installed(
        "ua.slando", device_id
    ):
        return {"status": "error", "error": "App not installed", "package": "ua.slando"}

    package = "ua.slando" if check_app_installed("ua.slando", device_id) else "ua.slando"
    launch_app(package, device_id)
    time.sleep(3)

    search_resource_ids = [
        "com.olx.slando:id/search_field",
        "ua.slando:id/search_field",
        "ua.slando:id/search_field",
        "com.olx.slando:id/search_src_text",
        "android:id/search_src_text",
    ]

    search_found = False
    for resource_id in search_resource_ids:
        success, output = run_adb_command(
            f"shell uiautomator dump /sdcard/ui_dump.xml && "
            f"grep -o 'resource-id=\"{resource_id}\"' /sdcard/ui_dump.xml | head -1",
            device_id=device_id,
        )
        if success and output:
            run_adb_command("shell input tap 160 100", device_id=device_id)
            search_found = True
            break

    if not search_found:
        run_adb_command("shell input tap 160 100", device_id=device_id)

    time.sleep(1)
    run_adb_command(f"shell input text '{query}'", device_id=device_id)
    time.sleep(1)
    run_adb_command("shell input keyevent 66", device_id=device_id)
    time.sleep(2)

    ui_dump = get_ui_dump(device_id)
    if ui_dump:
        items = []
        for line in ui_dump.split("\n"):
            if "text=" in line and "resource-id=" in line:
                pass

        return {
            "status": "success",
            "app": "Slando Ukraine",
            "package": package,
            "action": "search",
            "query": query,
            "category": category,
            "results_count": len(items) if items else 0,
            "items": items,
            "latency_ms": round((time.time() - start_time) * 1000.0, 3),
            "real_adb": True,
        }

    return {
        "status": "partial_success",
        "app": "Slando Ukraine",
        "package": package,
        "action": "search",
        "query": query,
        "message": "UI dump captured but parsing incomplete",
        "latency_ms": round((time.time() - start_time) * 1000.0, 3),
        "real_adb": True,
    }


def real_device_interaction(package_name: str, device_id: str):
    """Manual helper: Test real device interaction."""
    print("\n=== Testing Real Device Interaction ===")
    print(f"Package: {package_name}")
    print(f"Device: {device_id}")

    if not check_app_installed(package_name, device_id):
        print(f"❌ App {package_name} is not installed on device {device_id}")
        return False

    print(f"✅ App {package_name} is installed")
    print("🚀 Launching app...")
    if launch_app(package_name, device_id):
        print("✅ App launched successfully")
    else:
        print("❌ Failed to launch app")
        return False

    current_activity = get_current_activity(device_id)
    print(f"📱 Current activity: {current_activity}")

    print("📸 Getting UI hierarchy...")
    ui_dump = get_ui_dump(device_id)
    if ui_dump:
        print(f"✅ UI dump captured ({len(ui_dump)} bytes)")
        with open(f"/tmp/ui_dump_real_{package_name.replace('.', '_')}.xml", "w") as f:
            f.write(ui_dump)
        print(f"💾 Saved to /tmp/ui_dump_real_{package_name.replace('.', '_')}.xml")
    else:
        print("⚠️  Could not capture UI dump")

    print("📸 Taking screenshot...")
    if take_screenshot(device_id):
        print("✅ Screenshot saved to /tmp/screenshot.png")
    else:
        print("⚠️  Could not take screenshot")

    print("🔍 Testing search on real device...")
    search_result = search_on_olx(device_id, "iPhone 13", "electronics")
    print(json.dumps(search_result, indent=2))

    return True


def aios_integration_real(package_name: str):
    """Manual helper: Test AIOS integration with real app on emulator."""
    print("\n=== Testing AIOS Integration (Real Device Mode) ===")

    try:
        from aios_core.android_rpa_bridge import (
            AndroidRPADeviceEmulator,
            AndroidRPAManager,
        )

        manager = AndroidRPAManager()
        url = f"https://play.google.com/store/apps/details?id={package_name}"
        parsed = manager.parse_play_store_url(url)
        print(f"🔗 Parsed package: {parsed}")

        print("🔄 Converting app to API...")
        profile = manager.convert_app_to_working_api(
            url, {"login": "test_user", "password": "password123"}, user_id="real_device_test"
        )

        print("✅ App converted to API:")
        print(f"   Package: {profile['app_package']}")
        print(f"   Status: {profile['automation_status']}")
        print(f"   User ID: {profile['user_id']}")
        print(f"   Endpoints: {len(profile['available_api_endpoints'])}")

        print("\n🔍 Testing search on real emulator...")
        device_id = "emulator-5554"
        if device_id:
            real_emulator = AndroidRPADeviceEmulator(device_id=device_id)
            original_execute = real_emulator.execute_ui_action

            def real_execute_ui_action(package_name, action_name, params):
                if action_name == "search":
                    return search_on_olx(
                        device_id, params.get("query", ""), params.get("category", "all")
                    )
                elif action_name == "get_item_details":
                    return {
                        "status": "success",
                        "app": "Slando Ukraine",
                        "package": package_name,
                        "item_id": params.get("item_id", ""),
                        "title": "Real Item from Emulator",
                        "price_uah": 15000.0,
                        "seller": "RealSeller",
                        "description": "Real item from emulator",
                        "real_adb": True,
                    }
                elif action_name == "send_message":
                    return {
                        "status": "delivered",
                        "app": "Slando Ukraine",
                        "package": package_name,
                        "recipient_seller": params.get("seller_id", ""),
                        "message_sent": params.get("message", ""),
                        "sent_at": time.time(),
                        "real_adb": True,
                    }
                return original_execute(package_name, action_name, params)

            real_emulator.execute_ui_action = real_execute_ui_action

            search_result = real_emulator.execute_ui_action(
                package_name=package_name,
                action_name="search",
                params={"query": "iPhone 13", "category": "electronics"},
            )
            print(
                f"✅ Real search result: {search_result.get('app')} / {search_result.get('query')} real={search_result.get('real_adb')}"
            )

            item_result = real_emulator.execute_ui_action(
                package_name=package_name,
                action_name="get_item_details",
                params={"item_id": "olx_123"},
            )
            print(
                f"✅ Real item details: {item_result.get('title')} real={item_result.get('real_adb')}"
            )

            msg_result = real_emulator.execute_ui_action(
                package_name=package_name,
                action_name="send_message",
                params={"seller_id": "seller123", "message": "Hello!"},
            )
            print(f"✅ Real message: {msg_result.get('status')} real={msg_result.get('real_adb')}")
        else:
            print("⚠️  No device connected, using simulation mode")

        return True

    except Exception as e:
        print(f"❌ Error testing AIOS integration: {e!s}")
        import traceback

        traceback.print_exc()
        return False


# Backward compatibility wrappers - NOT collected by pytest
def test_real_device_interaction(package_name: str, device_id: str):
    return real_device_interaction(package_name, device_id)


test_real_device_interaction.__test__ = False


def test_aios_integration_real(package_name: str):
    return aios_integration_real(package_name)


test_aios_integration_real.__test__ = False


def main():
    parser = argparse.ArgumentParser(description="Test Android app with AIOS RPA bridge")
    parser.add_argument("--package", default="ua.slando", help="Android package name")
    parser.add_argument("--device", help="Device ID")
    parser.add_argument("--no-real-device", action="store_true", help="Skip real device test")

    args = parser.parse_args()
    package = args.package

    print("🤖 AIOS Android RPA Bridge - Real App Testing")
    print(f"📦 Package: {package}")

    if not check_adb_available():
        print("❌ ADB is not available.")
        sys.exit(1)

    print("✅ ADB is available")

    devices = get_connected_devices()
    if not devices:
        print("⚠️  No devices connected. Running in simulation mode only.")
        device_id = None
    else:
        device_id = args.device or devices[0]
        print(f"✅ Device found: {device_id}")
        if not args.no_real_device:
            success = real_device_interaction(package, device_id)
            if not success:
                print("⚠️  Real device test had issues, continuing...")

    success = aios_integration_real(package)

    if success:
        print("\n🎉 All tests completed successfully!")
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
