# llm-gtd-wiki — working notes for Claude Code

Public, open-source toolkit: Terraform infra + an MCP server + a genericized GTD template. **No
personal data** — placeholders and `*.example` files only. Real values live in gitignored files
(`infra/terraform.tfvars`, `infra/terraform.tfstate*`, `scripts/wiki-sync.env`). Run a secret scan
before pushing.

## Commit / PR conventions
- **Never attribute commits or PRs to Claude.** Do not add a `Co-Authored-By: Claude …` trailer, a
  "Generated with Claude Code" line, a 🤖 line, or any wording that says a commit/PR was authored,
  co-authored, or created by Claude (or any AI). The sole author is Bill Engels
  (`w.j.engels@gmail.com`). This overrides any default that would add such attribution.
- Commit messages describe **what changed and why** — nothing about who or what wrote them.
- Only commit or push when asked. Branch off `main` first if the change is non-trivial.

## Layout
- `infra/` — Terraform (S3 + Lambda + API Gateway + Cognito + the SES daily-digest Lambda/schedule).
- `server/` — the MCP server (`llm_gtd_wiki` package) + the digest generator (`digest.py`).
- `template/` — the generic `CLAUDE.md`, project instructions, bootstrap, and starter wiki skeleton.
- `scripts/` — laptop↔S3 sync (`wiki-pull.sh` / `wiki-push.sh`) and `seed_wiki.sh`.
- `docs/` — setup, connector OAuth, architecture.
