"""Authentification admin simple."""

import os
from functools import wraps

from flask import redirect, session, url_for


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated


def check_password(password: str) -> bool:
    expected = os.environ.get("ADMIN_PASSWORD", "admin123")
    return password == expected


def do_login():
    session["admin_logged_in"] = True
    session.permanent = True


def do_logout():
    session.pop("admin_logged_in", None)
