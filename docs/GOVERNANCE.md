# MobileChatGpt repository governance

## Canonical source of truth

For development of **MobileChatGpt**, the canonical planning/handoff state is the `main` branch of this GitHub repository.

Mandatory read order before project work:

1. `00_STRICT_EXECUTION_RULES.md`
2. `01_MASTER_PLAN.md`
3. `02_CURRENT_CHECKPOINT.md`

`AGENTS.md` repeats these instructions in agent-friendly form and is mandatory for repository-based work.

## Authority order

1. The user's latest explicit instruction.
2. `00_STRICT_EXECUTION_RULES.md`.
3. `01_MASTER_PLAN.md`.
4. `02_CURRENT_CHECKPOINT.md`.
5. Implementation specs, source code, tests and build notes.
6. Historical/archive references.

## Repository vs runtime state

- This GitHub repository owns MobileChatGpt **development** source code, roadmap governance, CI, checkpoint handoff and durable implementation history.
- Project Brain/PostgreSQL owns **runtime project state** for projects managed by the MobileChatGpt product.
- Chat history is not durable authority.
- Google Drive is retained only as archive/reference unless the user explicitly changes this governance again. Older Drive copies do not override newer GitHub canonical files.

## Execution rules

- Continue from the first incomplete canonical checkpoint.
- Do not repeat work already marked DONE.
- Do not change product direction, architecture, phase order, MVP scope or security boundaries without explicit user approval.
- Better ideas may be recorded as backlog proposals, but may not silently replace the plan.
- A checkpoint is DONE only after implementation exists and defined practical validation/tests pass.
- Update `02_CURRENT_CHECKPOINT.md` in the same development flow whenever the canonical checkpoint changes.
- High-impact or irreversible actions require the approval policy defined by the project.

## Main branch rule

Canonical planning changes must land on `main` (directly or through a merged PR). A branch/PR draft is not canonical until merged.
