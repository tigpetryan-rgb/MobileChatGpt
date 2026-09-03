from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import AnyHttpUrl

from app.core.config import Settings


MCP_READ_SCOPE = "projects:read"
MCP_CONTROL_SCOPE = "projects:control"
MCP_APPROVAL_SCOPE = "approvals:decide"


@dataclass(frozen=True)
class MCPAuthBundle:
    token_verifier: TokenVerifier
    auth_settings: AuthSettings


class IntrospectionTokenVerifier(TokenVerifier):
    """RFC 7662 verifier with strict issuer/resource binding.

    The authorization server is trusted only through the configured introspection
    endpoint. A token is accepted only when the response is active, issued by the
    configured issuer, and audience-bound to this MCP resource.
    """

    def __init__(
        self,
        *,
        introspection_url: str,
        client_id: str,
        client_secret: str,
        issuer_url: str,
        resource_server_url: str,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.introspection_url = introspection_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer_url = issuer_url.rstrip("/")
        self.resource_server_url = resource_server_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    self.introspection_url,
                    data={"token": token, "resource": self.resource_server_url},
                    auth=(self.client_id, self.client_secret),
                    headers={"accept": "application/json"},
                )
        except httpx.HTTPError:
            return None

        if response.status_code != 200:
            return None
        try:
            payload: dict[str, Any] = response.json()
        except ValueError:
            return None

        if payload.get("active") is not True:
            return None

        issuer = str(payload.get("iss") or "").rstrip("/")
        if issuer != self.issuer_url:
            return None

        audience = payload.get("aud")
        if isinstance(audience, str):
            audiences = {audience.rstrip("/")}
        elif isinstance(audience, list):
            audiences = {str(item).rstrip("/") for item in audience}
        else:
            audiences = set()
        if self.resource_server_url not in audiences:
            return None

        raw_scope = payload.get("scope", "")
        if isinstance(raw_scope, str):
            scopes = [scope for scope in raw_scope.split() if scope]
        elif isinstance(raw_scope, list):
            scopes = [str(scope) for scope in raw_scope if str(scope)]
        else:
            return None

        client_id = str(payload.get("client_id") or payload.get("azp") or "")
        if not client_id:
            return None

        expires_at = payload.get("exp")
        if expires_at is not None:
            try:
                expires_at = int(expires_at)
            except (TypeError, ValueError):
                return None

        return AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            resource=self.resource_server_url,
            subject=str(payload["sub"]) if payload.get("sub") is not None else None,
            claims={"iss": issuer, "aud": audience},
        )


def build_mcp_auth(settings: Settings) -> MCPAuthBundle | None:
    values = {
        "MCP_AUTH_ISSUER_URL": settings.mcp_auth_issuer_url,
        "MCP_RESOURCE_SERVER_URL": settings.mcp_resource_server_url,
        "MCP_TOKEN_INTROSPECTION_URL": settings.mcp_token_introspection_url,
        "MCP_INTROSPECTION_CLIENT_ID": settings.mcp_introspection_client_id,
        "MCP_INTROSPECTION_CLIENT_SECRET": settings.mcp_introspection_client_secret,
    }
    configured = {name: value for name, value in values.items() if value}
    if not configured:
        return None
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"Incomplete MCP OAuth configuration; missing: {', '.join(missing)}")

    issuer_url = str(settings.mcp_auth_issuer_url)
    resource_server_url = str(settings.mcp_resource_server_url)
    verifier = IntrospectionTokenVerifier(
        introspection_url=str(settings.mcp_token_introspection_url),
        client_id=str(settings.mcp_introspection_client_id),
        client_secret=str(settings.mcp_introspection_client_secret),
        issuer_url=issuer_url,
        resource_server_url=resource_server_url,
    )
    auth_settings = AuthSettings(
        issuer_url=AnyHttpUrl(issuer_url),
        resource_server_url=AnyHttpUrl(resource_server_url),
        required_scopes=[MCP_READ_SCOPE],
    )
    return MCPAuthBundle(token_verifier=verifier, auth_settings=auth_settings)


def require_scope(scope: str) -> AccessToken:
    token = get_access_token()
    if token is None:
        raise ToolError("Authentication required for this control operation")
    if scope not in token.scopes:
        raise ToolError(f"Missing required scope: {scope}")
    return token


def actor_from_token(token: AccessToken) -> str:
    principal = token.subject or token.client_id
    return f"mcp:{principal}"
