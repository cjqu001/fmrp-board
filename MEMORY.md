# MEMORY: things worth remembering about this project

- NAS user `cq_admin` is uid 1027 / gid 100; docker-compose runs the container as `1027:100` so it can write `data/` and `backups/`.
- `sudo` on the NAS asks for a password, so Claude can't run `sudo docker ...` over SSH unattended. Port checks were done with plain `netstat -tln` (no process names).
- NAS `/volume1/docker/` (2026-11-18): audiobookshelf, canutin, clinicnotes, habit-text, habit_tracker, homepage, jellyfin, patient-app, postgres, tmfcloset. Differs from the stack list in the handoff.
- Ports already listening on the NAS (2026-11-18): 22 80 111 139 161 443 445 512 662 892 2049 3000 3002 3261 3263-3265 4045 5000 5001 5055 5357 5432 5433 8096 8787 13378 33304 42069 55090. 8095 was free.
- Shared editor login: `session["actor_name"]` is whatever the person typed; it is not proof of identity.
- Passwords live only in `.env`; the app re-hashes on start if they changed.
- Lab label gets "(high)/(low)" only when that lab has both directions on the board (e.g. Glucose, BMI, K+, Platelets, WBC).
- 2026-11-19: the Flask app and NAS container were retired; the notes above about the NAS, logins and Docker apply only to the old version in git history.
- The static page writes `board.csv` with LF line endings (`.gitattributes` keeps LF).
