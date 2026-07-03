# The Claude Project

The plain Claude apps don't auto-load a `CLAUDE.md` the way Claude Code does. To make every chat
behave like the Life OS, put the operating rules in a **Project**.

## Steps
1. In the Claude app, create a Project (e.g. "Life OS").
2. Paste [`template/project-instructions.md`](../template/project-instructions.md) as the Project's
   **custom instructions**. It tells Claude to call `get_operating_contract` first and summarizes the
   rules.
3. Make sure the **llm-gtd-wiki** connector is enabled, plus (optionally) the first-party **Gmail**
   and **Google Calendar** connectors.
4. Do your Life OS work inside this Project.

## Why `get_operating_contract` first
The full contract lives in the wiki's `CLAUDE.md` (in S3), so it stays editable and in one place. The
Project instructions are a short pointer + summary; the tool call pulls the authoritative version at
the start of each session.

## Keeping it in sync
Edit the rules by editing `CLAUDE.md` in the wiki (via the connector, or a laptop pull/push session) —
not by editing the Project instructions, which should stay a thin pointer.
