# CLAUDE.md: FMRP Record Board

Flask + SQLite + Jinja board for the FMRP Highest/Lowest whiteboard. Deployed via Docker on `home-nas` (192.168.0.65), `/volume1/docker/fmrp-board/`, port 8095, Tailscale only.

## Rules (Quinones' 4 rules)
1. Ask, don't assume. 2. Simplest solution first. 3. Don't touch unrelated code or other Docker stacks. 4. Flag uncertainty explicitly.
- Never modify/restart other containers. Confirm before `docker compose up`, opening ports, Tailscale changes, or Synology scheduled tasks.
- After each coding task report: Files changed / What was modified / Files intentionally not touched / Follow-up needed.
- Free and open source only.

## Invariants
- No PHI fields. Footer reminder stays.
- Every data change goes through `app/models.py` inside `with db:` so the audit row commits with the change.
- `audit_log` is append-only: no update/delete routes, and SQLite triggers block UPDATE/DELETE.
- Records and residents are never hard-deleted.

## Layout
- `app/routes.py` views, auth (`editor_required`, `admin_required`), change log, CSV, restore
- `app/models.py` data changes + audit writes
- `app/db.py` schema, triggers, password sync from `.env`
- `scripts/seed_board.py` whiteboard import; `scripts/backup_db.sh` nightly backup
- Tests: `.venv\Scripts\python -m pytest -q tests`

See `project_log.md` for decisions, `MEMORY.md` for gotchas, `ERRORS.md` for errors hit.
