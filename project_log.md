# FMRP Record Board: Project Log

Source handoff: `C:\stuff\2026-11-18_FMRP_RecordBoard_ClaudeCode_Handoff.md`

## 2026-11-18: Project created

Local build folder: `C:\Users\admin\Projects\active\fmrp-board` (git, branch `main`).
Deploy target (later, after confirmation): `/volume1/docker/fmrp-board/` on `home-nas` (192.168.0.65).

### Open questions (handoff section 9) and answers

| # | Question | Answer (2026-11-18) |
|---|---|---|
| 1 | Access scope: Tailscale only, or co-residents off the tailnet? | **Tailscale only.** No Funnel, no reverse proxy. |
| 2 | Accounts: one per resident, or shared editor password? | **Shared editor password.** Editor types their name; logs can be spoofed (accepted trade-off). |
| 3 | Viewing: public read-only, or login to view? | **Public read-only board.** Login needed only to edit. |
| 4 | Who is admin? | **Only Quinones**, with a separate admin password. |
| 5 | Port and URL | **8095 if free** (to verify on NAS). URL `http://home-nas:8095` over Tailscale. |
| 6 | Superseded records on the board? | **History only.** Board shows current record; old values in per-record history. |

### Design consequences
- Two logins: `editor` (shared) and `admin` (Quinones). On editor login the user types a display name, stored in the session and written to every audit row.
- "User" column in the change log = typed name + role, so a filter by user works but is not proof of identity.
- Local Python is 3.11.9; the container uses Python 3.12 as specified.

### Built (2026-11-18)
- Flask MVP: board, add/edit/soft-delete, residents (add/rename/graduate), change log with lab/resident/user filters and CSV, per-record history, admin Undo.
- Change log and edit pages need a login (board is public). IPs are stored but not shown.
- `audit_log` gets an extra `actor_name` column (typed name), because a shared login has one `user_id` for everyone.
- Edit is on the record page (expand "Edit this record") instead of a modal: simpler, works on phones.
- Seeded 55 records locally; BUN seeded as 166 Hammer/Belgrave, then updated to 186 Talebi/Charite, so its history shows both.
- 16 pytest tests pass (audit on create/edit/delete, viewers cannot edit, audit log unchangeable through any route or directly in SQLite, CSRF on, seed).

### Flagged uncertainty (please check)
- **Direction guesses**: set from the lab name. Low: HCO3, Hgb, Temp, K+ low, B12, EF, Na, pH, Vit D, Iron sat, WBC low, Platelets low, Mg, CD4, Hrs to bounceback, Glucose low, BMI low. Count: Admissions, Discharges, Most codes. Everything else High (including Units of insulin, Paracentesis fluid, Wt loss per day).
- **Possible duplicate residents** kept as separate names, as transcribed: Bidaisee / Bidaisse / Bidaisse?; Lopes / Lopez. Fix them with Rename on the Residents page.
- **pH**: the board pairs Kerr + Dunn and Dantas + Bennett. The app stores four residents and keeps the pairing in the note.
- **IP column**: behind Docker's port mapping the logged IP will likely be the Docker gateway, not the resident's device.
- **LAN exposure**: port 8095 is published on all NAS interfaces, so it is reachable from the home LAN as well as Tailscale (not the internet). Binding it to the NAS's Tailscale IP only is possible; not done yet.
- **Font**: the Atkinson Hyperlegible woff2 files are not downloaded yet; the page falls back to the system font.

### Next
- Deploy to the NAS (needs Quinones' OK to copy files and run `docker compose up`; sudo on the NAS needs their password).
- Create the Synology nightly backup task (needs OK).
