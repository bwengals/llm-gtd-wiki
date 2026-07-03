# Bootstrap prompt — stand up a fresh Life OS

After the infra is deployed, the bucket seeded with the `template/wiki/` skeleton, the connector added,
and the Project created (see `docs/setup.md`), paste the prompt below into the Project to personalize
the wiki. It interviews you, fills in the placeholders, and does a first pass.

---

You're setting up my GTD Life OS for the first time. Work through this with me:

1. Call `get_operating_contract` and `list_files` to see the starting skeleton.
2. **Interview me** (a round at a time, not a questionnaire): 
   - My **life areas** — which `areas/*.md` to keep, rename, or add (defaults: work, home, health, admin).
   - Current **projects** worth their own `projects/*.md` page.
   - Recurring **routines** (daily/weekly habits) for `routines.md`.
   - My **@errands store tags** (the shops I actually go to).
   - What **`[client-work]`** means for me, if anything (for the weekend rule), and my **calendar email**.
3. **Fill the placeholders** in `CLAUDE.md` via `edit_file`: replace `[the human]` with my name,
   `[personal-calendar-email]` with my calendar address, `[client-work]`/`[store-a]` etc. with real
   values, and rename the area files to match. Confirm the non-obvious calls.
4. **First capture:** ask me for a brain-dump of everything on my mind → `append_to_inbox` each item,
   then run a full **Clarify** pass (sort, define next actions, file them).
5. **Rebuild `index.md`** from the area/project pages.
6. Append a one-line setup summary to `log.md` and write the first `> Reviewed through: <today>` marker.

Then tell me what you set up and what you'd like me to keep an eye on.
