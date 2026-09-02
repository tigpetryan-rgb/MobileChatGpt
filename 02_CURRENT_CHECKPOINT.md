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
- Backend ↔ Android secure device registration + command bridge: **COMPLETE / VERIFIED**
- `open_url` + `share_text` safe device tools: **CURRENT CHECKPOINT**

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

# SECURE DEVICE BRIDGE — COMPLETE / VERIFIED

Backend source commit:

- `df7e34132046b18c3a72448ab79eace3c0dc91f3`
- Added Alembic revision `0004_device_bridge`
- Added durable `device_pairings`, `devices`, `device_commands`
- Pairing codes are short-lived and single-use; only SHA-256 hashes are stored
- Device bearer credentials are returned once and only SHA-256 hashes are stored server-side
- First bridge milestone is allowlisted to `open_app`
- Commands are linked 1:1 to validated Project Brain `ToolCall` records
- Idempotency key is mandatory for command enqueue
- Device-authenticated claim / heartbeat / complete / fail APIs implemented
- PostgreSQL claim uses row locking / skip-locked semantics
- stale command leases are requeued with bounded retry; exhausted delivery fails the linked ToolCall
- device revocation invalidates future claims

Backend verification:

- Workflow: `Backend CI`
- Run ID: `33620137773`
- Result: **SUCCESS**
- tests: **PASS**
- Python compile: **PASS**
- PostgreSQL Alembic migration smoke test through `0004_device_bridge`: **PASS**

Android bridge source commit:

- `452539c2bfd21b5cc9387aa4954e40bf2dda0797`
- one-time pairing client implemented
- device bearer token encrypted at rest with AES-GCM
- encryption key stored in Android Keystore
- raw bearer token is not stored in source/APK/plain SharedPreferences
- bearer-authenticated command claim implemented
- `DeviceCommandProcessor` executes through the existing safe `DeviceToolRegistry`
- command result is reported through DeviceCommand complete/fail, which deterministically updates the linked ToolCall
- Home screen exposes explicit Pair device / Sync command controls

Android build verification:

- Workflow: `Android CI`
- Run ID: `33620754007`
- Result: **SUCCESS**
- unit tests: **PASS**
- debug APK assemble: **PASS**
- Artifact: `mobile-chatgpt-debug-apk`
- Artifact ID: `9842840727`
- Artifact SHA-256: `ebcfe14d7cc43e8dd4909248c422b60d9b0ff8acbc05c0849d97086e5d74b6f8`

Security scan:

- Workflow: `Secret Pattern Guard`
- Run ID: `33620754093`
- Result: **SUCCESS**

Full backend → paired Android emulator → device action → backend completion verification:

- Workflow: `Android Emulator Runtime QA`
- Run ID: `33620754011`
- Source commit: `452539c2bfd21b5cc9387aa4954e40bf2dda0797`
- Result: **SUCCESS**
- backend startup + migration + runtime project seed: **PASS**
- emulator boot/install/instrumentation: **PASS**
- one-time device pairing: **PASS**
- Android Keystore encrypted credential persistence: **PASS**
- bearer-authenticated device command claim: **PASS**
- backend-delivered `open_app(com.android.settings)`: **PASS**
- DeviceCommand completion: **PASS**
- linked Project Brain ToolCall completion: **PASS**
- backend health after the run: **PASS**
- Evidence artifact: `android-runtime-qa-evidence`
- Evidence artifact ID: `9842936294`
- Evidence SHA-256: `ec88d99504ea1441833848643da9546b4915a2e2edaf2abacfcf7c1e6b0df770`

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## `open_url` + `share_text` SAFE DEVICE TOOLS

Goal: add the next two Android intent-based phone tools without broadening permissions or bypassing Project Brain / device-bridge validation.

## REQUIRED EXECUTION ORDER

1. Add strict pure validators for `open_url` and `share_text`.
2. `open_url` must accept only normalized `http://` or `https://` URLs; reject `javascript:`, `file:`, `content:`, `data:` and malformed/oversized values.
3. Implement `open_url` with Android `ACTION_VIEW`; no AccessibilityService and no browser automation.
4. `share_text` must accept bounded non-empty text and optional bounded chooser title.
5. Implement `share_text` with `ACTION_SEND` + Android chooser only. It may open the share sheet but must **not** auto-select a recipient or send content.
6. Register both tools in `DeviceToolRegistry` with explicit risk metadata.
7. Extend backend device-bridge allowlist/payload validation to exactly `open_app`, `open_url`, `share_text`.
8. Preserve mandatory idempotency and linked ToolCall semantics for backend-delivered commands.
9. Add Android unit tests and backend tests for valid/invalid payloads and unsupported schemes/actions.
10. Extend emulator QA with safe deterministic checks. Do not require an external network response; verify intent dispatch / controlled no-handler behavior and share-sheet launch behavior.
11. Keep release HTTPS/cleartext and no-secret invariants intact.
12. Record exact CI/emulator evidence here before moving to approval UI.

# DO NOT START YET

Until `open_url` + `share_text` pass build/runtime verification, do not begin:

- approval UI
- direct recipient selection or autonomous message sending
- contacts/reminders integration
- generic Accessibility-based autonomous UI control
- payments
- unrelated ChatGPT/MCP bridge expansion

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`approval UI → full vertical slice → ChatGPT/MCP bridge → automation/reliability/security → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
