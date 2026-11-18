import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from app.db import get_db  # noqa: E402

ADMIN_PW, EDITOR_PW = "admin-test-pw", "editor-test-pw"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "test.db"),
        "ADMIN_PASSWORD": ADMIN_PW,
        "EDITOR_PASSWORD": EDITOR_PW,
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        db = get_db()
        with db:
            db.execute("INSERT INTO labs (name, sort_order) VALUES ('BUN', 1)")
            db.execute("INSERT INTO residents (name, active, created_at) VALUES ('Hammer', 1, 'x')")
            db.execute("INSERT INTO residents (name, active, created_at) VALUES ('Talebi', 1, 'x')")
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, role="editor", name="Dr Test"):
    pw = ADMIN_PW if role == "admin" else EDITOR_PW
    return client.post("/login", data={"password": pw, "name": name})


def query(app, sql, args=()):
    with app.app_context():
        return [dict(r) for r in get_db().execute(sql, args).fetchall()]
