#!/usr/bin/env python3
"""Type arbitrary text into focused Android field via adb, correctly escaping for sh -c."""
import subprocess, sys

DEV = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
text = sys.argv[2] if len(sys.argv) > 2 else ""

# Characters that are special inside single-quoted shell strings: single quote itself.
# Strategy: wrap text in sh single quotes, replacing each ' with '\''
def sh_single_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"

# After 'input text', adb shell invokes /system/bin/sh -c 'input text <arg>',
# and 'input text' uses its own small set of special characters: space -> %s, & -> &amp; etc.
# For Latin letters, digits, punctuation (including $!), it should accept verbatim.
# Spaces need to be converted to %s.
sanitized = text.replace(" ", "%s").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '\\"')

shell_cmd = f"input text {sh_single_quote(sanitized)}"
# Actually 'input text' treats its arg as-is (it doesn't re-shell), so we just need to pass the arg safely to adb shell.
# adb shell <command> joins args with spaces and hands to 'sh -c' on device.
# So pass as single arg to local subprocess which becomes the device shell command.

cmd = ["adb", "-s", DEV, "shell", f"input text {sh_single_quote(sanitized)}"]
r = subprocess.run(cmd, capture_output=True, text=True)
print(f"Sent text ({len(text)} chars). rc={r.returncode}")
if r.stderr.strip():
    print("stderr:", r.stderr[:300])
# Verify by dumping UI if requested
