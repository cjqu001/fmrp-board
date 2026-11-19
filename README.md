# FMRP Highest / Lowest Record Board

**Now a static page:** https://cjqu001.github.io/fmrp-board/ (GitHub Pages, from `docs/`).
How to edit it: [docs/README.md](docs/README.md). The Flask app below is the older NAS version.

Live version of the FMRP whiteboard. Public read-only board; editing needs a login.
Every change is written to an append-only change log in the same database transaction.

- Board: `http://home-nas:8095` (Tailscale only)
- Logins: shared **editor** password (type your name) and a separate **admin** password (Quinones).
- No patient identifiers, ever.

## Run locally (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env    # then edit .env; add DATABASE=data/board.db
.venv\Scripts\python scripts\seed_board.py
.venv\Scripts\python -m flask --app app run --port 5095
```

Tests: `.venv\Scripts\python -m pytest -q tests`

## Deploy to the NAS (first time)

1. Copy the project (not `.venv`, `data/*.db`, or your local `.env`) to `\\home-nas\docker\fmrp-board\`.
2. On the NAS create `.env` from `.env.example` with new values.
3. SSH in as `cq_admin`, then:
   ```sh
   cd /volume1/docker/fmrp-board
   sudo /usr/local/bin/docker-compose build
   sudo /usr/local/bin/docker-compose run --rm fmrp-board python -m pytest -q tests
   sudo /usr/local/bin/docker-compose up -d
   sudo /usr/local/bin/docker-compose exec fmrp-board python scripts/seed_board.py
   ```
4. Open `http://home-nas:8095` from a device on the tailnet.

## Update

Copy changed files over, then `sudo /usr/local/bin/docker-compose up -d --build`. Data in `data/` is kept.

## Change a password

On the NAS run `sh /volume1/docker/fmrp-board/scripts/set_password.sh admin` (or `editor`). It asks for the new password hidden, saves it to `.env`, and restarts the board.

## Backups

`scripts/backup_db.sh` makes a consistent copy (SQLite online backup) to
`backups/board-YYYY-MM-DD.db` and deletes copies older than 30 days.
Set it up in DSM: Control Panel → Task Scheduler → Create → Scheduled Task → User-defined script,
user `root`, daily at 03:00, command `sh /volume1/docker/fmrp-board/scripts/backup_db.sh`.

## Restore from a backup

```sh
cd /volume1/docker/fmrp-board
sudo /usr/local/bin/docker-compose stop
cp data/board.db data/board.db.before-restore
cp backups/board-YYYY-MM-DD.db data/board.db
sudo /usr/local/bin/docker-compose start
```

To undo a single change instead, log in as admin, open **Change log**, and press **Undo** on that row.

## Fonts

Atkinson Hyperlegible (SIL Open Font License) is self-hosted. Put
`AtkinsonHyperlegible-Regular.woff2` and `AtkinsonHyperlegible-Bold.woff2` in `app/static/fonts/`.
Until then the page falls back to the system font.
