# CLAUDE.md: FMRP Record Board

Static HTML board for the FMRP Highest/Lowest whiteboard, on GitHub Pages:
https://cjqu001.github.io/fmrp-board/ (public repo https://github.com/cjqu001/fmrp-board, served from `main` / `docs`).

## Rules (Quinones' 4 rules)
1. Ask, don't assume. 2. Simplest solution first. 3. Don't touch unrelated code or other Docker stacks. 4. Flag uncertainty explicitly.
- Confirm before publishing changes the user hasn't asked for, and before NAS, Tailscale or Synology changes.
- After each coding task report: Files changed / What was modified / Files intentionally not touched / Follow-up needed.
- Free and open source only.

## Invariants
- No PHI fields. Footer reminder stays.
- Visitors only view and export. Edit tools and the Whiteboard photos tab show only on file:// or localhost.
- `docs/photo-log/` is gitignored and never published.
- Git history of `docs/board.csv` is the change log. Don't rewrite or force-push history.
- Residents' names on the public page are OK (user, 2026-11-19: they are public via NPI and FSU).

## Layout
- `docs/index.html`, `docs/board.js`, `docs/style.css`: the page
- `docs/board.csv`: data (`lab, direction, value, residents, note, updated`), in board order, LF line endings
- `scripts/db_to_csv.py`: old Flask database to CSV
- Local preview: launch config `static-board` (http.server on 127.0.0.1:8096, serving `docs/`)

See `project_log.md` for decisions, `MEMORY.md` for gotchas, `ERRORS.md` for errors hit.

## NAS
- The old Flask board (`/volume1/docker/fmrp-board/`, port 8095) was retired on 2026-11-19. Its folder, including `data/board.db`, was left on the NAS as an archive.
- Claude can't run `sudo` on the NAS. The user runs sudo commands in their own PowerShell over SSH, with full paths (`sudo /usr/local/bin/docker-compose ...`).
- Never type, ask for, or store passwords for the user.

## Status (2026-11-19)
Done:
- Static board live on GitHub Pages with 55 records. Viewing, edit form, CSV/JPG export and CSV round-trip tested in the browser.
- Repo made public. Flask app, Docker files and tests removed from the repo (still in git history, commit `6c2c9f5` and earlier).

Not yet tested by the user: "Open board folder" editing and adding whiteboard photos (need a real folder pick in Chrome/Edge).

## Open items (ask the user before doing)
1. The user reviews flagged items in `project_log.md`: High/Low direction guesses, possible duplicate residents (Bidaisee/Bidaisse, Lopes/Lopez), and the pH pairing.
2. Optional: Atkinson Hyperlegible font (SIL OFL) for the page. Needs the user's OK to download.
3. Optional: once the user confirms the NAS container is gone, they can delete `/volume1/docker/fmrp-board/` and the `fmrp-board` image.
