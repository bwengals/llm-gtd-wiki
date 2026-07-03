"""Cognito access-token validation, applied as Starlette middleware on the /mcp endpoint.

On a missing/invalid token we return 401 with a WWW-Authenticate header pointing at the protected-
resource metadata, per the MCP authorization spec (RFC 9728) so the Claude client can discover how
to authenticate.
"""
from __future__ import annotations

import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import Config

# Reused across warm Lambda invocations; PyJWKClient caches signing keys internally.
_jwk_clients: dict[str, jwt.PyJWKClient] = {}


def _jwk_client(cfg: Config) -> jwt.PyJWKClient:
    client = _jwk_clients.get(cfg.jwks_uri)
    if client is None:
        client = jwt.PyJWKClient(cfg.jwks_uri)
        _jwk_clients[cfg.jwks_uri] = client
    return client


class AuthError(Exception):
    pass


def verify_token(token: str, cfg: Config) -> dict:
    """Validate a Cognito access token; return its claims or raise AuthError."""
    try:
        signing_key = _jwk_client(cfg).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=cfg.issuer,
            options={"verify_aud": False},  # Cognito access tokens carry client_id, not aud
        )
    except Exception as exc:  # noqa: BLE001 - normalize to AuthError
        raise AuthError(f"token verification failed: {exc}") from exc

    if claims.get("token_use") != "access":
        raise AuthError("not an access token")
    if cfg.cognito_client_id and claims.get("client_id") != cfg.cognito_client_id:
        raise AuthError("client_id mismatch")
    scopes = str(claims.get("scope", "")).split()
    if "wiki/readwrite" not in scopes:
        raise AuthError("missing wiki/readwrite scope")
    if cfg.allowed_subs and claims.get("sub") not in cfg.allowed_subs:
        raise AuthError("subject not allowed")
    return claims


class BearerAuthMiddleware:
    """Enforces auth on paths under /mcp; leaves discovery/register endpoints public."""

    def __init__(self, app: ASGIApp, cfg: Config, resource_metadata_path: str) -> None:
        self.app = app
        self.cfg = cfg
        self.resource_metadata_path = resource_metadata_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.cfg.auth_disabled:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        header = request.headers.get("authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else None

        if not token:
            await self._challenge(scope, receive, send, "missing bearer token")
            return
        try:
            verify_token(token, self.cfg)
        except AuthError as exc:
            await self._challenge(scope, receive, send, str(exc))
            return

        await self.app(scope, receive, send)

    async def _challenge(self, scope, receive, send, detail: str) -> None:
        base = _base_url(scope)
        resp = JSONResponse(
            {"error": "unauthorized", "detail": detail},
            status_code=401,
            headers={
                "WWW-Authenticate": (
                    f'Bearer resource_metadata="{base}{self.resource_metadata_path}"'
                )
            },
        )
        await resp(scope, receive, send)


def _base_url(scope: Scope) -> str:
    headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
    host = headers.get("x-forwarded-host") or headers.get("host", "")
    proto = headers.get("x-forwarded-proto", "https")
    return f"{proto}://{host}"
