import asyncio

from mcp.client import Client

from app.mcp.server import MOBILE_APPROVAL_HANDOFF_URL, project_brain_mcp


def _run(coro):
    return asyncio.run(coro)


def test_pending_approval_read_exposes_only_exact_native_handoff(client):
    project = client.post(
        "/projects",
        json={
            "title": "MCP Handoff QA",
            "goal": "Open native Approval Center without executing anything",
        },
    ).json()
    approval = client.post(
        "/approvals",
        json={
            "project_id": project["id"],
            "tool_name": "open_url",
            "risk_class": 2,
            "payload": {"url": "https://example.com/handoff"},
            "human_preview": "Open handoff test URL",
            "ttl_seconds": 600,
        },
    ).json()

    async def exercise():
        async with Client(project_brain_mcp) as mcp_client:
            result = await mcp_client.call_tool(
                "list_pending_approvals",
                {"project_id": project["id"], "limit": 10},
            )
            assert result.is_error is False
            assert result.structured_content["handoff_url"] == MOBILE_APPROVAL_HANDOFF_URL
            assert result.structured_content["handoff_url"] == "mobilechatgpt://approvals"
            rows = result.structured_content["approvals"]
            assert [row["id"] for row in rows] == [approval["id"]]
            assert "payload" not in rows[0]
            assert "normalized_payload" not in rows[0]

    _run(exercise())

    # Reading the handoff metadata is navigation-only and does not decide or consume anything.
    assert client.get("/approval-center?status=pending").json()[0]["id"] == approval["id"]
