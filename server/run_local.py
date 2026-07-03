"""Run the MCP server locally for testing with the MCP Inspector.

    cd server
    pip install -e ".[dev]"
    AUTH_DISABLED=1 python run_local.py
    # then: npx @modelcontextprotocol/inspector  ->  http://localhost:8000/mcp

With AUTH_DISABLED unset you can also exercise the OAuth shim endpoints:
    curl localhost:8000/.well-known/oauth-protected-resource
    curl localhost:8000/.well-known/oauth-authorization-server
"""
from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("llm_gtd_wiki.app:app", host="0.0.0.0", port=8000, reload=True)
