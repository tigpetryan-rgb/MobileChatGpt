# MobileChatGpt

Android-first AI operating layer for the phone, deterministic Project Brain, multi-agent orchestration, and a ChatGPT collaboration bridge.

## Repository role

This repository is the **source-of-truth for code**.

The canonical product plan and execution state remain in Google Drive:

- `00 – START HERE – STRICT EXECUTION RULES`
- `01 – MobileChatGpt Master Plan – SOURCE OF TRUTH`
- `02 – CURRENT CHECKPOINT – READ BEFORE WORK`

Every implementation session must follow the execution rules before changing code. See [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md).

## Monorepo layout

```text
MobileChatGpt/
├── android/                 # Kotlin + Jetpack Compose client
├── backend/                 # FastAPI + Project Brain + agents
├── docs/                    # repository handoff / checkpoint mirrors
└── .github/workflows/       # CI and safety checks
```

## Current implementation checkpoint

- Backend v0.3: implemented and locally verified (`38/38` tests at the source checkpoint).
- Android v0.1: implementation created; local pure-Kotlin validator `5/5` passed.
- **Current blocking checkpoint:** Android Gradle build + device verification.
- GitHub Actions is prepared to run the Android SDK build in CI once this repository exists on GitHub.

See [`docs/CURRENT_CHECKPOINT.md`](docs/CURRENT_CHECKPOINT.md).

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

The Android workflow installs the Android SDK platform required by the project and runs:

```bash
gradle --no-daemon -p android testDebugUnitTest assembleDebug
```

Device/emulator verification remains required after CI compile/test passes.

## Security invariants

- Never commit `OPENAI_API_KEY` or other secrets.
- No API key is embedded in the Android app.
- Release backend URLs must use HTTPS.
- `open_app` uses official Android launch APIs/intents.
- No generic AccessibilityService-based autonomous clicking core.
- No `QUERY_ALL_PACKAGES` permission for the MVP `open_app` path.
- High-impact external actions remain behind explicit approval policy.
