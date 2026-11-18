import os

from flask import Flask
from flask_wtf import CSRFProtect

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE=os.environ.get("DATABASE", os.path.join(app.instance_path, "board.db")),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        ADMIN_NAME=os.environ.get("ADMIN_NAME", "Quinones"),
        EDITOR_PASSWORD=os.environ.get("EDITOR_PASSWORD", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set. Copy .env.example to .env and fill it in.")

    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
    csrf.init_app(app)

    from . import db, routes

    db.init_app(app)
    app.register_blueprint(routes.bp)
    app.jinja_env.filters["et"] = routes.fmt_et
    return app
