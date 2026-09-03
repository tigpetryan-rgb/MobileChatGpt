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
- ChatGPT / MCP bridge: **COMPLETE / VERIFIED**
- Reliability & Security hardening: **CURRENT CHECKPOINT**

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

# CHATGPT / MCP BRIDGE — COMPLETE / VERIFIED

Goal achieved: ChatGPT now has a narrow Project Brain bridge that can read authoritative project state and request explicitly scoped validated controls without becoming a second database writer, weakening approval authority, exposing credentials, or remotely automating Android UI.

Implementation commits:

- `58162bcd408c46a3806559b5076b78cdd7a549d3` — add Project Brain MCP package
- `fb18f25a5a4748cc0365ca7693213aba5dc10062` — add read-only Project Brain tools
- `40b92ebe1f379100fdd144f6a90f9b7020f49c15` — add stable MCP Python SDK dependency
- `6909897e1060a5bf3fe652558fe91b3daf9fccc8` — mount the MCP bridge into the existing FastAPI process
- `26d26d371f183d0e8efbd602c27f808818084e85` — expose controlled expected MCP lookup errors without leaking unexpected exceptions
- `1036f1c1d7a3cbab41aed19ac790de7289ce98bb` — share the canonical project continue control service
- `a49101e2bbc445ba28124056418e06206c3250c4` — keep terminal projects non-resumable
- `719236a5aea293da7c8dc950675a931cb0984763` — add OAuth introspection resource-server auth
- `53c0da4d1bf8aafd42ce96a6ec9001c6d7379338` — pin direct HTTP dependency used by token introspection
- `2baad556deb1f785b6a92a0fd58f85ca935e70b3` — add scoped project and approval controls
- `77322fc15911a56423cf12ff0be7931c165ce643` — serve the bridge with stateless HTTP auth context
- `035941c2807ae250009fe4cd8db646b99d41b7f8` — OAuth resource-server regression coverage
- `9973593adf8762a795989a4278bdad2048561309` — strict Android approval handoff route model
- `58e9e5725d74a5314d040b08c6fb9bdad2bad015` — route Android handoff intents
- `044a547a2f6e657ed56e5b0fb31c738133d92671` — navigate handoff to Approval Center without side effects
- `d285bd51d6adb0357057f50be9d7ce89d8e311f0` — register exact Android approval deep link
- `afcf6b2da266fae27afdfa6e494dd1d026aeedd7` — strict handoff parser tests
- `9b91796e2f3b4d22fbe0ed22a5de63331e3a86f5` — expose safe native approval handoff through MCP
- `999f698f8111c5127629a5726bb98f80572f0dcc` — prove the MCP handoff is navigation-only
- `7a4d764902f424ec733d610b93f92bde678b762e` — prove the native approval handoff through a real emulator VIEW intent
- `53363fc718202c60e36abdfd9f5859d3ff0311f6` — end-to-end MCP read → status → control → authoritative re-read verification

Verified semantics:

- read-only MCP surface is exactly `list_projects`, `get_project`, `get_project_status`, `list_project_tasks` and `list_pending_approvals`
- read responses expose only intended project/status/task data and safe approval preview/hash/reason metadata; raw normalized approval payloads, device bearer tokens, provider API keys and hidden credentials are not returned
- MCP handlers reuse canonical Project Brain services and do not become an alternate direct database-writing business layer
- `continue_project` requires `projects:control` and uses the shared project-control service
- approval decisions require `approvals:decide`, an exact approval ID and exact 64-character payload hash
- approval decisions call the existing approval lifecycle; they never enqueue or execute the underlying Android action and report `execution_started=false`
- unauthenticated control operations and missing scopes are rejected
- remote auth supports an OAuth resource-server boundary using token introspection with active-token, issuer, audience/resource and scope validation; partial auth configuration fails closed and credentials remain environment-only
- stateless MCP HTTP keeps auth context request-scoped
- MCP expected validation errors are controlled `ToolError` results while unexpected failures remain sanitized
- the safe native fallback is exactly `mobilechatgpt://approvals`; no approval ID, decision, payload or credential is embedded in the deep link
- Android accepts only the approval handoff host, and the parser rejects added path, query, fragment, user info, port, wrong scheme/host and malformed forms
- opening the deep link only navigates to Approval Center and refreshes state; it does not approve, reject, pair, sync, enqueue, claim or execute a device command
- emulator verification proves both approvals remain pending and device command claim remains idle immediately after the VIEW handoff
- real device actions still execute only through the previously verified secure device bridge and safe `DeviceToolRegistry`
- bridge E2E verifies `list_projects → get_project_status(paused) → continue_project → get_project_status(ready)` and confirms the same authoritative state through the normal HTTP backend
- release `usesCleartextTraffic=false`, approval single-use/exact-payload semantics, chooser-only `share_text`, no-secret and no-Accessibility invariants remain intact

Verification:

- read-only foundation Backend CI `33714720691`: **SUCCESS**
- read-only foundation Secret Pattern Guard `33714720675`: **SUCCESS**
- scoped control/auth Backend CI `33715273109`: **SUCCESS**
- scoped control/auth Secret Pattern Guard `33715273105`: **SUCCESS**
- final Backend CI `33715676368`: **SUCCESS** — tests, Python compile and PostgreSQL migration smoke all passed
- final Secret Pattern Guard `33715676299`: **SUCCESS**
- Android CI `33715633775`: **SUCCESS** — unit tests, debug APK build and upload passed
- APK artifact `9878420743`, SHA-256 `86e0f5d8a88870d430deddfbc5d113f1a85e3931d9b87bdea123675b438c3e96`
- deep-link Android Emulator Runtime QA `33715633785`: **SUCCESS**
- deep-link runtime evidence artifact `9878511896`, SHA-256 `c0cd13a577cab4736ea597de0c031e75bfd33b0d7821f8f654fc3d12ee90cb17`
- final combined Android Emulator Runtime QA `33715676302`: **SUCCESS** on source head `53363fc718202c60e36abdfd9f5859d3ff0311f6`
- final runtime evidence artifact `9878537210`, SHA-256 `7cd0d8e24a4c9685422ff2fc1a7699425d30402b92d4582a7011e5e445c57de1`

Release invariant remains mandatory:
`usesCleartextTraffic=false`; release backend URLs must use HTTPS.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## RELIABILITY & SECURITY HARDENING

Goal: complete Phase 7 by proving the Project Brain, MCP boundary and secure device bridge recover safely from failures/restarts, preserve idempotency and bounded execution, protect credentials/logs with least privilege, and leave a complete audit trail under abuse/risk testing before Beta.

## REQUIRED EXECUTION ORDER

1. Inventory remaining gaps against the Phase 7 reliability/security requirements before changing architecture.
2. Extend deterministic failure-recovery coverage across Project Brain scheduler/agents, MCP controls/auth and the secure device bridge.
3. Prove resume-after-restart behavior for durable project/task/approval/device-command state and long-running checkpointed work where implemented.
4. Audit and harden idempotency, concurrency races, lease expiry, heartbeat loss and bounded retry/exhaustion behavior; do not add unbounded retries or duplicate side effects.
5. Review secrets, redaction and least-privilege boundaries across backend config, MCP auth, Android credential storage, logs/audit data and CI; credentials must remain outside source control and APK plaintext.
6. Review audit traceability so project controls, approval decisions, tool/device execution, recovery and failures remain attributable to project/task/actor/policy where applicable.
7. Add abuse/risk regression tests for authorization bypass, approval bypass, malformed/hidden payloads, replay/race attempts, revoked/expired credentials, unsafe deep-link variants and direct-device-control attempts outside the secure bridge.
8. Verify DB-backed leases/checkpoints, bounded retries, concurrency/token budgets and stale-run recovery continue to satisfy the master-plan reliability requirements.
9. Keep Backend CI, Android CI when Android changes, Android Emulator Runtime QA where runtime behavior changes, Secret Pattern Guard, release HTTPS/no-cleartext, approval lifecycle and secure-device gates green.
10. Record exact implementation commits, CI runs, artifacts and hardening evidence here before moving to Beta.

# DO NOT START YET

Until Reliability & Security hardening passes its verification gates, do not begin:

- Beta templates or onboarding work
- broad telemetry/product analytics rollout
- UX polish unrelated to hardening
- performance/cost optimization unrelated to a concrete reliability issue
- broad autonomous external integrations
- direct recipient selection or autonomous messaging
- generic Accessibility-based autonomous UI control
- payments or financial actions
- weakening approval/auth/security boundaries for convenience

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`Beta — real project templates / telemetry / UX refinement / onboarding / performance & cost optimization`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
