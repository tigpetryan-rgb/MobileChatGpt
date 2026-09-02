#!/usr/bin/env sh
set -eu
if ! command -v gradle >/dev/null 2>&1; then
  echo "Gradle is not installed. Install Gradle 9.5.0 or open this project in Android Studio, then run this script again." >&2
  exit 1
fi
gradle wrapper --gradle-version 9.5.0 --distribution-type bin
