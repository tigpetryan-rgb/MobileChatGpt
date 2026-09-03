import asyncio
from datetime import datetime, timedelta, timezone

from mcp.client import Client
from mcp.server.auth.provider import AccessToken

from app.db.models import Approval
from app.db.session import SessionLocal
from app.mcp.auth import MCP_APPROVAL_SCOPE, MCP_CONTROL_SCOPE, MCP_READ_SCOPE
from app.mcp.server import project_brain_mcp


def _run(coro):
    return asyncio.run(coro)


def _seed_project(client):
    project = client.post(
        "/projects",
        json={
            "title": "MCP Control QA",
            "goal": "Verify scoped control operations",
            "autonomy_level": 2,
        },
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Resume through canonical service"},
    ).json()
    return project, task


def _access_token(*scopes: str) -> AccessToken:
    return AccessToken(
        token="test-token-not-a-secret",
        client_id="chatgpt-test-client",
        scopes=list(scopes),
        subject="user-123",
        claims={"iss": "https://issuer.example"},
    )


def _create_approval(client, project_id: str, suffix: str = "") -> dict:
    response = client.post(
        "/approvals",
        json={
            "project_id": project_id,
            "tool_name": "open_url",
            "risk_class": 2,
            "payload": {"url": f"https://example.com/{suffix}"},
            "human_preview": f"Open approved URL {suffix}",
            "reason": "MCP explicit decision QA",
            "ttl_seconds": 600,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_control_tools_reject_in_memory_unauthenticated_calls_without_mutation(client):
    project, _ = _seed_project(client)
    assert client.post(f"/projects/{project['id']}/pause").status_code == 200
    approval = _create_approval(client, project["id"], "unauth")

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            continued = await mcp_client.call_tool("continue_project", {"project_id": project["id"]})
            assert continued.is_error is True
            assert "Authentication required" in continued.content[0].text

            decided = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": approval["id"],
                    "payload_hash": approval["payload_hash"],
                    "decision": "approve",
                },
            )
            assert decided.is_error is True
            assert "Authentication required" in decided.content[0].text

    _run(exercise())

    assert client.get(f"/projects/{project['id']}").json()["status"] == "paused"
    with SessionLocal() as db:
        row = db.get(Approval, approval["id"])
        assert row.status == "pending"
        assert row.decided_at is None


def test_continue_project_requires_control_scope_and_uses_authoritative_state(client, monkeypatch):
    project, task = _seed_project(client)
    assert client.post(f"/projects/{project['id']}/pause").status_code == 200

    monkeypatch.setattr(
        "app.mcp.auth.get_access_token",
        lambda: _access_token(MCP_READ_SCOPE),
    )

    async def denied():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool("continue_project", {"project_id": project["id"]})
            assert result.is_error is True
            assert MCP_CONTROL_SCOPE in result.content[0].text

    _run(denied())
    assert client.get(f"/projects/{project['id']}").json()["status"] == "paused"

    monkeypatch.setattr(
        "app.mcp.auth.get_access_token",
        lambda: _access_token(MCP_READ_SCOPE, MCP_CONTROL_SCOPE),
    )

    async def allowed():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool("continue_project", {"project_id": project["id"]})
            assert result.is_error is False
            body = result.structured_content
            assert body["project_id"] == project["id"]
            assert body["project_status"] == "active"
            assert body["promoted_ready"] == 1
            assert body["status"]["execution_state"] == "ready"
            assert body["status"]["next_tasks"][0]["id"] == task["id"]

    _run(allowed())
    assert client.get(f"/projects/{project['id']}").json()["status"] == "active"
    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    assert tasks[0]["status"] == "ready"


def test_approval_decision_requires_scope_exact_hash_and_remains_decision_only(client, monkeypatch):
    project, _ = _seed_project(client)
    approval = _create_approval(client, project["id"], "approve")

    monkeypatch.setattr(
        "app.mcp.auth.get_access_token",
        lambda: _access_token(MCP_READ_SCOPE),
    )

    async def missing_scope():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": approval["id"],
                    "payload_hash": approval["payload_hash"],
                    "decision": "approve",
                },
            )
            assert result.is_error is True
            assert MCP_APPROVAL_SCOPE in result.content[0].text

    _run(missing_scope())

    monkeypatch.setattr(
        "app.mcp.auth.get_access_token",
        lambda: _access_token(MCP_READ_SCOPE, MCP_APPROVAL_SCOPE),
    )

    async def exact_binding():
        async with Client(project_brain_mcp) as mcp_client:
            changed = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": approval["id"],
                    "payload_hash": "0" * 64,
                    "decision": "approve",
                },
            )
            assert changed.is_error is True
            assert "payload hash does not match" in changed.content[0].text

            exact = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": approval["id"],
                    "payload_hash": approval["payload_hash"],
                    "decision": "approve",
                },
            )
            assert exact.is_error is False
            assert exact.structured_content["status"] == "approved"
            assert exact.structured_content["execution_started"] is False
            assert exact.structured_content["payload_hash"] == approval["payload_hash"]

            replay = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": approval["id"],
                    "payload_hash": approval["payload_hash"],
                    "decision": "approve",
                },
            )
            assert replay.is_error is True
            assert "not pending" in replay.content[0].text

    _run(exact_binding())

    with SessionLocal() as db:
        row = db.get(Approval, approval["id"])
        assert row.status == "approved"
        assert row.decided_by == "mcp:user-123"
        assert row.consumed_at is None


def test_approval_reject_and_expiry_use_existing_lifecycle_service(client, monkeypatch):
    project, _ = _seed_project(client)
    rejected = _create_approval(client, project["id"], "reject")
    expired = _create_approval(client, project["id"], "expired")
    with SessionLocal() as db:
        row = db.get(Approval, expired["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    monkeypatch.setattr(
        "app.mcp.auth.get_access_token",
        lambda: _access_token(MCP_READ_SCOPE, MCP_APPROVAL_SCOPE),
    )

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            reject_result = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": rejected["id"],
                    "payload_hash": rejected["payload_hash"],
                    "decision": "reject",
                },
            )
            assert reject_result.is_error is False
            assert reject_result.structured_content["status"] == "rejected"
            assert reject_result.structured_content["execution_started"] is False

            expired_result = await mcp_client.call_tool(
                "decide_approval",
                {
                    "approval_id": expired["id"],
                    "payload_hash": expired["payload_hash"],
                    "decision": "approve",
                },
            )
            assert expired_result.is_error is True
            assert "expired" in expired_result.content[0].text

    _run(exercise())

    with SessionLocal() as db:
        assert db.get(Approval, rejected["id"]).status == "rejected"
        assert db.get(Approval, expired["id"]).status == "expired"
