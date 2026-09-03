# 02 — CURRENT CHECKPOINT — READ BEFORE WORK

> Canonical handoff state for the MobileChatGpt development project.
> Read `00_STRICT_EXECUTION_RULES.md` and `01_MASTER_PLAN.md` first.

# PROJECT STATUS

- Phase 0 — Specification & Foundations: **COMPLETE**
- Backend deterministic Project Brain: **IMPLEMENTED**
- Backend v0.3 manager/workers/budgets: **COMPLETE / VERIFIED**
- GitHub monorepo migration: **COMPLETE**
- Android v0.1 shell/build/runtime: **PASS / VERIFIED**
- Backend ↔ Android secure device registration + command bridge: **COMPLETE / VERIFIED**
- `open_app`: **COMPLETE / VERIFIED**
- `open_url` + `share_text` safe device tools: **COMPLETE / VERIFIED**
- Approval Center / explicit approval UI: **COMPLETE / VERIFIED**
- Approved-action full vertical slice: **CURRENT CHECKPOINT**

# CANONICAL SOURCE CONTROL STATE

Repository: `tigpetryan-rgb/MobileChatGpt`

Mandatory planning/handoff files on `main`:

1. `00_STRICT_EXECUTION_RULES.md`
2. `01_MASTER_PLAN.md`
3. `02_CURRENT_CHECKPOINT.md`
4. `AGENTS.md`

Google Drive is archive/reference only. Repository state is canonical for continuation.

# VERIFIED FOUNDATIONS

Backend includes:

- FastAPI + SQLAlchemy + Alembic
- deterministic Project Brain state machine
- dependency resolver
- DB-backed worker leases/recovery + bounded retries
- idempotent ToolCall execution/replay protection
- exact-payload approval lifecycle and autonomy guardrails
- project status engine
- guarded OpenAI Project Manager contract
- DB-leased Worker Agents
- token/concurrency budgets
- stale agent-run reservation recovery
- manager restricted to validated domain services/tools; no direct DB writes

Android includes:

- Kotlin + Jetpack Compose
- `ui / domain / data-backend / device` separation
- Home / Projects screen
- Project Dashboard
- Approval Center
- backend `/health`, `/projects`, `/projects/{id}/status`
- release HTTPS enforcement; debug-only HTTP local development
- no embedded API secrets
- no AccessibilityService autonomous core
- no `QUERY_ALL_PACKAGES`
- safe Android intent-based DeviceTool registry

# SECURE DEVICE BRIDGE — COMPLETE / VERIFIED

Backend source commit: `df7e34132046b18c3a72448ab79eace3c0dc91f3`

Android bridge source commit: `452539c2bfd21b5cc9387aa4954e40bf2dda0797`

Key invariants:

- Alembic revision `0004_device_bridge`
- durable `device_pairings`, `devices`, `device_commands`
- pairing codes short-lived/single-use; hashes only stored
- device bearer tokens returned once; hashes only stored server-side
- Android bearer token AES-GCM encrypted at rest with key in Android Keystore
- mandatory command idempotency keys
- device-authenticated claim / heartbeat / complete / fail
- PostgreSQL row locking / skip-locked claims
- stale command lease recovery with bounded retries
- delivery exhaustion fails linked ToolCall deterministically
- device revocation invalidates future claims
- command execution only through the safe `DeviceToolRegistry`

Verification:

- Backend CI `33620137773`: **SUCCESS**
- Android CI `33620754007`: **SUCCESS**
- Secret Pattern Guard `33620754093`: **SUCCESS**
- Android Emulator Runtime QA `33620754011`: **SUCCESS**
- bridge APK artifact `9842840727`, SHA-256 `ebcfe14d7cc43e8dd4909248c422b60d9b0ff8acbc05c0849d97086e5d74b6f8`
- bridge runtime evidence `9842936294`, SHA-256 `ec88d99504ea1441833848643da9546b4915a2e2edaf2abacfcf7c1e6b0df770`

# SAFE INTENT TOOLS — COMPLETE / VERIFIED

Source commit: `2b340f9ee650b89b07caef30c6a452a1cd54b91c`

Implemented:

- `open_app` — validated Android package launch
- `open_url` — R1 local/reversible, `ACTION_VIEW`, only strict `http://` / `https://`
- `share_text` — R1 local/reversible, `ACTION_SEND` + chooser only

Safety invariants:

- exact bridge allowlist is `open_app`, `open_url`, `share_text`
- all three safe tools remain `external_side_effect=false`
- `share_text` never chooses a recipient and never sends automatically
- URL credentials / unsafe schemes / malformed URLs are rejected
- hidden/extra payload keys are rejected server-side and Android-side
- idempotency + linked ToolCall semantics are preserved

Verification:

- Backend CI `33670054503`: **SUCCESS**
- Secret Pattern Guard `33670054386`: **SUCCESS**
- Android CI `33670054571`: **SUCCESS**
- APK artifact `9862185153`, SHA-256 `af62d73d5752f59f32a3c7b137878fc3679bd2dbedd9704cae962d98d550a072`
- Android Emulator Runtime QA `33670054546`: **SUCCESS**
- runtime evidence artifact `9862322980`, SHA-256 `85dd270db7eb17a0711b34a7e7290bd4f5f56672b7e93a586fef6134b35fd34a`

# APPROVAL CENTER — COMPLETE / VERIFIED

Implementation source commit:

- `3953cf7a28f2c94e083311a036789b47fb4fc102` — `feat(approval): add explicit Android Approval Center`

Runtime stabilization commit:

- `389465da8135329d6e7d966a19feb150488c9921` — `test(runtime): tolerate recreated home before approval center`
- this changes runtime-test navigation tolerance only; it does not weaken approval semantics or production behavior

Implemented and verified:

- Android approval domain models + backend client list/approve/reject methods
- Home pending count + dedicated Approval Center navigation
- approval cards expose tool, risk class, human preview, project/task reference when available, expiry, exact payload hash and reason
- backend approval-center response exposes `payload_hash` and `reason`
- approve/reject always requires explicit user tap
- viewing/navigation/device pairing/autonomy never auto-approves
- approve/reject refreshes authoritative backend state
- expired/consumed approvals are not actionable
- approval tap changes approval state only; it does **not** execute the underlying action
- emulator seeds two approvals, rejects one and approves one through real Compose UI, then verifies authoritative backend state
- approved item remains unconsumed until a later execution path explicitly consumes it

Verification:

- Backend CI for implementation `33671288716`: **SUCCESS**
- implementation Android CI `33671288745`: **SUCCESS**
- final Android CI after runtime stabilization `33709660664`: **SUCCESS**
- final Secret Pattern Guard `33709660693`: **SUCCESS**
- final Android Emulator Runtime QA `33709660634`: **SUCCESS**
- final APK artifact `9876489879`, SHA-256 `a46208ec27867fbbca234b1306660c1d30a657547feba14cc9ccef56fedafe5c`
- final runtime evidence artifact `9876558337`, SHA-256 `3f164c386710b0b1afbe011fce2975f613a1a9e5267cef209eeb5bd3b1f935b5`

Release invariant remains mandatory:
`usesCleartextTraffic=false`; release backend URLs must use HTTPS.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## APPROVED-ACTION FULL VERTICAL SLICE

Goal: prove that an explicitly approved action is later executed through the normal Project Brain → ToolCall → secure device bridge pipeline, while preserving exact-context, exact-payload, expiry, single-use and idempotency semantics. Approval UI itself must remain decision-only.

For this checkpoint, use the existing `open_url` device path as an explicitly approval-gated test action. This is a vertical-slice proof and **does not reclassify `open_url` globally**; its normal product classification remains R1/local/reversible.

## REQUIRED EXECUTION ORDER

1. Strengthen approval consumption so an approval is bound to the same `project_id`, `task_id` (including null-vs-non-null), `tool_name`, and exact normalized payload/hash as the execution that consumes it.
2. Make first consumption race-safe/single-use under PostgreSQL concurrency (row lock or equivalent transactional guarantee).
3. Preserve idempotency semantics: an exact replay of an already-created approved ToolCall/DeviceCommand returns the same call/command without trying to consume again; a reused idempotency key with a different approval binding must fail.
4. Keep approval tap decision-only. Execution must begin only through a later normal execution/enqueue step after authoritative status is `approved`.
5. Wire the approved `open_url` vertical slice through the existing secure device-command path using the approval ID and exactly the approved payload.
6. Verify the first valid enqueue atomically consumes the approval and creates the linked ToolCall/DeviceCommand; if enqueue fails transactionally, approval must not be stranded as consumed.
7. Verify the Android device claims and executes the command through the existing safe `DeviceToolRegistry`, then reports linked ToolCall completion/failure deterministically.
8. Add regression tests for wrong project, wrong task, wrong tool, changed payload, already-consumed approval, expired approval, replay with same binding, and replay with a different approval binding.
9. Extend emulator QA from the existing approved-but-unconsumed `open_url` item: prove it is still approved immediately after the UI tap, then enqueue/execute it separately, verify it becomes `consumed`, verify linked ToolCall state, and verify replay does not execute/consume twice.
10. Keep `share_text` chooser-only behavior, safe-tool `external_side_effect=false`, secure bridge, release HTTPS, no-secret and no-Accessibility invariants green.
11. Record exact implementation commit, CI runs, APK/runtime artifacts and digests here before moving to ChatGPT/MCP bridge.

# DO NOT START YET

Until the approved-action vertical slice passes build/runtime verification, do not begin:

- ChatGPT/MCP bridge implementation
- direct recipient selection or autonomous messaging
- contacts/reminders expansion
- generic Accessibility-based autonomous UI control
- payments or financial actions
- unrelated feature expansion

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`ChatGPT/MCP bridge → automation/reliability/security → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
