#!/usr/bin/env python3
"""Type arbitrary text into focused Android field via adb, correctly escaping for sh -c.

Can be used as library:
    from adb_type import type_text
    type_text("emulator-5554", "password$123!")

Or CLI:
    python adb_type.py emulator-5554 "hello world"
"""
import subprocess
import sys

ADB = "/opt/android-sdk/platform-tools/adb"


def sh_single_quote(s: str) -> str:
    """Wrap string for POSIX sh single quotes."""
    return "'" + s.replace("'", "'\\''") + "'"


def type_text(serial: str, text: str, adb: str = ADB) -> bool:
    """Send text to the focused Android input field. Returns True on success."""
    if not text:
        return True
    # 'input text' treats space as separator, so replace spaces with %s
    sanitized = (text
                 .replace(" ", "%s")
                 .replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', '\\"'))
    # ADB shell takes a single command string; sh_single_quote protects special chars.
    shell_cmd = f"input text {sh_single_quote(sanitized)}"
    cmd = [adb, "-s", serial, "shell", shell_cmd]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and "error" not in (r.stderr or "").lower()
    except Exception:
        return False


def press_key(serial: str, keycode: int, adb: str = ADB) -> bool:
    try:
        r = subprocess.run([adb, "-s", serial, "shell", "input", "keyevent", str(keycode)],
                           capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    dev = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
    txt = sys.argv[2] if len(sys.argv) > 2 else ""
    ok = type_text(dev, txt)
    print(f"type_text dev={dev} len={len(txt)} ok={ok}")
    sys.exit(0 if ok else 1)
