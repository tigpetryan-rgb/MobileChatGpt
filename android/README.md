# MobileChatGpt Android v0.1

Checkpoint implementation: **Android shell + secure/configurable backend client + first safe phone tool `open_app`**.

## Implemented

- Kotlin + Jetpack Compose application shell.
- Package structure: `ui`, `domain`, `data/backend`, `device`.
- Home/Projects screen backed by `GET /health` and `GET /projects`.
- Project Dashboard backed by `GET /projects/{id}/status`.
- `DeviceTool` contract and `DeviceToolResult` model.
- `open_app` tool with package-name validation.
- Android 13+ uses `PackageManager.getLaunchIntentSenderForPackage()`; older devices use launch intents with a package-scoped fallback.
- No AccessibilityService and no `QUERY_ALL_PACKAGES` permission.
- `DeviceToolExecutor` automatically reports a command result when the backend command carries a `toolCallId`.
- Backend client uses the existing Project Brain result/audit endpoints:
  - `POST /tool-calls/{id}/complete`
  - `POST /tool-calls/{id}/fail`
- Release manifest forbids cleartext traffic. Debug builds allow HTTP for local emulator development only.
- No API key or backend secret is embedded in the app.

## Current Android toolchain target

- Android Gradle Plugin: 9.3.0
- Gradle: 9.5.0
- Compose BOM: 2026.08.00
- compileSdk: 37 (required by Compose 1.12)
- targetSdk: 36 (meets Google Play requirement in effect from 2026-08-31)
- minSdk: 26
- Java: 17

## Backend URL

Default is a non-routable placeholder:

`https://api.example.invalid/`

Configure without editing source:

- Gradle property: `MOBILE_CHATGPT_BACKEND_URL=https://.../`
- or `local.properties`: `mobileChatGpt.backendUrl=https://.../`

For emulator-only local development, a debug build may use `http://10.0.2.2:8000/`. Release builds require HTTPS.

## Build

Open the folder in Android Studio Quail 4+ and sync. This artifact includes `gradle-wrapper.properties`, but this execution environment could not download the Gradle wrapper JAR or Android SDK because outbound DNS is unavailable. Once Gradle is available, generate/refresh the wrapper with Gradle 9.5.0 if needed and run:

```bash
./gradlew testDebugUnitTest assembleDebug
```

## Local validation completed here

The pure Kotlin `OpenAppPayloadValidator` was compiled with the installed Kotlin compiler and exercised by `tools/validator_smoke_test.kt`.

## Next checkpoint after Android build verification

Backend ↔ Android device registration + secure command bridge, then `open_url` / `share_text`, approval UI, and the full vertical slice.
