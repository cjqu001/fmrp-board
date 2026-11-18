import sqlite3

from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash

from .models import now_utc

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'editor', 'viewer')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS residents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS labs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY,
    lab_id INTEGER NOT NULL REFERENCES labs(id),
    direction TEXT NOT NULL CHECK (direction IN ('High', 'Low', 'Count')),
    value_text TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    is_deleted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS record_residents (
    record_id INTEGER NOT NULL REFERENCES records(id),
    resident_id INTEGER NOT NULL REFERENCES residents(id),
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (record_id, resident_id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id),
    actor_name TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('create', 'update', 'delete', 'restore')),
    entity TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    before_json TEXT,
    after_json TEXT,
    ip TEXT
);
CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END;
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def sync_users(conn, config):
    """Make the admin and shared editor logins match the passwords in .env."""
    wanted = [
        ("admin", config["ADMIN_NAME"], config["ADMIN_PASSWORD"], "admin"),
        ("editor", "Shared editor", config["EDITOR_PASSWORD"], "editor"),
    ]
    with conn:
        for username, display, password, role in wanted:
            if not password:
                continue
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO users (username, display_name, password_hash, role, active, created_at)"
                    " VALUES (?, ?, ?, ?, 1, ?)",
                    (username, display, generate_password_hash(password), role, now_utc()),
                )
            else:
                if not check_password_hash(row["password_hash"], password):
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE id = ?",
                        (generate_password_hash(password), row["id"]),
                    )
                if row["display_name"] != display:
                    conn.execute("UPDATE users SET display_name = ? WHERE id = ?", (display, row["id"]))


def init_app(app):
    app.teardown_appcontext(close_db)
    conn = connect(app.config["DATABASE"])
    try:
        conn.executescript(SCHEMA)
        sync_users(conn, app.config)
    finally:
        conn.close()
