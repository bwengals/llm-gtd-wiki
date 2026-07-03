"""OAuth discovery + dynamic-client-registration shim.

Claude's MCP custom connectors expect the server to advertise, per the MCP authorization spec:
  - RFC 9728 protected-resource metadata  (/.well-known/oauth-protected-resource)
  - RFC 8414 authorization-server metadata (/.well-known/oauth-authorization-server)
  - RFC 7591 dynamic client registration   (POST /register)

Cognito provides authorize/token/PKCE/OIDC, but not AS metadata in the shape the client wants and no
DCR endpoint. So this Lambda serves the metadata (pointing at Cognito's real endpoints) and answers
/register by returning the pre-created public Cognito client_id.

VERIFY in Phase 0: exact fields Claude requires; whether Claude lets you enter a client_id manually
(which would let you delete /register entirely); and whether it needs RFC 8707 `resource` handling.
"""
from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import Config


def _base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    proto = request.headers.get("x-forwarded-proto", "https")
    return f"{proto}://{host}"


def make_routes(cfg: Config):
    from starlette.routing import Route

    async def protected_resource(request: Request) -> JSONResponse:
        base = _base_url(request)
        return JSONResponse(
            {
                "resource": f"{base}/mcp",
                "authorization_servers": [base],
                "scopes_supported": ["wiki/readwrite"],
                "bearer_methods_supported": ["header"],
            }
        )

    async def authorization_server(request: Request) -> JSONResponse:
        base = _base_url(request)
        return JSONResponse(
            {
                "issuer": base,
                "authorization_endpoint": f"{cfg.cognito_domain}/oauth2/authorize",
                "token_endpoint": f"{cfg.cognito_domain}/oauth2/token",
                "registration_endpoint": f"{base}/register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["none"],
                "scopes_supported": ["openid", "email", "wiki/readwrite"],
            }
        )

    async def register(request: Request) -> JSONResponse:
        # Hand back the pre-created public client. No secret (public client + PKCE).
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        redirect_uris = body.get("redirect_uris", [])
        return JSONResponse(
            {
                "client_id": cfg.cognito_client_id,
                "token_endpoint_auth_method": "none",
                "redirect_uris": redirect_uris,
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
            },
            status_code=201,
        )

    return [
        Route("/.well-known/oauth-protected-resource", protected_resource, methods=["GET"]),
        Route("/.well-known/oauth-authorization-server", authorization_server, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
    ]
