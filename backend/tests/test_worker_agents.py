from sqlalchemy import select

from app.agents.openai_worker_runtime import get_worker_runtime
from app.agents.worker_contracts import WorkerOutput, WorkerRunResult
from app.db.models import AgentRun, ProjectBudget, Task
from app.db.session import SessionLocal


class FakeWorkerRuntime:
    def __init__(self, output: WorkerOutput | None = None, error: Exception | None = None, tokens: int = 150):
        self.output = output
        self.error = error
        self.tokens = tokens
        self.context = None

    async def run_worker(self, *, context: dict) -> WorkerRunResult:
        self.context = context
        if self.error:
            raise self.error
        return WorkerRunResult(
            output=self.output,
            provider_run_ref="resp_worker_123",
            usage={"requests": 1, "input_tokens": 100, "output_tokens": self.tokens - 100, "total_tokens": self.tokens},
        )


def _project_task(client):
    project = client.post(
        "/projects",
        json={"title": "Worker Project", "goal": "Finish worker task", "autonomy_level": 2},
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Analyze input", "description": "Produce a concise analysis", "task_type": "analysis"},
    ).json()
    return project, task


def test_worker_agent_success_completes_leased_task_and_charges_budget(client):
    project, task = _project_task(client)
    fake = FakeWorkerRuntime(
        WorkerOutput(
            summary="Analysis complete.",
            success=True,
            rationale="The requested analysis was completed from the supplied context.",
            output_refs=["model-invented-ref-is-not-trusted"],
            requires_review=False,
        ),
        tokens=150,
    )
    client.app.dependency_overrides[get_worker_runtime] = lambda: fake
    try:
        response = client.post(
            f"/projects/{project['id']}/worker-agents/run-next",
            json={"worker_label": "analysis-a", "estimated_max_tokens": 1000},
        )
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["task_status"] == "done"
    assert body["provider_run_ref"] == "resp_worker_123"
    assert fake.context["task"]["id"] == task["id"]
    assert fake.context["constraints"]["external_side_effects_allowed"] is False

    with SessionLocal() as db:
        saved_task = db.get(Task, task["id"])
        assert saved_task.status == "done"
        assert saved_task.output_refs == [f"agent-run:{body['agent_run_id']}"]
        budget = db.get(ProjectBudget, project["id"])
        assert budget.used_tokens == 150
        assert budget.reserved_tokens == 0
        run = db.get(AgentRun, body["agent_run_id"])
        assert run.status == "completed"
        assert run.reserved_tokens == 0


def test_worker_agent_can_escalate_task_to_review(client):
    project, task = _project_task(client)
    fake = FakeWorkerRuntime(
        WorkerOutput(
            summary="Need human review.",
            success=False,
            rationale="Required information is ambiguous.",
            requires_review=True,
        )
    )
    client.app.dependency_overrides[get_worker_runtime] = lambda: fake
    try:
        response = client.post(
            f"/projects/{project['id']}/worker-agents/run-next",
            json={"estimated_max_tokens": 1000},
        )
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["task_status"] == "needs_review"
    with SessionLocal() as db:
        saved_task = db.get(Task, task["id"])
        assert saved_task.status == "needs_review"
        assert saved_task.lease_owner is None
        assert "ambiguous" in saved_task.blocked_reason


def test_worker_runtime_failure_releases_budget_and_retries_task(client):
    project, task = _project_task(client)
    fake = FakeWorkerRuntime(error=RuntimeError("provider unavailable"))
    client.app.dependency_overrides[get_worker_runtime] = lambda: fake
    try:
        response = client.post(
            f"/projects/{project['id']}/worker-agents/run-next",
            json={"estimated_max_tokens": 1000},
        )
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 503
    with SessionLocal() as db:
        saved_task = db.get(Task, task["id"])
        assert saved_task.retry_count == 1
        assert saved_task.status == "ready"
        budget = db.get(ProjectBudget, project["id"])
        assert budget.used_tokens == 0
        assert budget.reserved_tokens == 0
        run = db.scalar(select(AgentRun).where(AgentRun.project_id == project["id"]))
        assert run.status == "failed"
        assert run.reserved_tokens == 0


def test_worker_returns_idle_when_no_ready_task(client):
    project = client.post(
        "/projects",
        json={"title": "Empty", "goal": "Nothing yet", "autonomy_level": 2},
    ).json()
    fake = FakeWorkerRuntime(
        WorkerOutput(summary="unused", success=True, rationale="unused")
    )
    client.app.dependency_overrides[get_worker_runtime] = lambda: fake
    try:
        response = client.post(f"/projects/{project['id']}/worker-agents/run-next", json={})
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["status"] == "idle"
