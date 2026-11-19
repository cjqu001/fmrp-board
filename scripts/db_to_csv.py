"""Copy the live records from the old Flask board's database into the static board's CSV.

    .venv\\Scripts\\python scripts/db_to_csv.py [path/to/board.db] [path/to/board.csv]

Defaults: data/board.db -> docs/board.csv. Rows keep the board's order.
"""
import csv
import sqlite3
import sys
from collections import defaultdict

db_path = sys.argv[1] if len(sys.argv) > 1 else "data/board.db"
out_path = sys.argv[2] if len(sys.argv) > 2 else "docs/board.csv"

db = sqlite3.connect(db_path)
db.row_factory = sqlite3.Row
people = defaultdict(list)
for r in db.execute(
    "SELECT rr.record_id, s.name FROM record_residents rr JOIN residents s ON s.id = rr.resident_id"
    " ORDER BY rr.record_id, rr.position"
):
    people[r["record_id"]].append(r["name"])

rows = db.execute(
    "SELECT r.id, r.direction, r.value_text, r.note, r.updated_at, l.name AS lab"
    " FROM records r JOIN labs l ON l.id = r.lab_id WHERE r.is_deleted = 0"
    " ORDER BY l.sort_order, l.name, r.direction"
).fetchall()

with open(out_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["lab", "direction", "value", "residents", "note", "updated"])
    for r in rows:
        w.writerow([r["lab"], r["direction"], r["value_text"], " / ".join(people[r["id"]]),
                    r["note"], r["updated_at"][:10]])
print(f"Wrote {len(rows)} records to {out_path}")
