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
- Approval Center / explicit approval UI: **CURRENT CHECKPOINT**

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
- backend `/health`, `/projects`, `/projects/{id}/status`
- release HTTPS enforcement; debug-only HTTP local development
- no embedded API secrets
- no AccessibilityService autonomous core
- no `QUERY_ALL_PACKAGES`
- safe Android intent-based DeviceTool registry

# SECURE DEVICE BRIDGE — COMPLETE / VERIFIED

Backend source commit:

- `df7e34132046b18c3a72448ab79eace3c0dc91f3`
- Alembic revision `0004_device_bridge`
- durable `device_pairings`, `devices`, `device_commands`
- pairing codes short-lived/single-use; hashes only stored
- device bearer tokens returned once; hashes only stored server-side
- mandatory command idempotency keys
- device-authenticated claim / heartbeat / complete / fail
- PostgreSQL row locking / skip-locked claims
- stale command lease recovery with bounded retries
- delivery exhaustion fails linked ToolCall deterministically
- device revocation invalidates future claims

Android bridge source commit:

- `452539c2bfd21b5cc9387aa4954e40bf2dda0797`
- one-time pairing client
- bearer token AES-GCM encrypted at rest
- encryption key in Android Keystore
- bearer-authenticated command claim
- command execution through safe `DeviceToolRegistry`
- DeviceCommand result deterministically updates linked ToolCall

Verification:

- Backend CI `33620137773`: **SUCCESS**
- Android CI `33620754007`: **SUCCESS**
- Secret Pattern Guard `33620754093`: **SUCCESS**
- Android Emulator Runtime QA `33620754011`: **SUCCESS**
- bridge APK artifact `9842840727`, SHA-256 `ebcfe14d7cc43e8dd4909248c422b60d9b0ff8acbc05c0849d97086e5d74b6f8`
- bridge runtime evidence `9842936294`, SHA-256 `ec88d99504ea1441833848643da9546b4915a2e2edaf2abacfcf7c1e6b0df770`

# SAFE INTENT TOOLS — COMPLETE / VERIFIED

Source commit:

- `2b340f9ee650b89b07caef30c6a452a1cd54b91c`

Implemented `open_url`:

- risk class R1 local/reversible
- Android `ACTION_VIEW` only
- only `http://` and `https://`
- strict host/port validation
- credentials rejected
- `javascript:`, `file:`, `content:`, `data:` rejected
- malformed/oversized/whitespace/control-character URLs rejected
- no browser automation
- controlled no-handler failure supported

Implemented `share_text`:

- risk class R1 local/reversible
- Android `ACTION_SEND` + `Intent.createChooser` only
- bounded non-empty text
- optional bounded chooser title
- exact payload keys only: `text`, optional `chooser_title`
- recipient/hidden action fields rejected
- **never selects a recipient and never sends automatically**

Bridge/backend constraints:

- exact allowlist is `open_app`, `open_url`, `share_text`
- all three safe tools must be `external_side_effect=false`
- idempotency + linked ToolCall semantics preserved
- hidden extra payload keys rejected server-side and Android-side

Verification:

- Backend CI run `33670054503`: **SUCCESS**
  - tests PASS
  - Python compile PASS
  - PostgreSQL Alembic migration smoke PASS
- Secret Pattern Guard run `33670054386`: **SUCCESS**
- Android CI run `33670054571`: **SUCCESS**
  - unit tests PASS
  - debug APK assemble PASS
  - artifact upload PASS
- APK artifact `9862185153`
- APK SHA-256 `af62d73d5752f59f32a3c7b137878fc3679bd2dbedd9704cae962d98d550a072`
- Android Emulator Runtime QA run `33670054546`: **SUCCESS**
  - backend startup/seed PASS
  - emulator boot/install/instrumentation PASS
  - unsafe URL local rejection PASS
  - hidden share recipient rejection PASS
  - backend-delivered `open_app` PASS
  - backend-delivered `open_url` ACTION_VIEW/controlled-handler semantics PASS
  - backend-delivered `share_text` chooser-only behavior PASS
  - linked ToolCall state reporting PASS
  - backend final health PASS
- runtime evidence artifact `9862322980`
- runtime evidence SHA-256 `85dd270db7eb17a0711b34a7e7290bd4f5f56672b7e93a586fef6134b35fd34a`

Release invariant remains mandatory:
`usesCleartextTraffic=false`; release backend URLs must use HTTPS.

# CURRENT NEXT CHECKPOINT — DO NOT SKIP

## APPROVAL CENTER / EXPLICIT APPROVAL UI

Goal: expose Project Brain's existing approval guardrail on Android so R2/R3/R4 actions can be reviewed and explicitly approved/rejected without weakening exact-payload, expiry, or single-use semantics.

## REQUIRED EXECUTION ORDER

1. Add Android approval domain models and BackendClient methods for listing approvals and explicit approve/reject actions.
2. Expose pending approval count/navigation from Home and add a dedicated Approval Center screen.
3. Each approval card must show at minimum: tool name, risk class, human preview, project/task reference when available, expiry and exact payload hash; show reason when available.
4. Add `payload_hash` and `reason` to the backend approval-list response if not already exposed; never expose secrets beyond the approved human preview/normalized contract.
5. Approval decisions must require an explicit user tap. Do **not** auto-approve based on viewing, navigation, autonomy level, or device pairing.
6. Approve/reject must call the existing Project Brain approval lifecycle endpoints and then refresh authoritative backend state.
7. Preserve expiry and single-use behavior: an expired/consumed approval must not be presented as actionable.
8. Provide clear pending/approved/rejected/expired/error UI states without executing the underlying side effect as part of the approval tap itself.
9. Add backend regression coverage for approval-list fields/status filtering if needed and Android unit tests for mapping/state logic.
10. Extend emulator QA: seed at least two pending approvals, open Approval Center, approve one and reject one via real Compose UI, then verify authoritative backend states.
11. Keep all existing safe-tool, secure bridge, release HTTPS and no-secret gates green.
12. Record exact CI/emulator evidence here before moving to the full approved-action vertical slice.

# DO NOT START YET

Until Approval Center passes build/runtime verification, do not begin:

- automatically executing an R2/R3/R4 action immediately after approval UI work
- direct recipient selection or autonomous messaging
- contacts/reminders expansion
- generic Accessibility-based autonomous UI control
- payments
- unrelated ChatGPT/MCP bridge expansion

# NEXT ONLY AFTER THIS CHECKPOINT PASSES

`approved-action full vertical slice → ChatGPT/MCP bridge → automation/reliability/security → Beta`

# RULE

Every future repository-based chat/agent must read `00_STRICT_EXECUTION_RULES.md`, `01_MASTER_PLAN.md` and this file before executing project work. Continue only from the first incomplete item above unless the user explicitly changes the plan.

`Շ` / `Շարունակի` = continue this first incomplete checkpoint immediately.
