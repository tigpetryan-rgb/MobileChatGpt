# AGENTS.md — MobileChatGpt mandatory project instructions

These instructions apply to every agent/chat working from this repository.

## Before doing any project work

Read, in this exact order:

1. `00_STRICT_EXECUTION_RULES.md`
2. `01_MASTER_PLAN.md`
3. `02_CURRENT_CHECKPOINT.md`

Do not start implementation until these three files have been read.

## Canonical authority

For the MobileChatGpt development project, the `main` branch of this GitHub repository is the canonical planning/handoff source of truth. Google Drive is archive/reference only and must not override newer GitHub canonical state.

Runtime project state for projects managed by the MobileChatGpt product belongs to Project Brain/PostgreSQL; do not confuse that runtime state with this repository's development roadmap.

## Execution rules

- Continue from the first incomplete item in `02_CURRENT_CHECKPOINT.md`.
- Do not repeat work already marked DONE.
- Do not skip a blocked/current checkpoint to start a later product phase unless the user explicitly changes the plan.
- Do not change product direction, architecture, phase order, MVP scope, security boundaries, or accepted technical decisions without explicit user approval.
- A better idea may be recorded as a proposal/backlog item but may not silently replace the plan.
- Prefer implementation, tests, CI evidence and artifacts over renewed brainstorming when the plan is sufficient.
- A checkpoint is DONE only after implementation exists and defined validation passes.
- Update `02_CURRENT_CHECKPOINT.md` whenever a meaningful checkpoint changes.
- Never commit API keys, tokens or plaintext secrets.
- Keep Android automation on supported APIs/intents/integrations; do not make AccessibilityService-based autonomous clicking the product core.
- High-impact/irreversible actions require the project's approval policy.

## Armenian continuation command

In this project, `Շ` / `Շարունակի` means: immediately continue the first incomplete canonical checkpoint without re-asking already-resolved questions.

## Conflict order

1. User's latest explicit instruction
2. `00_STRICT_EXECUTION_RULES.md`
3. `01_MASTER_PLAN.md`
4. `02_CURRENT_CHECKPOINT.md`
5. Implementation specs, source code, tests and build notes
6. Historical/archive material
