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
- Android v0.1 emulator runtime verification: **PASS / VERIFIED**
- Backend ↔ Android secure device registration + command bridge: **CURRENT CHECKPOINT**

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

# ANDROID v0.1 — BUILD + RUNTIME VERIFIED

Implemented:

- Kotlin + Jetpack Compose project skeleton
- `ui / domain / data-backend / device` package separation
- Home / Projects screen
- Project Dashboard shell
- backend `/health`, `/projects`, `/projects/{id}/status` connectivity
- release HTTPS enforcement; debug-only HTTP local development
- no embedded secrets
- `DeviceTool` contract + `DeviceToolResult`
- `open_app` safe tool using official Android launch APIs/intents
- no AccessibilityService
- no `QUERY_ALL_PACKAGES` permission
- `DeviceToolExecutor` result-return path to Project Brain ToolCall complete/fail endpoints
- local pure Kotlin validator tests: **5/5 PASS**
- static safety/checkpoint checks: **PASS**

Clean GitHub Android build:

- Run ID: `33614336495`
- Source commit: `e5649e5f155655a4bf6d0e98a19644b18f1a6a1c`
- Artifact: `mobile-chatgpt-debug-apk`
- Artifact ID: `9840387743`
- Artifact SHA-256: `c8e4a2165b707a837367d769c0a1280a2e1cd7cbdec85a6fd8b34a742d44f879`

Real Android emulator runtime verification:

- Workflow: `Android Emulator Runtime QA`
- Run ID: `33618580459`
- Source commit: `69d9d8bbf32ee7f7b859c4e29a407c4aeb58c6c5`
- Result: **SUCCESS**
- API 36 x86_64 emulator boot: **PASS**
- Project Brain backend startup + Alembic seed: **PASS**
- `connectedDebugAndroidTest`: **PASS**
- Home → Project Dashboard: **PASS**
- backend `/health`, project list/status: **PASS**
- `open_app(com.android.settings)`: **PASS**
- malformed package rejection: **PASS**
- missing package controlled failure: **PASS**
- Project Brain ToolCall complete/fail reporting: **PASS**
- backend health after emulator test: **PASS**
- Evidence artifact: `android-runtime-qa-evidence`
- Evidence artifact ID: `9842116802`
- Evidence SHA-256: `6c2de67f76ece6e63ac1e7357ec15cadfd6bb5d5adfc181b901ec41fe87805cd`

Release invariant remains required and previously statically/build verified:
`usesCleartextTraffic=false`; release backend URLs must be HTTPS.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## BACKEND ↔ ANDROID SECURE DEVICE REGISTRATION + COMMAND BRIDGE

Goal: turn the locally callable Android `open_app` tool into a securely paired backend-delivered device command while preserving Project Brain ToolCall authority, idempotency, auditability and lease recovery.

## REQUIRED EXECUTION ORDER

1. Add durable `Device`, one-time `DevicePairing`, and `DeviceCommand` records via Alembic.
2. Store only hashes of pairing/device bearer credentials on the backend.
3. Make pairing codes short-lived and single-use.
4. Restrict the first bridge milestone to `open_app`; do not silently enable later tools.
5. Enqueue device work only through validated domain services that create/reuse Project Brain `ToolCall` records.
6. Require an idempotency key for every backend-delivered device command.
7. Add device-authenticated claim / heartbeat / complete / fail endpoints.
8. Add bounded stale-lease recovery; exhausted delivery must fail the linked ToolCall deterministically.
9. Add Android Keystore-backed device credential storage; never store a plaintext token in source/APK.
10. Add Android pairing + claim/execute/report client path.
11. Verify the full backend → paired Android emulator → `open_app` → backend completion vertical slice.
12. Record exact backend CI and emulator evidence here before marking the bridge complete.

# DO NOT START YET

Until the secure device bridge checkpoint passes, do not begin:

- `open_url` / `share_text`
- approval UI
- generic Accessibility-based autonomous UI control
- payments
- fully autonomous external messaging
- unrelated ChatGPT/MCP bridge expansion

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`open_url/share_text → approval UI → full vertical slice → ChatGPT/MCP bridge → reliability/security → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
