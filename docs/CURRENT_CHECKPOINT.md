# Current checkpoint mirror

> This file is a convenience mirror. The Google Drive `02 – CURRENT CHECKPOINT – READ BEFORE WORK` document is authoritative.

## Completed

### Backend v0.3

- FastAPI + SQLAlchemy + Alembic
- deterministic Project Brain state machine
- dependency resolver
- worker lease/recovery + bounded retries
- idempotent tool execution protection
- approval lifecycle and autonomy guardrails
- project status engine
- guarded OpenAI Project Manager contract
- DB-leased Worker Agents
- token/concurrency budgets
- stale agent-run reservation recovery
- source checkpoint verification: 38/38 tests PASS

### Android v0.1 implementation

- Kotlin + Jetpack Compose skeleton
- UI/domain/data/device package separation
- Home / Projects
- Project Dashboard shell
- `/health`, `/projects`, `/projects/{id}/status` connectivity
- release HTTPS enforcement; debug-only local HTTP support
- no embedded secrets
- `DeviceTool` + `DeviceToolResult`
- `open_app` via official Android launch APIs/intents
- no AccessibilityService
- no `QUERY_ALL_PACKAGES`
- result-return path to Project Brain tool-call endpoints
- pure Kotlin validator: 5/5 PASS
- static safety checks: PASS

## First incomplete checkpoint — DO NOT SKIP

**Android build / device verification for v0.1**

Required order:

1. Run Android CI with compileSdk 37.
2. Make `testDebugUnitTest` PASS.
3. Make `assembleDebug` PASS.
4. Install debug APK on emulator/device.
5. Verify Home → Projects → Project Dashboard.
6. Verify backend `/health` + project status.
7. Verify `open_app` with `com.android.settings`.
8. Verify malformed package names are rejected.
9. Verify release config rejects cleartext HTTP backend URL.
10. Record actual results in Drive and update canonical `02`.

Do not start device registration/secure command bridge, `open_url/share_text`, approval UI, or later phases until this checkpoint passes unless the user explicitly changes the plan.
