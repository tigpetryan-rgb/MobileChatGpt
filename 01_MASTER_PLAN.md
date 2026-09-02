# 01 — MobileChatGpt Master Plan — SOURCE OF TRUTH

> Canonical product/development roadmap. Current execution state is always in `02_CURRENT_CHECKPOINT.md`.
> Historical progress notes are preserved below; they do not override the current checkpoint.

# 1. Product Vision

MobileChatGpt-ը Android-first AI operating layer է, որը միավորում է երեք հիմնական դեր՝

- **AI assistant** — հասկանում է բնական լեզվով հրահանգները և կատարում հեռախոսի թույլատրելի գործողություններ։
- **Project Orchestrator** — պահում է երկարատև նախագծերի նպատակները, պլանը, վիճակը և ինքնուրույն շարունակում անվտանգ քայլերը։
- **ChatGPT Bridge** — համագործակցում է ChatGPT-ի հետ OpenAI API / ChatGPT App / MCP ինտեգրմամբ, որպեսզի նույն նախագծերը հնարավոր լինի ղեկավարել թե՛ MobileChatGpt-ից, թե՛ ChatGPT-ից։

Գլխավոր գաղափարը՝ օգտատերը չպետք է հիշի՝ որ chat-ում, ֆայլում կամ task-ում ինչ էր կատարվում։ Համակարգը պետք է պահի Project Brain-ը և «շարունակի նախագիծը» հրահանգից հասկանա ամբողջ ընթացքը։

# 2. Core User Outcomes

- Հեռախոսում գործողությունների կատարում՝ app բացել, URL/Maps բացել, share անել, reminder/calendar ստեղծել, կոնտակտ գտնել և այլ թույլատրելի device actions։
- Երկարատև նախագծերի վարում՝ `goal → plan → tasks → dependencies → results → next actions`։
- Միաժամանակ մի քանի worker agent/session գործարկել անկախ ենթաառաջադրանքների համար։
- Կանգ առած կամ ձախողված աշխատանքը checkpoint-ից շարունակել։
- ChatGPT-ի հետ project state-ի երկկողմ համագործակցություն։
- Բարձր ռիսկի գործողությունների համար user approval։
- Ցույց տալ՝ ինչ է հիմա կատարվում, ինչու, ինչ ավարտվեց և ինչ է հաջորդը։

# 3. Product Principles

1. Project state-ը chat history-ից անկախ է։
2. AI-ն հնարավորինս շատ աշխատանք է կատարում ինքնուրույն, բայց authority boundaries-ը միշտ հստակ են։
3. Safe actions-ը կարող են ավտոմատանալ, high-impact actions-ը պահանջում են approval։
4. Յուրաքանչյուր գործողություն պետք է ունենա audit trail։
5. Parallelism-ը օգտագործվում է միայն այնտեղ, որտեղ task dependencies-ը դա թույլ են տալիս։
6. Recovery-ը և resumability-ն core feature են։
7. ChatGPT-ը control surface է, բայց project backend-ը չպետք է կախված լինի մեկ chat-ից կամ device session-ից։

# 4. High-Level Architecture

## A. Android App

- Kotlin + Jetpack Compose UI
- Voice/Text command surface
- Project dashboard
- Approval center
- Device tool adapters
- Notifications
- Local secure cache
- WorkManager՝ persistent local jobs-ի համար

## B. Backend / Orchestrator

- Project Manager agent
- Planner
- Worker agent pool
- Task scheduler / dependency engine
- Project State database
- Checkpoint & recovery service
- Event log / audit trail
- Budget / rate / concurrency controls
- Notification service

## C. AI Layer

- OpenAI Responses API / Agents SDK
- Structured tool calling
- Multiple agent sessions
- Tool permissions
- Retry / evaluation / review loops

## D. ChatGPT Integration

- ChatGPT App / MCP server
- Project state read tools
- Project control tools
- Approval / status surfaces
- Deep links back to MobileChatGpt when device interaction is needed

Canonical architecture flow:

```text
User
 ↓
MobileChatGpt
 ↓
Project Manager AI
 ↓
Project Plan / DAG
 ↓
Worker sessions/agents
 ↓
Tools / Android / external services
 ↓
Project Brain PostgreSQL durable state
```

# 5. Project Brain — Core Data Model

## Project

- `id`
- `title`
- `goal`
- `success_criteria`
- `status`
- `autonomy_level`
- `priority`
- `created_at / updated_at`

## Plan

- `project_id`
- `version`
- `objective`
- `assumptions`
- `steps`
- `current_phase`
- `approved_at`

## Task

- `id`
- `project_id`
- `parent_task_id`
- `title`
- `description`
- `type`
- `status`
- `dependencies[]`
- `assigned_agent`
- `required_tools[]`
- `risk_level`
- `approval_policy`
- `retry_policy`
- `checkpoint`
- `output_refs[]`

## Project Memory

- decisions
- user preferences
- known facts
- constraints
- unresolved questions
- important artifacts
- summaries

## Event Log

- actor
- action
- timestamp
- input summary
- result
- cost
- approval reference
- error/retry info

# 6. Task State Machine

Primary flow:

`PLANNED → READY → RUNNING → DONE`

Additional states:

- `BLOCKED`
- `FAILED`
- `RETRYING`
- `WAITING_APPROVAL`
- `PAUSED`
- `CANCELLED`
- `NEEDS_REVIEW` where required by implementation

Rule: Project Manager-ը միայն READY task-երն է գործարկում, որոնց dependencies-ը DONE են։ Անկախ READY task-երը կարող են զուգահեռ գործարկվել։

# 7. Agent Roles

## Project Manager

- պահում է ամբողջ project state-ը
- որոշում է հաջորդ քայլերը
- բացում/lease է անում worker tasks
- միացնում է արդյունքները
- հետևում է blockers-ին և budget-ին
- **չի գրում DB tables ուղղակիորեն** — օգտագործում է validated domain services/tools

## Planner

- goal-ը բաժանում է փուլերի և tasks-ի
- կառուցում է dependency graph
- թարմացնում է plan version-ը, երբ replanning-ը թույլատրված/անհրաժեշտ է

## Research Agent

- որոնում, համեմատում, ամփոփում, source gathering

## Builder / Coder Agent

- code, config, tests, technical artifacts

## Device Agent

- Android/phone tools-ի միջոցով իրականացնում է թույլատրելի device գործողություններ

## Reviewer Agent

- ստուգում է worker արդյունքները, հակասությունները, completeness-ը և risk-ը

## Messenger / Integration Agent

- արտաքին ինտեգրացիաների actions՝ միայն համապատասխան permissions/approval-ով

# 8. Autonomy Levels

- **Level 0 — Observe**: միայն կարդում է և զեկուցում։
- **Level 1 — Suggest**: պլանավորում/առաջարկում է, բայց չի կատարում գործողություններ։
- **Level 2 — Execute Safe**: ինքնուրույն կատարում է safe/reversible գործողությունները։
- **Level 3 — Execute With Guardrails**: կատարում է նաև որոշ արտաքին գործողություններ նախապես սահմանված կանոններով, high-impact քայլերը կանգնեցնում է approval-ի համար։
- **Level 4 — Project Autopilot**: նախագիծը շարունակաբար առաջ է տանում հաստատված plan/budget սահմաններում, բայց irreversible/high-impact actions-ը մնում են user approval-ի տակ։

# 9. Approval Policy

Միշտ explicit approval պահանջող գործողությունների օրինակներ՝

- հաղորդագրություն/նամակ ուղարկել որպես օգտատեր
- հրապարակել կամ comment անել
- վճարում/գնում
- տվյալ կամ ֆայլ ջնջել
- account/security փոփոխություն
- անձնական տվյալ փոխանցել արտաքին ծառայության
- զանգ կամ այլ significant communication սկսել

Approval կարող է չպահանջվել՝

- research
- analysis
- draft ստեղծել
- read-only status checks
- internal project state update
- safe local navigation/open actions
- նախապես թույլատրված recurring workflow

Risk classes used by implementation:

- **R0** read-only → no approval
- **R1** low-impact local/reversible → auto under appropriate autonomy
- **R2** moderate external/user-visible → conditional/narrow preapproval
- **R3** high-impact communication/action → ALWAYS explicit approval in MVP
- **R4** destructive/security/financial → explicit approval or unsupported

Approval must match the exact normalized payload/hash, be unexpired and single-use by default.

# 10. Android Device Capabilities — Priority Order

## Tier A — Official APIs / Intents

- `open_app`
- `open_url`
- `open_maps`
- `share_text`
- `share_file`
- `find_contact`
- `create_calendar_event`
- `create_reminder/task`
- clipboard helpers
- notification handling՝ permission-ով

## Tier B — App-specific integrations

- deep links
- share targets
- public APIs / OAuth integrations

## Tier C — Restricted/Experimental Device Automation

Միայն այնտեղ, որտեղ policy/permissions-ը թույլ են տալիս։ **Core architecture-ը չի կառուցվում AccessibilityService-based autonomous clicking-ի վրա**։

# 11. ChatGPT Collaboration Model

ChatGPT-ից նախատեսվող հիմնական tools՝

- `list_projects()`
- `get_project_status(project_id)`
- `get_project_plan(project_id)`
- `continue_project(project_id)`
- `pause_project(project_id)`
- `create_task(project_id, ...)`
- `approve_action(action_id)`
- `reject_action(action_id)`
- `get_blockers(project_id)`
- `get_recent_results(project_id)`
- `open_on_device(project_id/task_id)`

ChatGPT-ը կարող է դառնալ project control UI, բայց execution state-ը պահվում է MobileChatGpt backend-ում։

# 12. MVP v1 — Build Scope

Առաջին իրական աշխատող տարբերակը պետք է ապացուցի գաղափարի ամբողջ vertical slice-ը, ոչ թե բոլոր feature-ները։

## MVP Features

1. Android chat UI՝ text command
2. OpenAI connection
3. 3 device tools՝ `open_app`, `open_url`, `share_text`
4. Project ստեղծում
5. Project goal + plan պահպանում
6. Task state machine
7. Project Manager + մեկ worker agent pattern
8. Safe parallel execution՝ առնվազն 2 անկախ task
9. Checkpoint + resume
10. Approval center մեկ high-impact action-ի համար
11. Project dashboard՝ progress / running / blocked / next
12. Basic ChatGPT/MCP bridge՝ project status կարդալու և `continue_project` կանչելու համար
13. Audit log

## MVP-ից դուրս առաջին փուլում

- ամբողջ հեռախոսը կառավարող generic UI automation
- մեծ agent marketplace
- տասնյակ integrations
- payments
- fully autonomous messaging
- complex multi-device sync

# 13. Development Roadmap

## Phase 0 — Specification & Foundations

- final MVP spec
- data model
- API contracts
- risk/approval matrix
- project lifecycle rules

## Phase 1 — Android Shell

- Compose app
- auth/session
- command UI
- local project dashboard
- backend connection

## Phase 2 — AI Tool Runtime

- OpenAI Responses/Agents integration
- structured tools
- tool result handling
- retries/errors

## Phase 3 — Project Brain

- project/plan/task DB
- task state machine
- memory summaries
- checkpoints
- event log

## Phase 4 — Orchestration

- manager agent
- worker sessions
- dependency scheduler
- parallel execution
- reviewer loop
- budget/concurrency guardrails

## Phase 5 — Device Actions

- official Android intents/tools
- permissions
- safe execution adapters
- approval flow

## Phase 6 — ChatGPT Bridge

- MCP server / ChatGPT App
- project read/control tools
- status/continue/approve flows

## Phase 7 — Reliability & Security

- failure recovery
- resume after restart
- idempotency
- secrets storage
- audit review
- abuse/risk tests

## Phase 8 — Beta

- real project templates
- telemetry
- UX refinement
- onboarding
- performance/cost optimization

# 14. Reliability Requirements

- Every task must be idempotent where possible.
- Every long-running task must persist checkpoint state.
- Agent output is not DONE until validation passes when validation is defined.
- Retries must be bounded.
- Parallel workers must have concurrency limits.
- Project Manager must never silently drop failed tasks.
- User must be able to pause/cancel a project.
- Scheduler uses DB-backed READY selection, leases, heartbeat, stale-lease recovery and bounded concurrency/retries for MVP.

# 15. Security Requirements

- API keys/secrets never stored in plaintext on device or committed to source.
- Least-privilege permissions.
- Tool-level authorization.
- Explicit approval for high-impact actions.
- Sensitive logs redacted.
- Every external side effect traceable to a task and approval policy.
- Project autonomy can be lowered instantly by the user.
- Never embed OpenAI API key in APK; backend owns provider credentials.

# 16. UX Requirements

Main screens:

- Home / Projects
- Project Dashboard
- Project Chat
- Running Tasks
- Approval Center
- Activity / Audit Log
- Settings / Autonomy / Permissions

Project Dashboard should answer immediately:

1. Ո՞րն է նպատակը։
2. Որտե՞ղ ենք հիմա։
3. Ի՞նչ է աշխատում հիմա։
4. Ի՞նչն է blocked կամ approval սպասում։
5. Ի՞նչ է հաջորդը։

# 17. Success Criteria for MVP

MVP-ը հաջող է, եթե օգտատերը կարող է՝

- ստեղծել նախագիծ բնական լեզվով
- հաստատել գեներացված plan-ը
- փակել հավելվածը և հետո շարունակել նույն project state-ից
- գործարկել առնվազն երկու անկախ worker task զուգահեռ
- տեսնել live progress-ը
- մեկ safe device action ավտոմատ կատարել
- մեկ high-impact action կանգնեցնել approval-ի համար
- ChatGPT-ից ստանալ project status և հրահանգել `continue_project`

# 18. Immediate Next Actions — Original Plan Baseline

Original implementation sequence:

1. Սահմանել MVP-ի վերջնական user stories-ը։
2. Սահմանել Project Brain database schema-ն։
3. Սահմանել tool contract-ները և approval matrix-ը։
4. Ընտրել backend stack-ը։
5. Ստեղծել Android project skeleton-ը։
6. Կապել OpenAI API-ն։
7. Ավելացնել առաջին phone tool-ը՝ `open_app`։
8. Կառուցել առաջին end-to-end flow-ը՝ `ստեղծիր project → plan → run task → execute device tool → save result → show next action`։

> Many of these items are already completed. Do not execute this historical list directly; use `02_CURRENT_CHECKPOINT.md` for current work.

# Current Strategic Decision

MobileChatGpt-ը **պարզ chatbot չէ**։ Այն սահմանվում է որպես՝

> AI operating layer for the phone + autonomous project manager + ChatGPT collaboration bridge.

# 19. Phase 0 Progress Update

Completed:

- ✓ MVP v1 User Stories defined
- ✓ Project Brain Data Model v1 defined
- ✓ Product & Architecture build-level specs created

Key implementation decision:

> Build the deterministic Project Brain state engine before connecting LLM-driven manager/worker agents. AI should orchestrate a reliable state machine, not replace it.

# 20. Phase 0 Completion

Completed:

- ✓ Tool Contracts v1
- ✓ Approval & Risk Matrix v1
- ✓ Backend Stack Decision v1
- ✓ Python/FastAPI/PostgreSQL selected for backend
- ✓ Durable project state confirmed as DB-owned, independent from model/chat sessions
- ✓ DB-backed deterministic scheduler/worker lease pattern selected for MVP
- ✓ ChatGPT bridge will reuse the same backend/domain contracts

Phase 0 status: **COMPLETE**.

Implementation order established:

1. Scaffold backend repository and Docker/dev environment.
2. Implement Project/Plan/Task/Dependency/Approval/Audit DB models and migrations.
3. Implement deterministic task state machine and transition guards.
4. Implement dependency resolver + worker lease/recovery loop.
5. Implement tool registry/authorization wrapper.
6. Add REST API + `/health` + project status endpoints.
7. Add tests for transitions, dependencies, idempotency and approval rules.
8. Only after these pass, connect the first OpenAI manager agent.

Architecture rule:

> OpenAI conversation/background/parallel execution features are execution primitives; Project Brain PostgreSQL state is the durable runtime source of truth.

# 21. Implementation Progress Baseline

## Backend v0

- FastAPI runnable service
- Project Brain core SQLAlchemy models + Alembic migration
- deterministic task state machine
- dependency readiness resolver
- approval/risk authorization engine
- project/task/continue/pause/approval APIs
- audit events
- Docker + PostgreSQL dev setup
- 13 automated tests passed
- compile check passed
- migration smoke test passed

## Backend v0.1–v0.3 evolution

Subsequent implementation added and validated:

- worker lease/recovery + bounded retries
- strict approval payload lifecycle
- tool-call idempotency/replay protection
- project status snapshot
- audit endpoint
- guarded OpenAI Project Manager contract
- DB-leased Worker Agents
- token reservation/settlement
- project-level concurrency/token budgets
- stale agent-run reservation recovery
- Backend v0.3: **38/38 tests PASS**, compile PASS, migration checks PASS

## Android v0.1 baseline

Implemented:

- Kotlin + Jetpack Compose skeleton
- Home / Projects
- Project Dashboard shell
- backend `/health`, `/projects`, `/projects/{id}/status` connectivity
- release HTTPS enforcement / debug-only local HTTP support
- no embedded secrets
- `DeviceTool` contract + `DeviceToolResult`
- `open_app` using official Android launch APIs/intents
- no AccessibilityService
- no `QUERY_ALL_PACKAGES`
- tool result return path to Project Brain
- pure Kotlin validator: 5/5 PASS

Current up-to-date implementation status and exact next step are maintained only in `02_CURRENT_CHECKPOINT.md`.
