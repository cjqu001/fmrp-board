import json
import re
import sqlite3

import pytest

from app import create_app
from conftest import ADMIN_PW, EDITOR_PW, login, query

NEW_RECORD = {"lab": "1", "direction": "High", "value_text": "166", "resident_ids": ["1"], "note": ""}


def add_record(client, **overrides):
    return client.post("/records/new", data={**NEW_RECORD, **overrides})


def audit(app):
    return query(app, "SELECT * FROM audit_log ORDER BY id")


# ---------- create / edit / delete write audit rows ----------

def test_create_writes_audit_row(app, client):
    login(client, name="Quinones")
    resp = add_record(client)
    assert resp.status_code == 302
    rows = audit(app)
    assert len(rows) == 1
    row = rows[0]
    assert (row["action"], row["entity"], row["actor_name"]) == ("create", "record", "Quinones")
    assert row["before_json"] is None
    after = json.loads(row["after_json"])
    assert after["value_text"] == "166" and after["residents"] == ["Hammer"]


def test_edit_writes_before_and_after(app, client):
    login(client)
    add_record(client)
    client.post("/records/1/edit", data={**NEW_RECORD, "value_text": "186", "resident_ids": ["2"]})
    row = audit(app)[-1]
    assert row["action"] == "update"
    assert json.loads(row["before_json"])["value_text"] == "166"
    assert json.loads(row["after_json"])["value_text"] == "186"
    assert json.loads(row["after_json"])["residents"] == ["Talebi"]


def test_delete_is_soft_and_audited(app, client):
    login(client)
    add_record(client)
    client.post("/records/1/delete")
    assert query(app, "SELECT is_deleted FROM records WHERE id = 1") == [{"is_deleted": 1}]
    row = audit(app)[-1]
    assert row["action"] == "delete"
    assert "166" not in client.get("/").get_data(as_text=True).split("<tbody>")[1]


def test_new_lab_and_resident_are_created_and_audited(app, client):
    login(client)
    add_record(client, lab="__other__", new_lab="Ammonia", resident_ids=[], new_residents="Smith, Nguyen")
    rec = query(app, "SELECT * FROM records")[0]
    assert query(app, "SELECT name FROM labs WHERE id = ?", (rec["lab_id"],)) == [{"name": "Ammonia"}]
    entities = [r["entity"] for r in audit(app)]
    assert entities == ["lab", "resident", "resident", "record"]


def test_value_allows_symbols(app, client):
    login(client)
    add_record(client, value_text=">10,000 mg/dL +")
    assert query(app, "SELECT value_text FROM records") == [{"value_text": ">10,000 mg/dL +"}]


def test_admin_restore_undoes_change(app, client):
    login(client)
    add_record(client)
    client.post("/records/1/edit", data={**NEW_RECORD, "value_text": "186"})
    update_id = audit(app)[-1]["id"]
    client.post("/logout")
    login(client, role="admin")
    client.post(f"/log/{update_id}/restore")
    assert query(app, "SELECT value_text FROM records WHERE id = 1") == [{"value_text": "166"}]
    assert audit(app)[-1]["action"] == "restore"


def test_editor_cannot_restore(app, client):
    login(client)
    add_record(client)
    assert client.post("/log/1/restore").status_code == 403


# ---------- viewers cannot edit ----------

def post_routes(app):
    out = []
    for rule in app.url_map.iter_rules():
        if "POST" in rule.methods and rule.endpoint not in ("main.login", "main.logout"):
            out.append(re.sub(r"<[^>]+>", "1", rule.rule))
    return out


def test_viewer_sees_board_without_login(client):
    assert client.get("/").status_code == 200


def test_viewer_cannot_post_anything(app, client):
    login(client)
    add_record(client)
    client.post("/logout")
    before_records = query(app, "SELECT * FROM records")
    before_audit = audit(app)
    routes = post_routes(app)
    assert "/records/new" in routes and "/records/1/edit" in routes
    for url in routes:
        resp = client.post(url, data={**NEW_RECORD, "name": "x", "value_text": "999"})
        assert resp.status_code == 302 and "/login" in resp.headers["Location"], url
    assert query(app, "SELECT * FROM records") == before_records
    assert audit(app) == before_audit


def test_viewer_cannot_open_edit_pages(client):
    for url in ("/records/new", "/residents", "/log", "/log.csv"):
        resp = client.get(url)
        assert resp.status_code == 302 and "/login" in resp.headers["Location"], url


def test_password_ignores_surrounding_spaces(client):
    resp = client.post("/login", data={"password": f"  {ADMIN_PW} \n", "name": ""})
    assert resp.status_code == 302


def test_wrong_password_and_missing_name(client):
    assert "Wrong password" in client.post("/login", data={"password": "nope", "name": "a"}).get_data(as_text=True)
    assert "Type your name" in client.post("/login", data={"password": EDITOR_PW}).get_data(as_text=True)


# ---------- audit log cannot be modified ----------

def test_audit_log_is_append_only_in_database(app, client):
    login(client)
    add_record(client)
    with sqlite3.connect(app.config["DATABASE"]) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE audit_log SET actor_name = 'someone else'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM audit_log")


def test_no_route_changes_existing_audit_rows(app, client):
    """Hit every route with every method as admin; earlier audit rows must be unchanged."""
    login(client)
    add_record(client)
    client.post("/records/1/edit", data={**NEW_RECORD, "value_text": "186"})
    original = audit(app)
    for rule in app.url_map.iter_rules():
        if rule.endpoint in ("main.logout", "static"):
            continue
        url = re.sub(r"<[^>]+>", "1", rule.rule)
        for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            login(client, role="admin")
            client.open(url, method=method, data={**NEW_RECORD, "name": "x", "value_text": "777"})
    after = audit(app)
    assert after[: len(original)] == original


def test_no_log_route_accepts_update_methods(client):
    login(client, role="admin")
    for url in ("/log", "/log/1", "/log.csv"):
        for method in ("PUT", "PATCH", "DELETE"):
            assert client.open(url, method=method).status_code in (404, 405)


# ---------- CSRF ----------

def test_csrf_required_when_enabled(tmp_path):
    app = create_app({"SECRET_KEY": "t", "DATABASE": str(tmp_path / "c.db"),
                      "ADMIN_PASSWORD": ADMIN_PW, "EDITOR_PASSWORD": EDITOR_PW})
    client = app.test_client()
    assert client.post("/login", data={"password": EDITOR_PW, "name": "x"}).status_code == 400


# ---------- seed ----------

def test_seed_loads_board_and_bun_history(app):
    import importlib.util
    import pathlib
    spec = importlib.util.spec_from_file_location(
        "seed_board", pathlib.Path(__file__).parents[1] / "scripts" / "seed_board.py")
    seed_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_mod)
    with app.app_context():
        from app.db import get_db
        db = get_db()
        with db:
            db.execute("DELETE FROM residents")  # start from the real board only
            db.execute("DELETE FROM labs")
        assert seed_mod.seed(db) == 55  # rows in the handoff table
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert "Glucose (high)" in html and "Glucose (low)" in html and ">Hgb<" in html
    bun = query(app, "SELECT r.id FROM records r JOIN labs l ON l.id = r.lab_id WHERE l.name = 'BUN'")[0]["id"]
    page = client.get(f"/records/{bun}").get_data(as_text=True)
    assert "166" in page and "186" in page and "Hammer" in page and "Talebi" in page
