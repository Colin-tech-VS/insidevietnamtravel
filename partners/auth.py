"""Authentification espace partenaires (/partners)."""

from functools import wraps

from flask import redirect, session, url_for

from admin.partner_portal_service import get_account_by_id


def partner_login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        pid = session.get("partner_id")
        if not pid or not get_account_by_id(pid):
            return redirect(url_for("partners.login", next=request_path()))
        return f(*args, **kwargs)
    return decorated


def request_path() -> str:
    from flask import request
    return (request.full_path or request.path or "").rstrip("?")


def do_partner_login(partner_id: str) -> None:
    session["partner_id"] = partner_id
    session.permanent = True


def do_partner_logout() -> None:
    session.pop("partner_id", None)


def current_partner() -> dict | None:
    pid = session.get("partner_id")
    return get_account_by_id(pid) if pid else None
