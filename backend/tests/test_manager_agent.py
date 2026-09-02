from sqlalchemy import select

from app.agents.contracts import ManagerDecision, ManagerRunResult
from app.agents.openai_runtime import get_manager_runtime
from app.db.models import AgentRun, Task
from app.db.session import SessionLocal


class FakeManagerRuntime:
    def __init__(self, decision: ManagerDecision):
        self.decision = decision
        self.context = None
        self.instruction = None

    async def run_manager(self, *, context: dict, instruction: str | None = None) -> ManagerRunResult:
        self.context = context
        self.instruction = instruction
        return ManagerRunResult(
            decision=self.decision,
            provider_run_ref="resp_test_123",
            usage={"requests": 1, "input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )


def _create_project_and_task(client, *, autonomy_level: int = 2):
    project = client.post(
        "/projects",
        json={"title": "Manager Test", "goal": "Finish safely", "autonomy_level": autonomy_level},
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "First task", "description": "Do the first safe step"},
    ).json()
    return project, task


def test_manager_continue_applies_at_execute_safe(client):
    project, task = _create_project_and_task(client, autonomy_level=2)
    fake = FakeManagerRuntime(
        ManagerDecision(
            summary="Start the ready work.",
            action="continue_project",
            task_ids=[task["id"]],
            rationale="The task has no dependencies and is safe to make READY.",
            requires_user_attention=False,
            confidence=0.95,
        )
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: fake
    try:
        response = client.post(f"/projects/{project['id']}/manager/run", json={"apply": True})
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"]["action"] == "continue_project"
    assert body["application"]["applied"] is True
    assert body["provider_run_ref"] == "resp_test_123"
    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    assert tasks[0]["status"] == "ready"
    assert fake.context["project"]["id"] == project["id"]


def test_manager_recommendation_is_not_applied_below_autonomy_two(client):
    project, task = _create_project_and_task(client, autonomy_level=1)
    fake = FakeManagerRuntime(
        ManagerDecision(
            summary="Proceed.",
            action="continue_project",
            task_ids=[task["id"]],
            rationale="There is a runnable task.",
            confidence=0.8,
        )
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: fake
    try:
        response = client.post(f"/projects/{project['id']}/manager/run", json={"apply": True})
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["application"] == {
        "action": "continue_project",
        "applied": False,
        "reason": "autonomy_level_below_execute_safe",
    }
    assert client.get(f"/projects/{project['id']}/tasks").json()[0]["status"] == "planned"


def test_manager_dry_run_never_applies(client):
    project, task = _create_project_and_task(client, autonomy_level=4)
    fake = FakeManagerRuntime(
        ManagerDecision(
            summary="Proceed.",
            action="continue_project",
            task_ids=[task["id"]],
            rationale="A task is available.",
            confidence=0.9,
        )
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: fake
    try:
        response = client.post(f"/projects/{project['id']}/manager/run", json={"apply": False})
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["application"]["reason"] == "apply_disabled"
    assert client.get(f"/projects/{project['id']}/tasks").json()[0]["status"] == "planned"


def test_manager_cannot_reference_unknown_task_id(client):
    project, _ = _create_project_and_task(client, autonomy_level=4)
    fake = FakeManagerRuntime(
        ManagerDecision(
            summary="Proceed with a task.",
            action="continue_project",
            task_ids=["not-a-real-task"],
            rationale="Attempted invalid reference.",
            confidence=0.7,
        )
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: fake
    try:
        response = client.post(f"/projects/{project['id']}/manager/run", json={"apply": True})
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 502
    with SessionLocal() as db:
        run = db.scalar(select(AgentRun).where(AgentRun.project_id == project["id"]))
        assert run is not None
        assert run.status == "failed"
        assert "outside the project context" in run.error


def test_manager_run_is_visible_in_agent_run_feed(client):
    project, _ = _create_project_and_task(client, autonomy_level=2)
    fake = FakeManagerRuntime(
        ManagerDecision(
            summary="Nothing to do yet.",
            action="wait",
            rationale="Wait for another event.",
            confidence=0.75,
        )
    )
    client.app.dependency_overrides[get_manager_runtime] = lambda: fake
    try:
        response = client.post(
            f"/projects/{project['id']}/manager/run",
            json={"instruction": "Inspect and choose the next step.", "apply": True},
        )
    finally:
        client.app.dependency_overrides.clear()
    assert response.status_code == 200

    runs = client.get(f"/projects/{project['id']}/agent-runs").json()
    assert len(runs) == 1
    assert runs[0]["status"] == "completed"
    assert runs[0]["output"]["action"] == "wait"
    assert runs[0]["usage"]["total_tokens"] == 120
