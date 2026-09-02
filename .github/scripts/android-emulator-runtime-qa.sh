#!/usr/bin/env bash
set -euxo pipefail

mkdir -p runtime-evidence

capture_evidence() {
  adb logcat -d > runtime-evidence/logcat.txt || true
  adb exec-out screencap -p > runtime-evidence/final-screen.png || true
  adb shell uiautomator dump /sdcard/runtime-window.xml || true
  adb pull /sdcard/runtime-window.xml runtime-evidence/window.xml || true
  adb shell dumpsys activity activities > runtime-evidence/activities.txt || true
  adb shell dumpsys window windows > runtime-evidence/windows.txt || true
  cp /tmp/mobile-chatgpt-backend.log runtime-evidence/backend.log || true
}

trap capture_evidence EXIT
adb logcat -c

gradle --no-daemon -p android \
  -PMOBILE_CHATGPT_BACKEND_URL=http://10.0.2.2:8000/ \
  connectedDebugAndroidTest
