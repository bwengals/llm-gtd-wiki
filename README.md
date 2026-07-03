# llm-gtd-wiki

Run a **Claude-driven GTD "LifeTracker"** — a markdown wiki that Claude maintains for you per an
operating contract — from the **Claude desktop and phone apps**, with the files stored in **AWS S3**.

This repo is the reusable **plumbing + template**:

- **`infra/`** — Terraform for AWS (S3 wiki bucket, a Lambda MCP server, Cognito for OAuth).
- **`server/`** — a small [MCP](https://modelcontextprotocol.io) server exposing the wiki
  (`list_files`, `read_file`, `edit_file`, `write_file`, `append_to_inbox`, `search`,
  `get_operating_contract`). You add it to the Claude apps as a **custom connector**.
- **`template/`** — a genericized `CLAUDE.md` operating contract, a starter wiki skeleton, and a
  bootstrap prompt for standing up your own wiki.

It contains **no personal data** — your actual wiki lives privately in your own S3 bucket and is
never committed here.

## How it works
```
Claude phone app  ─┐
                   ├─(OAuth 2.1)→  MCP server (Lambda)  ──boto3──→  S3 bucket (your wiki)
Claude desktop app ─┘               list / read / edit / write / append / search
```
Email and calendar are **not** part of this — enable Anthropic's first-party Gmail and Google
Calendar connectors in the app alongside this one.

## Requirements
- An AWS account (you deploy into it with Terraform).
- An Anthropic **Max** plan (custom connectors) for the Claude apps.

## Getting started
See **[docs/setup.md](docs/setup.md)** for the end-to-end walkthrough (deploy → seed → connect →
personalize).

## Docs
- [setup.md](docs/setup.md) — full setup.
- [architecture.md](docs/architecture.md) — how it fits together (and the AWS gotchas it accounts for).
- [connector-oauth.md](docs/connector-oauth.md) — the Claude-connector OAuth handshake.
- [claude-project.md](docs/claude-project.md) — the Claude Project that carries the operating rules.
- [change-review-workflow.md](docs/change-review-workflow.md) — the two-tier change policy + batch review.
- [laptop-sync.md](docs/laptop-sync.md) — editing from a laptop with Claude Code (pull → work → push).

## License
MIT — see [LICENSE](LICENSE).
