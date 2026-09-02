# 02 — CURRENT CHECKPOINT — READ BEFORE WORK

> Canonical handoff state for the MobileChatGpt development project.
> Read `00_STRICT_EXECUTION_RULES.md` and `01_MASTER_PLAN.md` first.

# PROJECT STATUS

- Phase 0 — Specification & Foundations: **COMPLETE**
- Backend deterministic Project Brain: **IMPLEMENTED**
- Backend v0.3: **COMPLETE / VERIFIED**
- GitHub monorepo migration: **COMPLETE**
- Android v0.1 implementation: **CREATED**
- Android v0.1 clean GitHub Gradle build: **PASS**
- Android v0.1 emulator/physical-device verification: **NOT YET COMPLETE**

# CANONICAL SOURCE CONTROL STATE

Repository: `tigpetryan-rgb/MobileChatGpt`

Canonical planning/handoff files on `main`:

1. `00_STRICT_EXECUTION_RULES.md`
2. `01_MASTER_PLAN.md`
3. `02_CURRENT_CHECKPOINT.md`
4. `AGENTS.md` — agent-facing mandatory read/continue instructions

Google Drive is archive/reference only. It is no longer required for a new repository-based chat/agent to recover the development plan.

# COMPLETED AND VERIFIED BACKEND

Implemented and validated:

- FastAPI + SQLAlchemy + Alembic architecture
- deterministic Project Brain state machine
- dependency resolver
- worker lease/recovery + bounded retries
- idempotent tool execution/replay protection
- approval lifecycle and autonomy guardrails
- project status engine
- guarded OpenAI Project Manager contract
- DB-leased Worker Agents
- token/concurrency budgets
- stale agent-run reservation recovery
- Manager agent restricted to validated domain services/tools; no direct DB table writes
- Backend v0.3 local verification: **38/38 tests PASS**, compile PASS, ZIP integrity PASS
- GitHub Backend CI clean runner verification: **SUCCESS**, including PostgreSQL/migration checks

# ANDROID v0.1 IMPLEMENTED

- Kotlin + Jetpack Compose project skeleton
- `ui / domain / data-backend / device` package separation
- Home / Projects screen
- Project Dashboard shell
- backend `GET /health` connectivity
- backend `GET /projects` connectivity
- backend `GET /projects/{id}/status` connectivity
- release HTTPS enforcement; debug-only HTTP local development
- no embedded secrets
- `DeviceTool` contract + `DeviceToolResult`
- `open_app` safe tool using official Android launch APIs/intents
- no AccessibilityService
- no `QUERY_ALL_PACKAGES` permission
- `DeviceToolExecutor` result-return path to Project Brain tool-call complete/fail endpoints
- local pure Kotlin validator tests: **5/5 PASS**
- static safety/checkpoint checks: PASS

# GITHUB / CI CHECKPOINT — COMPLETE

Private monorepo migration is complete.

Permanent CI workflows:

- Backend CI
- Android CI
- Secret Pattern Guard

Verified results:

- Backend CI: **SUCCESS**
- Secret Pattern Guard: **SUCCESS**
- Android SDK/API 37 setup: **SUCCESS**
- Gradle 9.5.0 setup: **SUCCESS**
- `testDebugUnitTest`: **SUCCESS**
- `assembleDebug`: **SUCCESS**
- debug APK upload: **SUCCESS**

Successful Android workflow run:

- Run ID: `33614336495`
- Source commit: `e5649e5f155655a4bf6d0e98a19644b18f1a6a1c`
- Artifact: `mobile-chatgpt-debug-apk`
- Artifact ID: `9840387743`
- Artifact SHA-256 digest: `c8e4a2165b707a837367d769c0a1280a2e1cd7cbdec85a6fd8b34a742d44f879`

CI bugs discovered and fixed during clean-run verification:

1. Backend workflow invalid floating `setup-uv@v10` reference → pinned to published `v10.0.1`.
2. Android API 37 SDK identifier → corrected to `platforms;android-37.0`.
3. Debug manifest cleartext override conflict → explicit debug-only manifest override; `main/release` remains `usesCleartextTraffic=false`.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## ANDROID EMULATOR / PHYSICAL DEVICE VERIFICATION FOR v0.1

The Gradle/build gate is now DONE. The next unfinished gate is real runtime verification on an emulator or physical Android device.

## REQUIRED EXECUTION ORDER

1. Obtain the successful `mobile-chatgpt-debug-apk` artifact from GitHub Actions, or build the same `main` commit in an Android-SDK-enabled environment.
2. Install the debug APK on an Android emulator or physical device.
3. Launch MobileChatGpt and verify app startup without crash.
4. Verify `Home → Projects → Project Dashboard` flow.
5. Configure a reachable Project Brain backend URL and verify `/health`.
6. Verify project list/status retrieval against the backend.
7. Verify `open_app` using a known launchable package, initially `com.android.settings`.
8. Verify malformed/invalid package names are rejected safely.
9. Verify a missing/non-launchable package returns a controlled failure result rather than crashing.
10. Verify DeviceTool result reporting reaches Project Brain complete/fail endpoints when backend is connected.
11. Verify release configuration still rejects cleartext HTTP backend URLs / `usesCleartextTraffic=false` remains the release invariant.
12. Record concrete emulator/device results in this file and commit them to `main`.

# DO NOT START YET

Until the emulator/device checkpoint above passes, do not begin these later product phases except for work strictly necessary to unblock verification:

- Backend ↔ Android device registration / secure command bridge
- `open_url` / `share_text`
- approval UI
- generic Accessibility-based autonomous UI control
- payments
- fully autonomous external messaging
- unrelated ChatGPT/MCP bridge expansion

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`Backend ↔ Android device registration + secure command bridge → open_url/share_text → approval UI → full vertical slice → ChatGPT/MCP bridge → reliability/security → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
