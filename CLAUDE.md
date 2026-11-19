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

## NAS commands
- Claude can't run `sudo` on the NAS (it asks for a password). The user runs sudo commands in their own PowerShell over SSH, with full paths: `sudo /usr/local/bin/docker-compose ...`, `sudo /usr/local/bin/docker ...`.
- Never type, ask for, or store passwords for the user.

## Status (2026-11-18)
Done:
- MVP built: public read-only board; editor and admin logins; add, edit and soft-delete records; residents (add, rename, graduate); change log with filters and CSV export; per-record history; admin Undo. 17 pytest tests pass.
- Committed on `main` and pushed to the private repo https://github.com/cjqu001/fmrp-board.
- Deployed on the NAS at `/volume1/docker/fmrp-board/`, port 8095, and seeded with 55 records. The board answers HTTP 200 at `http://home-nas:8095`.
- The NAS `.env` has random passwords. The admin login failed, most likely because the 16-character password is hard to type. Fixes: added `scripts/set_password.sh` (asks for a new password hidden, saves it to `.env`, restarts only this board's container), and the login now ignores spaces around the password. Both are copied to the NAS.

## Static board (2026-11-19, user's choice)
- The board is now a static page in `docs/` on GitHub Pages (https://cjqu001.github.io/fmrp-board/); the repo is public. Anyone with the link views; only the user edits, on their own computer, and pushes `docs/board.csv`. Git history is the change log.
- Edit tools and the whiteboard photo tab show only on file:// or localhost. `docs/photo-log/` is gitignored (never published).
- The Flask app and NAS container are kept for now. Retiring them (stop container, remove code, update the invariants above) needs the user's OK.
- Not yet tested by the user: "Open board folder" and adding photos (need a real folder pick in Chrome/Edge).

## Next steps for the old Flask app (ask the user which to do first)
1. Editor login (if needed): the user runs `ssh -t cq_admin@192.168.0.65 "sh /volume1/docker/fmrp-board/scripts/set_password.sh editor"` in PowerShell, then confirms it works.
2. Backup when data changes, not nightly (user's choice, 2026-11-18). No Synology scheduled task. Proposed simplest design, to confirm with the user before coding: after each successful change in `app/models.py`, the app writes an SQLite online backup to `backups/board-YYYY-MM-DD.db` (one file per day that had changes, overwritten during that day), keeping the last 30 files. `scripts/backup_db.sh` stays for manual backups. Update README's Backups section to match.
3. Fonts (optional, looks only): the page is meant to use Atkinson Hyperlegible, a free easy-to-read font. Its two files (`AtkinsonHyperlegible-Regular.woff2`, `-Bold.woff2`, SIL OFL) are not in `app/static/fonts/` yet, so the board uses the device's default font. Needs the user's OK to download.
4. Optional: bind port 8095 to the NAS's Tailscale IP only (now open on the home LAN too). Needs the user's OK.
5. The user reviews the flagged items in `project_log.md`: High/Low direction guesses, possible duplicate residents (Bidaisee/Bidaisse, Lopes/Lopez), and the pH pairing.

Done by the user: changed the NAS `cq_admin` password (2026-11-18). Reset the board admin password with `set_password.sh`; admin login works (2026-11-18).
