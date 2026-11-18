"""Data changes. Every function that changes data writes its audit row on the same
connection; callers wrap the call in `with db:` so both commit or roll back together."""

import json
from datetime import datetime, timezone

DIRECTIONS = ("High", "Low", "Count")


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_audit(db, actor, action, entity, entity_id, before, after):
    db.execute(
        "INSERT INTO audit_log (ts_utc, user_id, actor_name, action, entity, entity_id,"
        " before_json, after_json, ip) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            now_utc(),
            actor.get("user_id"),
            actor["name"],
            action,
            entity,
            entity_id,
            None if before is None else json.dumps(before),
            None if after is None else json.dumps(after),
            actor.get("ip"),
        ),
    )


# ---------- records ----------

def record_snapshot(db, record_id):
    row = db.execute(
        "SELECT r.*, l.name AS lab FROM records r JOIN labs l ON l.id = r.lab_id WHERE r.id = ?",
        (record_id,),
    ).fetchone()
    if row is None:
        return None
    people = db.execute(
        "SELECT s.id, s.name FROM record_residents rr JOIN residents s ON s.id = rr.resident_id"
        " WHERE rr.record_id = ? ORDER BY rr.position",
        (record_id,),
    ).fetchall()
    return {
        "lab_id": row["lab_id"],
        "lab": row["lab"],
        "direction": row["direction"],
        "value_text": row["value_text"],
        "note": row["note"],
        "is_deleted": row["is_deleted"],
        "resident_ids": [p["id"] for p in people],
        "residents": [p["name"] for p in people],
    }


def _set_residents(db, record_id, resident_ids):
    db.execute("DELETE FROM record_residents WHERE record_id = ?", (record_id,))
    seen = []
    for rid in resident_ids:
        if rid not in seen:
            seen.append(rid)
    for pos, rid in enumerate(seen):
        db.execute(
            "INSERT INTO record_residents (record_id, resident_id, position) VALUES (?, ?, ?)",
            (record_id, rid, pos),
        )


def create_record(db, actor, lab_id, direction, value_text, note, resident_ids):
    ts = now_utc()
    cur = db.execute(
        "INSERT INTO records (lab_id, direction, value_text, note, is_deleted, created_at, updated_at, updated_by)"
        " VALUES (?, ?, ?, ?, 0, ?, ?, ?)",
        (lab_id, direction, value_text, note, ts, ts, actor["name"]),
    )
    record_id = cur.lastrowid
    _set_residents(db, record_id, resident_ids)
    write_audit(db, actor, "create", "record", record_id, None, record_snapshot(db, record_id))
    return record_id


def apply_record_state(db, actor, record_id, state, action):
    before = record_snapshot(db, record_id)
    db.execute(
        "UPDATE records SET lab_id = ?, direction = ?, value_text = ?, note = ?, is_deleted = ?,"
        " updated_at = ?, updated_by = ? WHERE id = ?",
        (
            state["lab_id"],
            state["direction"],
            state["value_text"],
            state["note"],
            state["is_deleted"],
            now_utc(),
            actor["name"],
            record_id,
        ),
    )
    _set_residents(db, record_id, state["resident_ids"])
    write_audit(db, actor, action, "record", record_id, before, record_snapshot(db, record_id))


def update_record(db, actor, record_id, **changes):
    state = record_snapshot(db, record_id)
    state.update(changes)
    apply_record_state(db, actor, record_id, state, "update")


def delete_record(db, actor, record_id):
    state = record_snapshot(db, record_id)
    state["is_deleted"] = 1
    apply_record_state(db, actor, record_id, state, "delete")


# ---------- residents ----------

def resident_snapshot(db, resident_id):
    row = db.execute("SELECT name, active FROM residents WHERE id = ?", (resident_id,)).fetchone()
    return None if row is None else {"name": row["name"], "active": row["active"]}


def get_or_create_resident(db, actor, name):
    name = " ".join(name.split())
    row = db.execute("SELECT id FROM residents WHERE lower(name) = lower(?)", (name,)).fetchone()
    if row:
        return row["id"]
    cur = db.execute(
        "INSERT INTO residents (name, active, created_at) VALUES (?, 1, ?)", (name, now_utc())
    )
    write_audit(db, actor, "create", "resident", cur.lastrowid, None, resident_snapshot(db, cur.lastrowid))
    return cur.lastrowid


def set_resident_state(db, actor, resident_id, state, action="update"):
    before = resident_snapshot(db, resident_id)
    db.execute(
        "UPDATE residents SET name = ?, active = ? WHERE id = ?",
        (state["name"], state["active"], resident_id),
    )
    write_audit(db, actor, action, "resident", resident_id, before, resident_snapshot(db, resident_id))


# ---------- labs ----------

def get_or_create_lab(db, actor, name):
    name = " ".join(name.split())
    row = db.execute("SELECT id FROM labs WHERE lower(name) = lower(?)", (name,)).fetchone()
    if row:
        return row["id"]
    next_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM labs").fetchone()[0]
    cur = db.execute("INSERT INTO labs (name, sort_order) VALUES (?, ?)", (name, next_order))
    write_audit(db, actor, "create", "lab", cur.lastrowid, None, {"name": name, "sort_order": next_order})
    return cur.lastrowid


# ---------- restore ----------

def restore_from_audit(db, actor, entry):
    """Put an entity back to how it was before the given audit entry."""
    before = json.loads(entry["before_json"]) if entry["before_json"] else None
    entity, eid = entry["entity"], entry["entity_id"]
    if entity == "record":
        if before is None:  # undoing a create = soft delete
            before = record_snapshot(db, eid)
            before["is_deleted"] = 1
        apply_record_state(db, actor, eid, before, "restore")
    elif entity == "resident":
        if before is None:  # undoing a create = deactivate
            before = resident_snapshot(db, eid)
            before["active"] = 0
        set_resident_state(db, actor, eid, before, "restore")
    else:
        raise ValueError(f"Cannot restore entity type {entity!r}")
