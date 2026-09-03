import asyncio

import httpx
import pytest
from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

import app.mcp.auth as auth_module
from app.core.config import Settings
from app.mcp.auth import MCP_READ_SCOPE, IntrospectionTokenVerifier, build_mcp_auth


def _run(coro):
    return asyncio.run(coro)


def _settings(**overrides) -> Settings:
    values = {
        "mcp_auth_issuer_url": None,
        "mcp_resource_server_url": None,
        "mcp_token_introspection_url": None,
        "mcp_introspection_client_id": None,
        "mcp_introspection_client_secret": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_mcp_auth_is_optional_only_when_completely_unconfigured():
    assert build_mcp_auth(_settings()) is None


def test_mcp_auth_partial_configuration_fails_closed():
    with pytest.raises(RuntimeError, match="Incomplete MCP OAuth configuration"):
        build_mcp_auth(
            _settings(
                mcp_auth_issuer_url="https://issuer.example",
                mcp_resource_server_url="https://brain.example/mcp",
            )
        )


def test_mcp_auth_full_configuration_builds_required_read_scope():
    bundle = build_mcp_auth(
        _settings(
            mcp_auth_issuer_url="https://issuer.example",
            mcp_resource_server_url="https://brain.example/mcp",
            mcp_token_introspection_url="https://issuer.example/oauth/introspect",
            mcp_introspection_client_id="mobile-chatgpt-resource",
            mcp_introspection_client_secret="runtime-only-test-value",
        )
    )
    assert bundle is not None
    assert bundle.auth_settings.required_scopes == [MCP_READ_SCOPE]
    assert str(bundle.auth_settings.issuer_url).rstrip("/") == "https://issuer.example"
    assert str(bundle.auth_settings.resource_server_url).rstrip("/") == "https://brain.example/mcp"


def _patch_introspection(monkeypatch, payload: dict, status_code: int = 200):
    real_async_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://issuer.example/oauth/introspect")
        assert request.headers.get("authorization", "").startswith("Basic ")
        body = request.content.decode()
        assert "token=opaque-token" in body
        assert "resource=https%3A%2F%2Fbrain.example%2Fmcp" in body
        return httpx.Response(status_code, json=payload)

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        auth_module.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(transport=transport, **kwargs),
    )


def _verifier() -> IntrospectionTokenVerifier:
    return IntrospectionTokenVerifier(
        introspection_url="https://issuer.example/oauth/introspect",
        client_id="mobile-chatgpt-resource",
        client_secret="runtime-only-test-value",
        issuer_url="https://issuer.example",
        resource_server_url="https://brain.example/mcp",
    )


def test_introspection_verifier_accepts_active_issuer_and_resource_bound_token(monkeypatch):
    _patch_introspection(
        monkeypatch,
        {
            "active": True,
            "iss": "https://issuer.example",
            "aud": ["https://brain.example/mcp"],
            "scope": "projects:read projects:control approvals:decide",
            "client_id": "chatgpt-client",
            "sub": "user-123",
            "exp": 2_000_000_000,
        },
    )
    token = _run(_verifier().verify_token("opaque-token"))
    assert token is not None
    assert token.client_id == "chatgpt-client"
    assert token.subject == "user-123"
    assert token.resource == "https://brain.example/mcp"
    assert token.scopes == ["projects:read", "projects:control", "approvals:decide"]
    assert token.claims == {
        "iss": "https://issuer.example",
        "aud": ["https://brain.example/mcp"],
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"active": False},
        {
            "active": True,
            "iss": "https://wrong-issuer.example",
            "aud": "https://brain.example/mcp",
            "scope": "projects:read",
            "client_id": "chatgpt-client",
        },
        {
            "active": True,
            "iss": "https://issuer.example",
            "aud": "https://other-resource.example/mcp",
            "scope": "projects:read",
            "client_id": "chatgpt-client",
        },
        {
            "active": True,
            "iss": "https://issuer.example",
            "aud": "https://brain.example/mcp",
            "scope": {"unexpected": "shape"},
            "client_id": "chatgpt-client",
        },
        {
            "active": True,
            "iss": "https://issuer.example",
            "aud": "https://brain.example/mcp",
            "scope": "projects:read",
        },
    ],
)
def test_introspection_verifier_rejects_invalid_security_binding(monkeypatch, payload):
    _patch_introspection(monkeypatch, payload)
    assert _run(_verifier().verify_token("opaque-token")) is None


class StaticVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if token == "read-token":
            return AccessToken(token=token, client_id="reader", scopes=[MCP_READ_SCOPE])
        if token == "no-scope-token":
            return AccessToken(token=token, client_id="reader", scopes=[])
        return None


def test_streamable_http_auth_rejects_missing_token_and_missing_scope():
    mcp = MCPServer(
        "MCP Auth QA",
        token_verifier=StaticVerifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl("https://issuer.example"),
            resource_server_url=AnyHttpUrl("http://testserver/mcp"),
            required_scopes=[MCP_READ_SCOPE],
        ),
    )

    @mcp.tool()
    def ping() -> str:
        return "pong"

    mcp_app = mcp.streamable_http_app(stateless_http=True, host="testserver")

    async def exercise():
        transport = httpx.ASGITransport(app=mcp_app)
        async with mcp.session_manager.run():
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                unauthenticated = await client.post("/mcp", json={})
                assert unauthenticated.status_code == 401
                assert "www-authenticate" in unauthenticated.headers

                missing_scope = await client.post(
                    "/mcp",
                    json={},
                    headers={"authorization": "Bearer no-scope-token"},
                )
                assert missing_scope.status_code == 403

                authorized = await client.post(
                    "/mcp",
                    json={},
                    headers={"authorization": "Bearer read-token"},
                )
                assert authorized.status_code not in {401, 403}

    _run(exercise())
