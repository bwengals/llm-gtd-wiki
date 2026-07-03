# Connector OAuth: how the handshake works (verified against Anthropic docs, 2026)

Claude custom connectors authenticate to a remote MCP server with **OAuth 2.1** (authorization-code
+ **PKCE/S256**). Key facts confirmed from Anthropic's connector docs:

- **Redirect URI** (hosted web/desktop/mobile): `https://claude.ai/api/mcp/auth_callback` — register
  this on your OAuth client. (Claude Code's native client uses an ephemeral loopback
  `http://localhost/callback` / `http://127.0.0.1/callback` with the port ignored — only needed if
  you also connect from Claude Code.)
- **Connectors are added on claude.ai WEB** (Settings → Connectors), then sync to desktop + mobile.
  You cannot add one in the phone app — only use it. First-party Gmail/Calendar connectors likewise
  work on mobile.
- Available on **Max** (also Pro/Team/Enterprise).

## Discovery / registration requirements (confirmed)
| Piece | Required? | Notes |
|---|---|---|
| **RFC 8414** authorization-server metadata (`/.well-known/oauth-authorization-server`) | **Yes** | Claude fetches this first (falls back to `/.well-known/openid-configuration`). Must advertise `code_challenge_methods_supported: ["S256"]` and a registration mechanism (below). |
| **RFC 8707** resource indicators (the `resource` param) | **Yes** | Claude **sends `resource`** (the canonical MCP URL: lowercase scheme/host, no trailing slash/fragment/default port) on every authorize + token request. The server must accept/validate it. |
| **RFC 9728** protected-resource metadata (`/.well-known/oauth-protected-resource`) | Optional | Not required by current Claude; harmless to serve (our shim does). |

## Client registration — three options (Cognito supports none natively)
1. **DCR (RFC 7591):** advertise a `registration_endpoint`; Claude auto-registers. → our
   `server/oauth_shim.py` `/register` returns the pre-created Cognito public client. **Current default.**
2. **CIMD (Client ID Metadata Documents)** — the **newer preferred** method (Nov 2025 MCP spec):
   Claude uses an HTTPS URL as the `client_id` and fetches metadata (redirect URIs, name) from it;
   no registration call. Requires the AS metadata to advertise `client_id_metadata_document_supported:
   true`. Worth switching to later — simpler lifecycle. (Cognito won't emit this field, so it still
   rides on our metadata shim.)
3. **Manual client ID / Anthropic-held creds:** the connector "Advanced settings" may let you paste
   a `client_id` — if so you can drop `/register` entirely and just use the Cognito app client.
   (Unconfirmed whether it fully bypasses needing a `registration_endpoint` — test in the UI.)

## Why the shim exists
Amazon Cognito provides `/oauth2/authorize`, `/oauth2/token`, PKCE, and OIDC discovery — but **not**
RFC 8414 metadata in the shape Claude wants, no DCR, and no CIMD. So the Lambda serves the metadata
(pointing at Cognito's real endpoints) and answers `/register` with the pre-created **public** Cognito
client (PKCE, no secret). See `server/oauth_shim.py`.

## Phase 0 checklist (resolve live — this is the whole point of Phase 0)
- [ ] Register `https://claude.ai/api/mcp/auth_callback` on the Cognito app client (done via
      `claude_redirect_uris`).
- [ ] Confirm Claude fetches `/.well-known/oauth-authorization-server` and completes PKCE against
      Cognito. If it only tries `/.well-known/openid-configuration`, add that alias.
- [ ] **Handle the `resource` param** — verify Cognito accepts it (or that the flow still succeeds);
      wire audience/resource validation if token exchange fails. *(TODO in `oauth_shim.py`/`config.py`.)*
- [ ] Decide DCR vs. manual client-ID (check the connector "Advanced settings"). If manual works,
      simplify by deleting `/register` + the `registration_endpoint` field.
- [ ] Consider CIMD as a follow-up once the basic flow passes.

## Official docs
- Get started with custom connectors (remote MCP): https://support.claude.com/en/articles/11175166
- Authentication for connectors: https://claude.com/docs/connectors/building/authentication
- Remote MCP custom connectors: https://claude.com/docs/connectors/custom/remote-mcp
- Build custom connectors via remote MCP: https://support.claude.com/en/articles/11503834

## Security notes
- Function URL is public (`authorization_type = NONE`) on purpose — discovery/register must be
  reachable unauthenticated; `/mcp` enforces the bearer token in-app (`server/auth.py`).
- `server/auth.py` checks Cognito JWKS signature, issuer, `token_use=access`, `client_id`, the
  `wiki/readwrite` scope, and an optional `sub` allow-list. Never log request bodies (wiki content).
