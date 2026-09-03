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
- Approved-action full vertical slice: **COMPLETE / VERIFIED**
- ChatGPT / MCP bridge: **CURRENT CHECKPOINT**

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

# APPROVED-ACTION FULL VERTICAL SLICE — COMPLETE / VERIFIED

Goal achieved: an explicit approval decision remains decision-only, and a later normal execution path consumes exactly that approval and executes through Project Brain → ToolCall → secure device bridge → Android DeviceToolRegistry without weakening exact-context, expiry, single-use, idempotency or existing safe-tool constraints.

Implementation commits:

- `875f900b21afa9fddbed5f1fd0e50773ab18013c` — bind approval consumption to exact execution context and PostgreSQL row lock
- `5e120cabb1ca95d2f5d0698fa374890d25d7bfdc` — enforce approval binding during ToolCall idempotent replay
- `70b34a1d4ea6950e800929d6e981ecc26543ff34` — preserve manual approval-consume compatibility without creating an execution bypass
- `1a41c804306d88622a6cf0b1dc1aae202e49c3c2` — regression coverage for exact approval execution binding
- `8aad3a75b5e57e787f99afa32bc38f6fe4f4dd86` — prove approved action through real Android emulator vertical slice
- `0def5808b94d50887e859c23c53837a7b1981146` — return clean HTTP 409 + rollback for invalid device approval binding
- `fee5177e5a40fea57ef0c0b440433d4f935e708d` — device-path regression test for changed-vs-exact approved payload

Verified semantics:

- approval consumption is bound to the same `project_id`, exact `task_id` including null-vs-non-null, `tool_name`, and exact normalized payload hash
- PostgreSQL first consumption locks the Approval row with `FOR UPDATE`, preventing concurrent double-consumption
- first valid execution consumes approval and creates the linked ToolCall/DeviceCommand in the same transaction; rollback does not strand an approval as consumed
- exact idempotent replay returns the same ToolCall/DeviceCommand without consuming again
- reused idempotency key with a different approval ID is rejected
- wrong project, wrong task, wrong tool, changed payload, expired and already-consumed approval paths are rejected
- invalid approval binding through the device enqueue API returns conflict/rollback rather than a server error and preserves the approval when execution was not created
- Approval Center approve tap still does not enqueue or execute anything
- the emulator proves `approved` immediately after UI approval, then a later separate enqueue changes it to `consumed`
- Android claims and executes the approved command only through the existing safe `DeviceToolRegistry`
- linked ToolCall completion/failure remains deterministic
- exact replay returns the same command/call and a subsequent device claim is idle, proving no duplicate execution
- this `open_url` approval gate is a vertical-slice proof only; normal product classification remains R1/local/reversible

Verification:

- approval-binding Backend CI `33710588762`: **SUCCESS**
- final Backend CI `33710938879`: **SUCCESS** on rerun after the first attempt failed before tests because GitHub Actions could not fetch the external Astral uv version manifest; successful rerun passed dependencies, tests, Python compile and PostgreSQL migration smoke
- final Secret Pattern Guard `33710938875`: **SUCCESS**
- Android CI `33710650198`: **SUCCESS** (`8aad3a75`; no Android source changed afterward)
- APK artifact `9876800838`, SHA-256 `7d470ca9a395769920f44353bee92a832106ee65c0e9f4c0c8592c6ca472fa43`
- implementation Android Emulator Runtime QA `33710649941`: **SUCCESS**
- implementation runtime evidence artifact `9876876889`, SHA-256 `e8bbb3c2ef32e4c8a13688c46886017534e153be3cef1aea902500594aaf1a4c`
- final Android Emulator Runtime QA `33710938934`: **SUCCESS** on final source head `fee5177e5a40fea57ef0c0b440433d4f935e708d`
- final runtime evidence artifact `9876957715`, SHA-256 `160584cb95400092fd73590657336c8782751b6c2859018e3a9f4d19fd3c0ce3`

Release invariant remains mandatory:
`usesCleartextTraffic=false`; release backend URLs must use HTTPS.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## CHATGPT / MCP BRIDGE

Goal: expose the durable Project Brain to ChatGPT through a narrow authenticated MCP / ChatGPT App bridge so ChatGPT can read project state and request existing validated project-control operations without becoming an alternate database writer, bypassing approval rules, or directly controlling unsafe device behavior.

This checkpoint implements Phase 6 from the master plan:

- MCP server / ChatGPT App
- project state read tools
- project control tools
- status / continue / approve flows
- approval/status surfaces
- deep links back to MobileChatGpt when device interaction is required

## REQUIRED EXECUTION ORDER

1. Inventory the existing repository for any MCP/ChatGPT bridge skeleton, reusable backend service boundaries and auth configuration before adding new architecture.
2. Define the smallest MCP surface around existing validated domain/API operations. Read tools first: list projects, read project/status/tasks and list actionable approvals.
3. Add project-control tools only through existing domain/API services: continue/resume a project and explicit approval decisions. MCP must not write database tables directly.
4. Preserve approval authority: MCP/ChatGPT must never auto-approve because a tool was invoked, a project is autonomous, or a device is paired. Any approval action exposed to ChatGPT must map to an explicit user-authorized approval operation and retain exact payload/expiry/single-use semantics.
5. Do not expose device bearer tokens, API secrets, hidden payload fields, raw credentials or unrestricted backend internals through MCP responses.
6. Keep actual Android actions on the existing secure device bridge. When device interaction is required, return project/action status and a safe MobileChatGpt handoff/deep-link surface rather than introducing remote UI automation.
7. Add authentication/authorization appropriate for the bridge boundary and reject unauthenticated control operations. Keep credentials outside source control.
8. Add deterministic MCP contract tests for tool schemas, project scoping, status/continue behavior, approval state handling, validation errors and forbidden direct/bypass actions.
9. Add an end-to-end bridge verification that reads a real Project Brain project, obtains status, invokes a permitted control operation, and confirms authoritative backend state through the same domain services.
10. Keep Backend CI, Android CI where Android source changes, Secret Pattern Guard, approval regression tests, secure device bridge and release HTTPS invariants green.
11. Record exact implementation commits, tests and integration evidence here before moving to automation/reliability/security.

# DO NOT START YET

Until the ChatGPT/MCP bridge passes its verification gates, do not begin:

- broad autonomous external integrations unrelated to the bridge
- direct recipient selection or autonomous messaging
- contacts/reminders expansion unless required by a later approved checkpoint
- generic Accessibility-based autonomous UI control
- payments or financial actions
- weakening approvals for convenience
- storing API keys/tokens in the repository or Android APK

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`automation / reliability / security hardening → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
