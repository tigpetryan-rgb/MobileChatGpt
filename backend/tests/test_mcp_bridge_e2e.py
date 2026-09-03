import asyncio

from mcp.client import Client
from mcp.server.auth.provider import AccessToken

from app.mcp.auth import MCP_CONTROL_SCOPE, MCP_READ_SCOPE
from app.mcp.server import project_brain_mcp


def _run(coro):
    return asyncio.run(coro)


def test_mcp_bridge_reads_controls_and_re_reads_authoritative_project_state(client, monkeypatch):
    project = client.post(
        "/projects",
        json={
            "title": "MCP E2E Project",
            "goal": "Read state, resume safely, and confirm authoritative state",
        },
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "MCP E2E ready task"},
    ).json()
    assert client.post(f"/projects/{project['id']}/pause").status_code == 200

    token = AccessToken(
        token="e2e-test-token",
        client_id="chatgpt-e2e-client",
        scopes=[MCP_READ_SCOPE, MCP_CONTROL_SCOPE],
        subject="e2e-user",
        claims={"iss": "https://issuer.example"},
    )
    monkeypatch.setattr("app.mcp.auth.get_access_token", lambda: token)

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            listed = await mcp_client.call_tool("list_projects", {"limit": 20})
            assert listed.is_error is False
            assert any(row["id"] == project["id"] for row in listed.structured_content["projects"])

            before = await mcp_client.call_tool(
                "get_project_status",
                {"project_id": project["id"]},
            )
            assert before.is_error is False
            assert before.structured_content["project_status"] == "paused"
            assert before.structured_content["execution_state"] == "paused"

            continued = await mcp_client.call_tool(
                "continue_project",
                {"project_id": project["id"]},
            )
            assert continued.is_error is False
            assert continued.structured_content["project_status"] == "active"
            assert continued.structured_content["promoted_ready"] == 1
            assert continued.structured_content["status"]["next_tasks"][0]["id"] == task["id"]

            after = await mcp_client.call_tool(
                "get_project_status",
                {"project_id": project["id"]},
            )
            assert after.is_error is False
            assert after.structured_content["project_status"] == "active"
            assert after.structured_content["execution_state"] == "ready"
            assert after.structured_content["next_tasks"][0]["id"] == task["id"]

    _run(exercise())

    authoritative_project = client.get(f"/projects/{project['id']}")
    authoritative_status = client.get(f"/projects/{project['id']}/status")
    assert authoritative_project.status_code == 200
    assert authoritative_project.json()["status"] == "active"
    assert authoritative_status.status_code == 200
    assert authoritative_status.json()["execution_state"] == "ready"
    assert authoritative_status.json()["next_tasks"][0]["id"] == task["id"]
