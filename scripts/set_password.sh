#!/bin/sh
# Set the admin or shared editor password, then restart the board.
# Run on the NAS:  sh /volume1/docker/fmrp-board/scripts/set_password.sh admin
#             or:  sh /volume1/docker/fmrp-board/scripts/set_password.sh editor
# The password is typed hidden and never appears on a command line.
set -eu
cd "$(dirname "$0")/.."

case "${1:-}" in
  admin) KEY=ADMIN_PASSWORD ;;
  editor) KEY=EDITOR_PASSWORD ;;
  *) echo "Usage: sh scripts/set_password.sh admin|editor"; exit 1 ;;
esac

trap 'stty echo 2>/dev/null' EXIT INT TERM
stty -echo
printf 'New %s password: ' "$1"; read -r P1
printf '\nType it again: '; read -r P2
stty echo; echo

[ "$P1" = "$P2" ] || { echo "The two entries don't match. Nothing changed."; exit 1; }
[ "${#P1}" -ge 8 ] || { echo "Use at least 8 characters. Nothing changed."; exit 1; }
case "$P1" in *"'"*) echo "Don't use a single quote ('). Nothing changed."; exit 1 ;; esac

KEY="$KEY" NEWPW="$P1" python3 - <<'EOF'
import os
key, pw = os.environ["KEY"], os.environ["NEWPW"]
lines = open(".env", encoding="utf-8").read().splitlines()
line = f"{key}='{pw}'"  # single quotes: docker compose reads $ # and spaces literally
out = [line if l.startswith(key + "=") else l for l in lines]
if out == lines and not any(l.startswith(key + "=") for l in lines):
    out.append(line)
open(".env", "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
EOF
chmod 600 .env
echo "Saved. Restarting the board (your NAS sudo password is needed next)..."
sudo /usr/local/bin/docker-compose up -d --build --force-recreate
echo "Done. Log in at http://home-nas:8095/login with the new password."
