import csv
import io
import json
from collections import defaultdict
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (
    Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

from . import models
from .db import get_db

bp = Blueprint("main", __name__)
ET = ZoneInfo("America/New_York")
MAX_VALUE, MAX_NOTE, MAX_NAME = 40, 200, 60


def fmt_et(ts):
    if not ts:
        return ""
    return datetime.fromisoformat(ts).astimezone(ET).strftime("%Y-%m-%d %H:%M %Z")


# ---------- auth ----------

def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            if role is None:
                return redirect(url_for("main.login", next=request.path))
            if role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return deco


editor_required = role_required("editor", "admin")
admin_required = role_required("admin")


def actor():
    return {"user_id": session["user_id"], "name": session["actor_name"], "ip": request.remote_addr}


@bp.app_context_processor
def inject_role():
    role = session.get("role")
    return {"role": role, "can_edit": role in ("editor", "admin"), "is_admin": role == "admin",
            "actor_name": session.get("actor_name")}


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "").strip()  # copy-paste often adds spaces
        name = " ".join(request.form.get("name", "").split())[:MAX_NAME]
        users = get_db().execute(
            "SELECT * FROM users WHERE active = 1 AND role IN ('admin', 'editor')"
        ).fetchall()
        user = next((u for u in users if check_password_hash(u["password_hash"], password)), None)
        if user is None:
            error = "Wrong password."
        elif user["role"] == "editor" and not name:
            error = "Type your name so the change log shows who made each change."
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["actor_name"] = user["display_name"] if user["role"] == "admin" else name
            nxt = request.args.get("next", "")
            if not nxt.startswith("/") or nxt.startswith("//"):
                nxt = url_for("main.board")
            return redirect(nxt)
    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("main.board"))


# ---------- board ----------

def residents_by_record(db):
    out = defaultdict(list)
    for r in db.execute(
        "SELECT rr.record_id, s.name FROM record_residents rr JOIN residents s ON s.id = rr.resident_id"
        " ORDER BY rr.record_id, rr.position"
    ):
        out[r["record_id"]].append(r["name"])
    return out


@bp.route("/")
def board():
    db = get_db()
    rows = db.execute(
        "SELECT r.id, r.direction, r.value_text, r.note, r.updated_at, l.name AS lab"
        " FROM records r JOIN labs l ON l.id = r.lab_id WHERE r.is_deleted = 0"
        " ORDER BY l.sort_order, l.name, r.direction"
    ).fetchall()
    people = residents_by_record(db)
    dirs = defaultdict(set)
    for r in rows:
        dirs[r["lab"]].add(r["direction"])
    records = []
    for r in rows:
        label = r["lab"]
        if {"High", "Low"} <= dirs[r["lab"]] and r["direction"] in ("High", "Low"):
            label += f" ({r['direction'].lower()})"
        records.append({**dict(r), "label": label, "residents": people[r["id"]]})
    return render_template("board.html", records=records)


# ---------- record add / edit / delete ----------

def form_choices(db):
    labs = db.execute("SELECT id, name FROM labs ORDER BY name COLLATE NOCASE").fetchall()
    residents = db.execute(
        "SELECT id, name FROM residents WHERE active = 1 ORDER BY name COLLATE NOCASE"
    ).fetchall()
    return labs, residents


def read_record_form(db):
    """Validate the form. Returns (cleaned, errors); creates nothing."""
    f = request.form
    errors = []
    lab_choice = f.get("lab", "")
    new_lab = " ".join(f.get("new_lab", "").split())[:MAX_NAME]
    if lab_choice == "__other__":
        if not new_lab:
            errors.append("Type the new lab name.")
        lab_id = None
    else:
        try:
            lab_id = int(lab_choice)
        except ValueError:
            lab_id = None
        if lab_id is None or db.execute("SELECT 1 FROM labs WHERE id = ?", (lab_id,)).fetchone() is None:
            errors.append("Pick a lab.")
    direction = f.get("direction", "")
    if direction not in models.DIRECTIONS:
        errors.append("Pick High, Low or Count.")
    value = f.get("value_text", "").strip()
    if not value:
        errors.append("Value is required.")
    elif len(value) > MAX_VALUE:
        errors.append(f"Value must be {MAX_VALUE} characters or fewer.")
    note = f.get("note", "").strip()
    if len(note) > MAX_NOTE:
        errors.append(f"Note must be {MAX_NOTE} characters or fewer.")
    resident_ids = []
    for v in f.getlist("resident_ids"):
        try:
            resident_ids.append(int(v))
        except ValueError:
            pass
    resident_ids = [
        rid for rid in resident_ids
        if db.execute("SELECT 1 FROM residents WHERE id = ?", (rid,)).fetchone()
    ]
    new_names = [" ".join(n.split())[:MAX_NAME] for n in f.get("new_residents", "").split(",")]
    new_names = [n for n in new_names if n]
    if not resident_ids and not new_names:
        errors.append("Pick at least one resident.")
    cleaned = {"lab_id": lab_id, "new_lab": new_lab, "direction": direction, "value_text": value,
               "note": note, "resident_ids": resident_ids, "new_residents": new_names}
    return cleaned, errors


def resolve_new_items(db, who, cleaned):
    """Create any typed-in lab/residents. Call inside the same transaction as the record change."""
    if cleaned["lab_id"] is None:
        cleaned["lab_id"] = models.get_or_create_lab(db, who, cleaned["new_lab"])
    for name in cleaned["new_residents"]:
        cleaned["resident_ids"].append(models.get_or_create_resident(db, who, name))


@bp.route("/records/new", methods=["GET", "POST"])
@editor_required
def record_new():
    db = get_db()
    labs, residents = form_choices(db)
    errors, form = [], {}
    if request.method == "POST":
        form, errors = read_record_form(db)
        if not errors:
            who = actor()
            with db:
                resolve_new_items(db, who, form)
                rid = models.create_record(db, who, form["lab_id"], form["direction"],
                                           form["value_text"], form["note"], form["resident_ids"])
            flash("Record added.")
            return redirect(url_for("main.record_view", record_id=rid))
    return render_template("record_form.html", labs=labs, residents=residents, errors=errors,
                           form=form, record=None)


def history_for(db, entity, entity_id):
    rows = db.execute(
        "SELECT * FROM audit_log WHERE entity = ? AND entity_id = ? ORDER BY id DESC",
        (entity, entity_id),
    ).fetchall()
    return [decorate(r) for r in rows]


@bp.route("/records/<int:record_id>")
def record_view(record_id):
    db = get_db()
    record = models.record_snapshot(db, record_id)
    if record is None:
        abort(404)
    labs, residents = form_choices(db)
    # put this record's residents first, in their board order, so saving keeps that order
    chosen = record["resident_ids"]
    residents = sorted(residents, key=lambda r: (chosen.index(r["id"]) if r["id"] in chosen else len(chosen)))
    return render_template("record.html", record=record, record_id=record_id, labs=labs,
                           residents=residents, history=history_for(db, "record", record_id),
                           errors=[], form={})


@bp.route("/records/<int:record_id>/edit", methods=["POST"])
@editor_required
def record_edit(record_id):
    db = get_db()
    record = models.record_snapshot(db, record_id)
    if record is None:
        abort(404)
    form, errors = read_record_form(db)
    if errors:
        for e in errors:
            flash(e, "error")
        return redirect(url_for("main.record_view", record_id=record_id))
    who = actor()
    with db:
        resolve_new_items(db, who, form)
        models.update_record(db, who, record_id, lab_id=form["lab_id"], direction=form["direction"],
                             value_text=form["value_text"], note=form["note"],
                             resident_ids=form["resident_ids"])
    flash("Record updated.")
    return redirect(url_for("main.record_view", record_id=record_id))


@bp.route("/records/<int:record_id>/delete", methods=["POST"])
@editor_required
def record_delete(record_id):
    db = get_db()
    record = models.record_snapshot(db, record_id)
    if record is None:
        abort(404)
    if not record["is_deleted"]:
        with db:
            models.delete_record(db, actor(), record_id)
        flash("Record removed from the board. An admin can restore it from the change log.")
    return redirect(url_for("main.board"))


# ---------- residents ----------

@bp.route("/residents", methods=["GET", "POST"])
@editor_required
def residents():
    db = get_db()
    if request.method == "POST":
        name = " ".join(request.form.get("name", "").split())[:MAX_NAME]
        if name:
            with db:
                models.get_or_create_resident(db, actor(), name)
            flash(f"Added {name}.")
        return redirect(url_for("main.residents"))
    rows = db.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM record_residents rr JOIN records r ON r.id = rr.record_id"
        " WHERE rr.resident_id = s.id AND r.is_deleted = 0) AS n_records"
        " FROM residents s ORDER BY s.active DESC, s.name COLLATE NOCASE"
    ).fetchall()
    return render_template("residents.html", residents=rows)


@bp.route("/residents/<int:resident_id>/rename", methods=["POST"])
@editor_required
def resident_rename(resident_id):
    db = get_db()
    state = models.resident_snapshot(db, resident_id)
    if state is None:
        abort(404)
    name = " ".join(request.form.get("name", "").split())[:MAX_NAME]
    if name and name != state["name"]:
        with db:
            models.set_resident_state(db, actor(), resident_id, {**state, "name": name})
        flash(f"Renamed {state['name']} to {name}.")
    return redirect(url_for("main.residents"))


@bp.route("/residents/<int:resident_id>/toggle", methods=["POST"])
@editor_required
def resident_toggle(resident_id):
    db = get_db()
    state = models.resident_snapshot(db, resident_id)
    if state is None:
        abort(404)
    with db:
        models.set_resident_state(db, actor(), resident_id, {**state, "active": 0 if state["active"] else 1})
    return redirect(url_for("main.residents"))


# ---------- change log ----------

FIELDS = [("lab", "Lab"), ("direction", "Direction"), ("value_text", "Value"),
          ("residents", "Residents"), ("note", "Note"), ("is_deleted", "Deleted"),
          ("name", "Name"), ("active", "Active")]


def _fmt(key, v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " / ".join(v)
    if key in ("is_deleted", "active"):
        return "yes" if v else "no"
    return str(v)


def decorate(row):
    before = json.loads(row["before_json"]) if row["before_json"] else None
    after = json.loads(row["after_json"]) if row["after_json"] else None
    changes = []
    for key, label in FIELDS:
        b = before.get(key) if before else None
        a = after.get(key) if after else None
        if b == a or (before is None and a in (None, "", [], 0) and key in ("note", "is_deleted")):
            continue
        if before is None and a is None:
            continue
        changes.append((label, _fmt(key, b), _fmt(key, a)))
    state = after or before or {}
    if row["entity"] == "record":
        what = f"{state.get('lab', '?')} ({state.get('direction', '?')})"
    else:
        what = state.get("name", "")
    return {**dict(row), "before": before, "after": after, "changes": changes, "what": what,
            "ts_et": fmt_et(row["ts_utc"])}


def filtered_log(db):
    lab = request.args.get("lab", "").strip().lower()
    resident = request.args.get("resident", "").strip().lower()
    user = request.args.get("user", "").strip().lower()
    out = []
    for row in db.execute("SELECT * FROM audit_log ORDER BY id DESC"):
        e = decorate(row)
        states = [s for s in (e["before"], e["after"]) if s]
        if lab and not any(s.get("lab", "").lower() == lab for s in states) \
                and not (e["entity"] == "lab" and any(s.get("name", "").lower() == lab for s in states)):
            continue
        if resident and not any(resident in [n.lower() for n in s.get("residents", [])] for s in states) \
                and not (e["entity"] == "resident" and any(s.get("name", "").lower() == resident for s in states)):
            continue
        if user and user not in e["actor_name"].lower():
            continue
        out.append(e)
    return out


@bp.route("/log")
@editor_required
def change_log():
    db = get_db()
    entries = filtered_log(db)
    labs = [r["name"] for r in db.execute("SELECT name FROM labs ORDER BY name COLLATE NOCASE")]
    people = [r["name"] for r in db.execute("SELECT name FROM residents ORDER BY name COLLATE NOCASE")]
    users = [r["actor_name"] for r in db.execute(
        "SELECT DISTINCT actor_name FROM audit_log ORDER BY actor_name COLLATE NOCASE")]
    return render_template("log.html", entries=entries[:500], total=len(entries), labs=labs,
                           people=people, users=users, args=request.args)


@bp.route("/log.csv")
@editor_required
def change_log_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "time_et", "user", "action", "entity", "entity_id", "what", "changes",
                "before_json", "after_json"])
    for e in filtered_log(get_db()):
        changes = "; ".join(f"{label}: {b} -> {a}" for label, b, a in e["changes"])
        w.writerow([e["id"], e["ts_et"], e["actor_name"], e["action"], e["entity"], e["entity_id"],
                    e["what"], changes, e["before_json"] or "", e["after_json"] or ""])
    stamp = datetime.now(ET).strftime("%Y-%m-%d")
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=fmrp-change-log-{stamp}.csv"})


@bp.route("/log/<int:entry_id>/restore", methods=["POST"])
@admin_required
def restore(entry_id):
    db = get_db()
    entry = db.execute("SELECT * FROM audit_log WHERE id = ?", (entry_id,)).fetchone()
    if entry is None or entry["entity"] not in ("record", "resident"):
        abort(404)
    with db:
        models.restore_from_audit(db, actor(), entry)
    flash(f"Undid change #{entry_id}. The undo is itself logged.")
    if entry["entity"] == "record":
        return redirect(url_for("main.record_view", record_id=entry["entity_id"]))
    return redirect(url_for("main.change_log"))
