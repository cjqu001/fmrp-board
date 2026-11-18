# Tech stack (all free and open source)

| Part | Choice | Version | License |
|---|---|---|---|
| Language | Python | 3.12 in Docker (3.11.9 locally) | PSF |
| Web framework | Flask, Jinja templates, minimal vanilla JS | 3.1.3 | BSD-3 |
| CSRF | Flask-WTF | 1.3.0 | BSD-3 |
| Password hashing | Werkzeug `generate_password_hash` (scrypt) | 3.1.9 | BSD-3 |
| Database | SQLite (single file in `data/`) | bundled | Public domain |
| Time zones | `zoneinfo` + tzdata (America/New_York) | 2026.6 | Apache-2.0 |
| App server | gunicorn, 2 workers | 27.0.1 | MIT |
| Container | Docker + docker compose, one service | NAS Container Manager | Apache-2.0 |
| Font | Atkinson Hyperlegible, self-hosted woff2 | (not yet added) | OFL-1.1 |
| Tests | pytest | 9.2.0 | MIT |
| Local env | python-dotenv | 1.2.4 | BSD-3 |
