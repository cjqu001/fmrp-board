#!/bin/sh
# Nightly backup of the FMRP board database. Run as root from Synology Task Scheduler:
#   sh /volume1/docker/fmrp-board/scripts/backup_db.sh
# Uses SQLite's online backup API inside the container, so the copy is consistent
# even while someone is editing. Keeps 30 days of backups.
set -eu

DIR=/volume1/docker/fmrp-board
STAMP=$(date +%Y-%m-%d)

/usr/local/bin/docker exec fmrp-board python -c "
import sqlite3
src = sqlite3.connect('/data/board.db')
dst = sqlite3.connect('/backups/board-$STAMP.db')
src.backup(dst)
dst.close(); src.close()
"

find "$DIR/backups" -name 'board-*.db' -type f -mtime +30 -delete
echo "Backed up to $DIR/backups/board-$STAMP.db"
