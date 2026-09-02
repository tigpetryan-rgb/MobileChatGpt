# MobileChatGpt repository governance

## Mandatory execution order

Before project work, read the canonical Drive documents in this order:

1. `00 – START HERE – STRICT EXECUTION RULES`
2. `01 – MobileChatGpt Master Plan – SOURCE OF TRUTH`
3. `02 – CURRENT CHECKPOINT – READ BEFORE WORK`

## Authority order

1. The user's latest explicit instruction.
2. Canonical `00` strict execution rules.
3. Canonical `01` Master Plan.
4. Canonical `02` Current Checkpoint.
5. Implementation specs, build notes, then this repository mirror.

## Rules

- Continue from the first incomplete canonical checkpoint.
- Do not repeat work already marked DONE.
- Do not change product direction, architecture, phase order, or MVP scope without explicit user approval.
- Better ideas may be recorded as backlog proposals, but may not silently replace the plan.
- A checkpoint is DONE only after implementation exists, practical validation/tests pass, artifacts/state are stored, and canonical Drive state is updated.
- Chat history is not the durable source of truth.
- High-impact or irreversible actions require the approval policy defined by the project.

## Repository role

GitHub owns code history, review, CI and source control. Google Drive remains the canonical planning/handoff store until the project explicitly changes that rule.
