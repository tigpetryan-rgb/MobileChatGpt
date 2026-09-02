# MobileChatGpt

Android-first AI operating layer for the phone, deterministic Project Brain, multi-agent orchestration, and a ChatGPT collaboration bridge.

## START HERE — canonical project instructions

This GitHub repository's `main` branch is the **canonical source of truth for MobileChatGpt development code, plan, governance and handoff state**.

Before any project work, read in this exact order:

1. [`00_STRICT_EXECUTION_RULES.md`](00_STRICT_EXECUTION_RULES.md)
2. [`01_MASTER_PLAN.md`](01_MASTER_PLAN.md)
3. [`02_CURRENT_CHECKPOINT.md`](02_CURRENT_CHECKPOINT.md)

Repository-based agents must also obey [`AGENTS.md`](AGENTS.md).

Google Drive is retained only as historical/archive reference and is not required to recover the current development plan.

See [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) for authority rules.

## Monorepo layout

```text
MobileChatGpt/
├── 00_STRICT_EXECUTION_RULES.md
├── 01_MASTER_PLAN.md
├── 02_CURRENT_CHECKPOINT.md
├── AGENTS.md
├── android/                 # Kotlin + Jetpack Compose client
├── backend/                 # FastAPI + Project Brain + agents
├── docs/                    # governance / supporting repository docs
└── .github/workflows/       # CI and safety checks
```

## Current implementation checkpoint

- Backend v0.3: implemented and verified (`38/38` source tests plus successful GitHub Backend CI).
- GitHub monorepo migration: complete.
- Secret Pattern Guard: successful.
- Android v0.1 clean GitHub CI: `testDebugUnitTest` **PASS**, `assembleDebug` **PASS**, debug APK artifact uploaded.
- **Current next checkpoint:** install/run the APK on an emulator or physical device and complete runtime verification.

See [`02_CURRENT_CHECKPOINT.md`](02_CURRENT_CHECKPOINT.md).

## Backend quick start

```bash
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run pytest -q
uv run uvicorn app.main:app --reload
```

Production state belongs in PostgreSQL. Do not commit `.env` files or API keys.

## Android CI verification

The Android workflow installs the Android API 37 platform and runs:

```bash
gradle --no-daemon -p android testDebugUnitTest
gradle --no-daemon -p android assembleDebug
```

CI build/test now passes. Emulator/device verification remains the active checkpoint.

## Security invariants

- Never commit `OPENAI_API_KEY` or other secrets.
- No API key is embedded in the Android app.
- Release backend URLs must use HTTPS.
- `open_app` uses official Android launch APIs/intents.
- No generic AccessibilityService-based autonomous clicking core.
- No `QUERY_ALL_PACKAGES` permission for the MVP `open_app` path.
- High-impact external actions remain behind explicit approval policy.
