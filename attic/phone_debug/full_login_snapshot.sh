#!/bin/bash
set -e
export ANDROID_SDK_ROOT=/opt/android-sdk
export PATH=$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/emulator:$PATH
DEV=emulator-5554
SLEEP="sleep"
SCRIPT_DIR=/root/AIOS

log() { echo "[$(date +%H:%M:%S)] $*"; }

# Wait for device fully booted
for i in $(seq 1 60); do
  if adb -s $DEV shell getprop sys.boot_completed 2>/dev/null | grep -q 1; then
    log "Emulator booted"
    break
  fi
  sleep 2
done

# Dismiss any system dialogs once (swipe/back)
adb -s $DEV shell input keyevent KEYCODE_BACK >/dev/null 2>&1
sleep 1

# Kill OLX/Chrome if running
adb -s $DEV shell am force-stop ua.slando 2>&1 || true
adb -s $DEV shell am force-stop com.android.chrome 2>&1 || true
sleep 1

# Grant POST_NOTIFICATIONS in advance so popup doesn't appear during login
adb -s $DEV shell pm grant ua.slando android.permission.POST_NOTIFICATIONS 2>/dev/null || true
log "Permissions granted"

# Launch OLX
log "Launching OLX"
adb -s $DEV shell am start -n ua.slando/pl.tablica2.app.startup.activity.StartupActivity 2>&1 || \
  adb -s $DEV shell monkey -p ua.slando -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 6

# Wait for WelcomeScreenActivity, click Login button
# The loginBtnExp bounds from earlier were [16,497][304,547] -> center (160,522)
log "Tap login button"
adb -s $DEV shell input tap 160 522
sleep 6

# Dismiss Chrome welcome if any ("Use without an account")
adb -s $DEV shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
if adb -s $DEV shell cat /sdcard/ui.xml | grep -q "Use without an account"; then
  log "Dismiss Chrome welcome"
  adb -s $DEV shell input tap 160 507
  sleep 4
fi

# Dismiss Chrome notifications "No thanks"
adb -s $DEV shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
if adb -s $DEV shell cat /sdcard/ui.xml | grep -q "No thanks"; then
  log "Dismiss Chrome notification prompt"
  adb -s $DEV shell input tap 137 524
  sleep 4
fi

# Tap phone field at ~(160, 550) (below the +380 prefix), type "959052288"
log "Type phone 959052288"
adb -s $DEV shell input tap 200 370
sleep 1
# Select all existing text and delete, then type
adb -s $DEV shell input keyevent KEYCODE_MOVE_END
sleep 0.3
for i in $(seq 1 20); do adb -s $DEV shell input keyevent KEYCODE_DEL; done
sleep 0.5
adb -s $DEV shell input text '959052288'
sleep 1

# Tap password field ~(160, 480), clear, type password
log "Type password"
adb -s $DEV shell input tap 160 480
sleep 1
adb -s $DEV shell input keyevent KEYCODE_MOVE_END
sleep 0.3
for i in $(seq 1 25); do adb -s $DEV shell input keyevent KEYCODE_DEL; done
sleep 0.5
# Use python helper to correctly type password with special chars
python3 $SCRIPT_DIR/adb_type.py $DEV '321456987Fff$$'
sleep 2

# Hide keyboard & press "Увійти" button at ~(160, 594)
log "Submit login"
adb -s $DEV shell input keyevent KEYCODE_BACK  # hide keyboard
sleep 1
adb -s $DEV shell input tap 160 594
sleep 18

# If notification permission appears (should be suppressed), tap Don't allow
adb -s $DEV shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
if adb -s $DEV shell cat /sdcard/ui.xml | grep -q "Don.t allow"; then
  log "Dismiss notification permission (fallback)"
  adb -s $DEV shell input tap 160 411
  sleep 4
fi

# Wait for main screen - check for "Головна" or "Що шукаєте"
log "Waiting for main/home screen"
for i in $(seq 1 30); do
  adb -s $DEV shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
  if adb -s $DEV shell cat /sdcard/ui.xml | grep -q "Головна"; then
    log "Main screen visible!"
    break
  fi
  sleep 2
done

# Screenshot final
adb -s $DEV shell screencap -p /sdcard/logged_in.png
adb -s $DEV pull /sdcard/logged_in.png $SCRIPT_DIR/screenshots/logged_in.png >/dev/null 2>&1
log "Screenshot saved to screenshots/logged_in.png"

# Save emulator snapshot "logged_in"
log "Saving emulator snapshot 'logged_in'"
adb -s $DEV emu avd snapshot save logged_in 2>&1 || true
sleep 5
log "Snapshot saved. Done!"
adb -s $DEV shell ps | grep -E "slando|emulator" | head -5 || true
