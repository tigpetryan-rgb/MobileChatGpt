# Mobile ChatGpt Backend v0.3

Project Brain backend with guarded **Project Manager + Worker Agent** contracts, durable scheduler/recovery, approvals, idempotency, and project-level agent budgets.

## Architecture invariant

**PostgreSQL Project Brain state is the durable source of truth.** OpenAI Agents SDK runs are bounded decision/execution workers attached to that state. They never replace task state, approvals, leases, audit logs, or budgets.

## v0.3 capabilities

### Project Brain
- FastAPI + SQLAlchemy + Alembic
- Projects, plans, tasks, dependencies, approvals, checkpoints, agent runs, tool calls, audit events
- Deterministic task state machine and dependency resolver
- Explicit flush after readiness changes so same-transaction lease queries see newly READY tasks
- DB-backed worker leases, heartbeat, bounded retry, expired-lease recovery
- Exact one-time approval lifecycle
- Tool idempotency and replay detection
- Project status + audit feed

### Project Manager agent
- OpenAI Agents SDK lazy runtime adapter
- Structured `ManagerDecision`
- Unknown task IDs rejected
- Model output never mutates DB directly
- `continue_project` auto-apply only at autonomy >= 2
- `pause_project` auto-apply only at autonomy >= 3
- Dry-run support
- AgentRun input/output/usage/provider-ref/error persistence

### Worker agents
- DB leases exactly one READY task per worker-agent run
- Worker receives only project + leased-task context
- No external side-effect tools in this milestone
- Success → deterministic `DONE`
- Uncertain result → deterministic `NEEDS_REVIEW`
- Runtime failure → bounded retry path
- Model-supplied artifact refs are not trusted as durable refs; Project Brain stores the AgentRun reference
- Multiple processes can call `run-next` concurrently; PostgreSQL lease + budget guards bound parallelism

### Agent budgets
- `project_budgets` table
- max total tokens
- max tokens per run
- max concurrent agent runs
- used + reserved token accounting
- pre-dispatch reservation, post-run settlement
- stale/crashed agent reservation recovery

## Default models

Manager and worker defaults are configurable and currently set to `gpt-5.6-terra`.

## Core endpoints

```text
GET  /health
POST /projects
GET  /projects/{id}/status
GET  /projects/{id}/budget
PUT  /projects/{id}/budget
POST /projects/{id}/manager/run
POST /projects/{id}/worker-agents/run-next
GET  /projects/{id}/agent-runs
POST /scheduler/recover
```

## Local run

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Live agent runs additionally require a securely mounted server-side `OPENAI_API_KEY`. Never place that key in the Android application or source control.

## Validation

```bash
PYTHONPATH=. python -m pytest -q
```

Current result: **38/38 tests passing** + `compileall` passing + Alembic upgrade through `0003_project_budgets`.

Live OpenAI calls were not executed in this runtime because `OPENAI_API_KEY` is not mounted into the current process environment.

## Next milestone

1. Add read-only Project Brain tools to the manager agent.
2. Add controlled worker tool requests through the existing ToolCall/approval layer.
3. Build Android shell + secure backend client.
4. Implement the first device bridge tool: `open_app`.
5. Run end-to-end: project → manager → worker → device command → audit/result.
