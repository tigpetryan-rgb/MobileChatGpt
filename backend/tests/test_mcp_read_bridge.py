import asyncio
from datetime import datetime, timedelta, timezone

from mcp.client import Client

from app.db.models import Approval
from app.db.session import SessionLocal
from app.mcp.server import project_brain_mcp


def _run(coro):
    return asyncio.run(coro)


def _seed_project(client):
    project = client.post(
        "/projects",
        json={
            "title": "MCP QA Project",
            "goal": "Verify the ChatGPT read bridge",
            "success_criteria": {"verified": True},
            "autonomy_level": 2,
        },
    ).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={
            "title": "Read project state",
            "risk_class": 1,
            "approval_policy": "conditional",
        },
    ).json()
    return project, task


def test_mcp_tool_catalog_has_safe_read_and_control_annotations(client):
    _seed_project(client)

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            tools = await mcp_client.list_tools()
            by_name = {tool.name: tool for tool in tools.tools}
            assert set(by_name) == {
                "list_projects",
                "get_project",
                "get_project_status",
                "list_project_tasks",
                "list_pending_approvals",
                "continue_project",
                "decide_approval",
            }
            read_names = {
                "list_projects",
                "get_project",
                "get_project_status",
                "list_project_tasks",
                "list_pending_approvals",
            }
            for name in read_names:
                tool = by_name[name]
                assert tool.annotations is not None
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.idempotent_hint is True
                assert tool.annotations.open_world_hint is False
                assert tool.output_schema is not None

            continue_tool = by_name["continue_project"]
            assert continue_tool.annotations is not None
            assert continue_tool.annotations.read_only_hint is False
            assert continue_tool.annotations.destructive_hint is False
            assert continue_tool.annotations.idempotent_hint is False
            assert continue_tool.annotations.open_world_hint is False

            approval_tool = by_name["decide_approval"]
            assert approval_tool.annotations is not None
            assert approval_tool.annotations.read_only_hint is False
            assert approval_tool.annotations.destructive_hint is True
            assert approval_tool.annotations.idempotent_hint is False
            assert approval_tool.annotations.open_world_hint is False
            assert approval_tool.output_schema is not None

    _run(exercise())


def test_mcp_reads_project_status_and_tasks_from_authoritative_backend_state(client):
    project, task = _seed_project(client)
    continued = client.post(f"/projects/{project['id']}/continue")
    assert continued.status_code == 200

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            listed = await mcp_client.call_tool("list_projects", {"limit": 10})
            assert listed.is_error is False
            projects = listed.structured_content["projects"]
            assert any(row["id"] == project["id"] for row in projects)

            detail = await mcp_client.call_tool("get_project", {"project_id": project["id"]})
            assert detail.is_error is False
            assert detail.structured_content["id"] == project["id"]
            assert detail.structured_content["goal"] == "Verify the ChatGPT read bridge"
            assert detail.structured_content["success_criteria"] == {"verified": True}

            status = await mcp_client.call_tool("get_project_status", {"project_id": project["id"]})
            assert status.is_error is False
            assert status.structured_content["project_id"] == project["id"]
            assert status.structured_content["execution_state"] == "ready"
            assert status.structured_content["next_tasks"][0]["id"] == task["id"]

            tasks = await mcp_client.call_tool("list_project_tasks", {"project_id": project["id"]})
            assert tasks.is_error is False
            assert tasks.structured_content["project_id"] == project["id"]
            assert tasks.structured_content["tasks"][0]["id"] == task["id"]
            assert tasks.structured_content["tasks"][0]["status"] == "ready"

    _run(exercise())


def test_mcp_pending_approvals_expose_preview_hash_not_raw_payload_and_skip_expired(client):
    project, _ = _seed_project(client)
    secret_value = "raw-secret-value-must-not-cross-mcp"
    created = client.post(
        "/approvals",
        json={
            "project_id": project["id"],
            "tool_name": "open_url",
            "risk_class": 2,
            "payload": {"url": "https://example.com", "hidden_test_value": secret_value},
            "human_preview": "Open the approved URL",
            "reason": "MCP safe approval preview test",
            "ttl_seconds": 600,
        },
    )
    assert created.status_code == 200
    actionable_id = created.json()["id"]

    expired = client.post(
        "/approvals",
        json={
            "project_id": project["id"],
            "tool_name": "open_url",
            "risk_class": 2,
            "payload": {"url": "https://example.com/expired"},
            "human_preview": "Expired approval",
            "ttl_seconds": 600,
        },
    ).json()
    with SessionLocal() as db:
        row = db.get(Approval, expired["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool(
                "list_pending_approvals",
                {"project_id": project["id"], "limit": 20},
            )
            assert result.is_error is False
            rows = result.structured_content["approvals"]
            assert [row["id"] for row in rows] == [actionable_id]
            assert rows[0]["human_preview"] == "Open the approved URL"
            assert len(rows[0]["payload_hash"]) == 64
            assert "normalized_payload" not in rows[0]
            assert "payload" not in rows[0]
            assert secret_value not in str(result.structured_content)

    _run(exercise())

    # Read-only MCP inspection does not mutate the lifecycle merely to hide an expired item.
    with SessionLocal() as db:
        assert db.get(Approval, expired["id"]).status == "pending"


def test_mcp_project_scoped_reads_fail_safely_for_unknown_project(client):
    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool("get_project_status", {"project_id": "missing-project"})
            assert result.is_error is True
            assert result.structured_content is None
            assert "Project not found" in result.content[0].text

    _run(exercise())
