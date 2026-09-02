from datetime import datetime, timezone

from app.agents.contracts import ManagerDecision, ManagerRunResult
from app.agents.openai_runtime import get_manager_runtime
from app.agents.openai_worker_runtime import get_worker_runtime
from app.agents.worker_contracts import WorkerOutput, WorkerRunResult
from app.db.models import AgentRun, ProjectBudget, Task
from app.db.session import SessionLocal


class ManagerRuntime:
    async def run_manager(self, *, context: dict, instruction: str | None = None):
        return ManagerRunResult(
            decision=ManagerDecision(
                summary="Wait.", action="wait", rationale="No mutation is needed.", confidence=0.8
            ),
            usage={"total_tokens": 321},
        )


class WorkerRuntime:
    async def run_worker(self, *, context: dict):
        return WorkerRunResult(
            output=WorkerOutput(summary="done", success=True, rationale="complete"),
            usage={"total_tokens": 100},
        )


def _project(client):
    return client.post(
        "/projects", json={"title": "Budget Project", "goal": "Stay within budget", "autonomy_level": 2}
    ).json()


def test_budget_endpoint_and_manager_usage_accounting(client):
    project = _project(client)
    initial = client.get(f"/projects/{project['id']}/budget")
    assert initial.status_code == 200
    assert initial.json()["used_tokens"] == 0

    updated = client.put(
        f"/projects/{project['id']}/budget",
        json={"max_total_tokens": 50000, "max_run_tokens": 5000, "max_concurrent_runs": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["max_run_tokens"] == 5000

    client.app.dependency_overrides[get_manager_runtime] = lambda: ManagerRuntime()
    try:
        run = client.post(
            f"/projects/{project['id']}/manager/run",
            json={"apply": True, "estimated_max_tokens": 1000},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert run.status_code == 200, run.text

    budget = client.get(f"/projects/{project['id']}/budget").json()
    assert budget["used_tokens"] == 321
    assert budget["reserved_tokens"] == 0


def test_budget_rejects_run_estimate_above_per_run_limit(client):
    project = _project(client)
    client.put(
        f"/projects/{project['id']}/budget",
        json={"max_total_tokens": 10000, "max_run_tokens": 500, "max_concurrent_runs": 2},
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: ManagerRuntime()
    try:
        response = client.post(
            f"/projects/{project['id']}/manager/run",
            json={"estimated_max_tokens": 1000},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 409
    assert "max_run_tokens" in response.text


def test_concurrency_budget_blocks_worker_before_persisting_lease(client):
    project = _project(client)
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "Task"}).json()
    client.put(
        f"/projects/{project['id']}/budget",
        json={"max_total_tokens": 10000, "max_run_tokens": 1000, "max_concurrent_runs": 1},
    )
    with SessionLocal() as db:
        db.add(
            AgentRun(
                project_id=project["id"],
                role="project_manager",
                status="running",
                started_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    client.app.dependency_overrides[get_worker_runtime] = lambda: WorkerRuntime()
    try:
        response = client.post(
            f"/projects/{project['id']}/worker-agents/run-next",
            json={"estimated_max_tokens": 500},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 409
    assert "concurrent" in response.text
    with SessionLocal() as db:
        saved_task = db.get(Task, task["id"])
        assert saved_task.status == "planned"
        assert saved_task.lease_owner is None
        budget = db.get(ProjectBudget, project["id"])
        assert budget.reserved_tokens == 0


def test_scheduler_recovery_releases_orphaned_agent_reservation(client):
    project = _project(client)
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "Orphaned"}).json()
    with SessionLocal() as db:
        budget = db.get(ProjectBudget, project["id"])
        budget.reserved_tokens = 700
        db.add(
            AgentRun(
                project_id=project["id"],
                task_id=task["id"],
                role="worker:generic",
                status="running",
                reserved_tokens=700,
                started_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    response = client.post("/scheduler/recover")
    assert response.status_code == 200
    assert response.json()["stale_agent_runs"] == 1
    with SessionLocal() as db:
        budget = db.get(ProjectBudget, project["id"])
        assert budget.reserved_tokens == 0
        run = db.query(AgentRun).filter(AgentRun.project_id == project["id"]).one()
        assert run.status == "failed"
        assert run.reserved_tokens == 0
