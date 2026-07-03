# Architecture

```
Claude phone app  ─┐
                   ├─(OAuth 2.1 / PKCE)→  API Gateway (HTTP API)  →  Lambda (FastMCP + Mangum)
Claude desktop app ─┘                                                      │  boto3
                                                                           ▼
                        Cognito  ← discovery/token                     S3 bucket (the wiki,
                        (auth server, via the Lambda's OAuth shim)       versioned)
```

## Components
- **S3** — the wiki store; one markdown object per file, versioning on (undo), noncurrent versions
  expire after 90 days. Encrypted, TLS-only, all public access blocked.
- **Lambda** (`server/`) — a [FastMCP](https://modelcontextprotocol.io) server behind
  [Mangum](https://mangum.io) (ASGI→Lambda). Serves the MCP endpoint at `/mcp`, the OAuth discovery
  docs, and a DCR `/register` shim. Tools: `list_files`, `read_file`, `edit_file`, `write_file`,
  `append_to_inbox`, `search`, `get_operating_contract`. A fresh app is built per invocation (the MCP
  session manager's `.run()` is once-per-instance; Lambda runs the lifespan every invocation).
- **API Gateway (HTTP API)** — the public front door. *Not* a Lambda Function URL — see gotchas.
- **Cognito** — OAuth 2.1 authorization server (authorization-code + PKCE), single admin-created
  user, a `wiki/readwrite` scope. The Lambda serves RFC 8414 metadata + an RFC 7591 DCR shim because
  Cognito provides neither in the shape Claude's connector expects.
- **Email/calendar** — not here; Anthropic's first-party Gmail/Calendar connectors, used alongside.

## Gotchas we hit (and why the design is what it is)
These bit during bring-up; the config already accounts for them:
1. **Public NONE-auth Function URL** needs an explicit `lambda:InvokeFunctionUrl` **and**
   `lambda:InvokeFunction` grant to `*` (the console adds them; Terraform must too).
2. **Lambda + FastMCP lifespan** — `StreamableHTTPSessionManager.run()` is once-per-instance; build a
   fresh app per invocation, not a module-level singleton.
3. **Lambda Function URLs remap `WWW-Authenticate`** → they break the MCP OAuth discovery handshake.
   Fix: front the Lambda with **API Gateway HTTP API**, which passes headers through unchanged.
4. **Trailing-slash redirect** — mount the MCP app so `/mcp` is served directly (307→/mcp/ fails).
5. **DNS-rebinding protection** — the MCP SDK rejects unknown `Host` headers with `421`; disable it
   (`enable_dns_rebinding_protection=False`) since traffic is server-side and OAuth-gated.

## Alternative host
**Amazon Bedrock AgentCore Gateway** can act as a managed MCP endpoint + auth layer (an alternative to
the DIY API Gateway + Cognito here). Heavier than a single-user wiki needs; noted for completeness.

## Cost
All pay-per-use, scale-to-zero. For one user it's **cents/month** at most (S3 requests + a little API
Gateway/CloudWatch); idle cost ≈ $0. Small markdown edits are cheap — S3 bills per request
(~$0.005/1,000 writes), not per byte.
