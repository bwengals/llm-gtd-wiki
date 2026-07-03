"""Phase 0 MCP app: a single `ping` tool + the OAuth shim, wired for AWS Lambda.

Phase 1 replaces `ping` with the real wiki tools (list_files/read_file/edit_file/write_file/
append_to_inbox/search/get_operating_contract) backed by storage.py.

Lambda note: FastMCP's StreamableHTTPSessionManager can only have `.run()` called once per instance,
but Mangum runs the ASGI lifespan on every invocation. So we build a FRESH app (fresh session
manager) per invocation in `handler()` rather than reusing a module-level instance.
"""
from __future__ import annotations

from mangum import Mangum
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.routing import Mount

from .auth import BearerAuthMiddleware
from .config import load_config
from .oauth_shim import make_routes
from .storage import WikiStorage

cfg = load_config()
RESOURCE_METADATA_PATH = "/.well-known/oauth-protected-resource"
CONTRACT_PATH = "CLAUDE.md"
INBOX_PATH = "inbox.md"

# Reused across warm invocations (boto3 client is thread-safe and cheap to keep).
_storage: WikiStorage | None = None


def storage() -> WikiStorage:
    global _storage
    if _storage is None:
        _storage = WikiStorage(cfg)
    return _storage


class LogMiddleware:
    """Lean access log: method, path, status only (no bodies/headers) → CloudWatch."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        status = {"code": None}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        print(f"{scope.get('method')} {scope.get('path')} -> {status['code']}")


def build_app() -> Starlette:
    # Fresh FastMCP -> fresh StreamableHTTPSessionManager each call (see module docstring).
    # streamable_http_path="/mcp" + mounting at "/" makes the MCP endpoint live at exactly "/mcp"
    # (no trailing-slash 307 redirect, which the client can't follow cleanly).
    # DNS-rebinding protection off: it validates the Host header against an allow-list and returns
    # 421 behind API Gateway (Host = execute-api domain). Safe here — Claude calls server-side and
    # /mcp is OAuth-protected; the rebinding attack (a malicious browser page) isn't our threat model.
    mcp = FastMCP(
        "llm-gtd-wiki",
        stateless_http=True,
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def list_files() -> str:
        """List every file (path) in the wiki, one per line."""
        return "\n".join(storage().list_files()) or "(empty wiki)"

    @mcp.tool()
    def read_file(path: str) -> str:
        """Read a wiki file's full text. `path` is relative, e.g. 'index.md' or 'areas/home.md'."""
        return storage().read(path)

    @mcp.tool()
    def edit_file(path: str, old_string: str, new_string: str) -> str:
        """Replace `old_string` with `new_string` in the file at `path`. `old_string` must match
        exactly and occur exactly once (include surrounding context to make it unique); errors
        otherwise. This is the preferred way to make targeted edits."""
        return storage().edit(path, old_string, new_string)

    @mcp.tool()
    def write_file(path: str, content: str) -> str:
        """Create or fully overwrite the file at `path` with `content`. Prefer `edit_file` for
        small changes. Writes under 'raw/' are refused. Returns a confirmation."""
        storage().write(path, content)
        return f"wrote {path} ({len(content)} chars)"

    @mcp.tool()
    def append_to_inbox(text: str) -> str:
        """Append a line to inbox.md (the capture buffer). Use for quick capture from anywhere."""
        storage().append(INBOX_PATH, text if text.lstrip().startswith("-") else f"- {text}")
        return "captured to inbox.md"

    @mcp.tool()
    def search(query: str, path_prefix: str = "") -> str:
        """Case-insensitive substring search across .md files. Returns 'path:line: text' hits
        (max 100). Optional `path_prefix` limits the search (e.g. 'areas/')."""
        hits = storage().search(query, path_prefix)
        return "\n".join(hits) if hits else "(no matches)"

    @mcp.tool()
    def get_operating_contract() -> str:
        """Return the wiki's operating contract (CLAUDE.md) — the rules for maintaining it.
        Call this at the start of a session and follow it."""
        return storage().read(CONTRACT_PATH)

    stream_app = mcp.streamable_http_app()
    routes = make_routes(cfg)
    routes.append(Mount("/", app=stream_app))  # shim routes match first; MCP served at /mcp
    app = Starlette(routes=routes, lifespan=stream_app.router.lifespan_context)
    # Auth only guards /mcp; discovery + /register stay public.
    app.add_middleware(
        BearerAuthMiddleware, cfg=cfg, resource_metadata_path=RESOURCE_METADATA_PATH
    )
    app.add_middleware(LogMiddleware)  # outermost: logs final status
    return app


# Long-lived app for local dev (uvicorn in run_local.py runs the lifespan exactly once).
app = build_app()


def handler(event, context):
    # Lambda entrypoint (infra/lambda.tf handler = "llm_gtd_wiki.app.handler").
    # Fresh app per invocation so the session manager's run-once constraint holds.
    return Mangum(build_app(), lifespan="auto")(event, context)
