"""Google Search Console — OAuth2 + Search Analytics API (admin)."""

from __future__ import annotations

import os
import re
import secrets
import time
from datetime import date, timedelta
from urllib.parse import quote, urlencode

import requests

import config

GSC_SCOPE_WEBMASTERS = "https://www.googleapis.com/auth/webmasters.readonly"
GSC_SCOPE_EMAIL = "openid email"
GSC_SCOPES = (GSC_SCOPE_WEBMASTERS, GSC_SCOPE_EMAIL)
GSC_SCOPE = " ".join(GSC_SCOPES)
OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GSC_API = "https://www.googleapis.com/webmasters/v3"
TIMEOUT = (8, 30)


class GscError(RuntimeError):
    pass


def _settings() -> dict:
    try:
        from admin.store import get_settings
        return get_settings()
    except Exception:
        return {}


def _is_masked(value: str) -> bool:
    return bool(re.fullmatch(r"[•*]{3,}\d{0,4}", (value or "").strip()))


def get_client_id() -> str:
    return (
        _settings().get("gsc_client_id")
        or os.environ.get("GOOGLE_GSC_CLIENT_ID", "")
        or os.environ.get("GOOGLE_CLIENT_ID", "")
    ).strip()


def get_client_secret() -> str:
    return (
        _settings().get("gsc_client_secret")
        or os.environ.get("GOOGLE_GSC_CLIENT_SECRET", "")
        or os.environ.get("GOOGLE_CLIENT_SECRET", "")
    ).strip()


def oauth_configured() -> bool:
    return bool(get_client_id() and get_client_secret())


def redirect_uri() -> str:
    """URI de callback OAuth — doit correspondre EXACTEMENT à Google Cloud Console."""
    explicit = os.environ.get("GOOGLE_GSC_REDIRECT_URI", "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = (config.SITE_CANONICAL_URL or config.SITE_URL).rstrip("/")
    return f"{base}/admin/gsc/oauth/callback"


def oauth_error_help(error: str, description: str = "") -> str:
    """Message actionnable pour les erreurs OAuth Google (écran de consentement)."""
    err = (error or "").strip().lower()
    desc = (description or "").strip()
    if err == "access_denied":
        return (
            "Accès refusé par Google (403 access_denied). Votre app OAuth est probablement "
            "en mode « Test » : ajoutez votre adresse Gmail comme utilisateur test dans "
            "Google Cloud Console → OAuth consent screen → Test users "
            "(ex. coco.cayre@gmail.com), puis réessayez. "
            "Utilisez le même compte Google que Search Console. "
            "Pour un accès sans liste de testeurs, publiez l'app (Publishing status → In production) "
            "— une vérification Google peut être requise pour l'API Search Console."
        )
    if err == "redirect_uri_mismatch":
        uri = redirect_uri()
        return (
            f"URI de redirection incorrecte (redirect_uri_mismatch). "
            f"Ajoutez exactement cette URL dans Google Cloud Console → Credentials → "
            f"Authorized redirect URIs : {uri}"
        )
    if desc:
        return f"Erreur Google OAuth ({error}) : {desc}"
    return f"Erreur Google OAuth : {error or 'inconnue'}"


def scope_insufficient_help() -> str:
    return (
        "Google n'a pas accordé l'accès Search Console (scopes insuffisants). "
        "Dans Google Cloud Console → OAuth consent screen → Scopes → Add or remove scopes, "
        "ajoutez « Google Search Console API » "
        f"({GSC_SCOPE_WEBMASTERS}), enregistrez, puis cliquez « Reconnecter » ci-dessous "
        "et acceptez toutes les autorisations demandées."
    )


def _scopes_include_webmasters(scope_str: str) -> bool:
    scopes = (scope_str or "").split()
    return any("webmasters" in s for s in scopes)


def save_oauth_config(client_id: str, client_secret: str) -> None:
    from admin.store import save_settings

    data: dict = {"gsc_client_id": (client_id or "").strip()}
    secret = (client_secret or "").strip()
    if secret and not _is_masked(secret):
        data["gsc_client_secret"] = secret
    save_settings(data)


def masked_client_secret() -> str:
    secret = get_client_secret()
    if not secret:
        return ""
    return "••••••••" + secret[-4:]


def get_refresh_token() -> str:
    return (_settings().get("gsc_refresh_token") or "").strip()


def get_access_token() -> str:
    return (_settings().get("gsc_access_token") or "").strip()


def get_token_expires_at() -> float:
    try:
        return float(_settings().get("gsc_token_expires_at") or 0)
    except (TypeError, ValueError):
        return 0.0


def get_connected_email() -> str:
    return (_settings().get("gsc_connected_email") or "").strip()


def get_site_url() -> str:
    return (_settings().get("gsc_site_url") or "").strip()


def get_granted_scopes() -> str:
    return (_settings().get("gsc_granted_scopes") or "").strip()


def has_webmasters_scope() -> bool:
    stored = get_granted_scopes()
    if stored:
        return _scopes_include_webmasters(stored)
    return is_connected()


def is_connected() -> bool:
    return bool(get_refresh_token())


def _save_granted_scopes(scope_str: str) -> None:
    from admin.store import save_settings
    save_settings({"gsc_granted_scopes": (scope_str or "").strip()})


def _save_tokens(
    *,
    access_token: str,
    refresh_token: str | None = None,
    expires_in: int | None = None,
    email: str | None = None,
) -> None:
    from admin.store import save_settings

    data: dict = {"gsc_access_token": access_token}
    if refresh_token:
        data["gsc_refresh_token"] = refresh_token
    if expires_in is not None:
        data["gsc_token_expires_at"] = time.time() + max(0, int(expires_in) - 60)
    if email:
        data["gsc_connected_email"] = email
    save_settings(data)


def disconnect() -> None:
    from admin.store import save_settings

    save_settings({
        "gsc_refresh_token": "",
        "gsc_access_token": "",
        "gsc_token_expires_at": 0,
        "gsc_connected_email": "",
        "gsc_site_url": "",
        "gsc_granted_scopes": "",
    })


def build_auth_url(state: str) -> str:
    if not oauth_configured():
        raise GscError("Configurez d'abord le Client ID et le Client Secret OAuth Google.")
    params = {
        "client_id": get_client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": GSC_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{OAUTH_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> None:
    if not oauth_configured():
        raise GscError("OAuth Google non configuré.")
    try:
        resp = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": get_client_id(),
                "client_secret": get_client_secret(),
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GscError(f"Connexion à Google impossible : {exc}") from exc
    payload = _json_or_empty(resp)
    if resp.status_code >= 400 or "access_token" not in payload:
        raise GscError(payload.get("error_description") or payload.get("error") or "Échange OAuth échoué.")
    granted = payload.get("scope") or GSC_SCOPE
    if not _scopes_include_webmasters(granted):
        raise GscError(scope_insufficient_help())
    if not payload.get("refresh_token"):
        raise GscError(
            "Google n'a pas renvoyé de refresh token. Déconnectez, puis reconnectez "
            "(l'écran de consentement doit s'afficher avec toutes les autorisations)."
        )
    email = _fetch_user_email(payload["access_token"])
    _save_granted_scopes(granted)
    _save_tokens(
        access_token=payload["access_token"],
        refresh_token=payload.get("refresh_token"),
        expires_in=payload.get("expires_in"),
        email=email,
    )


def _fetch_user_email(access_token: str) -> str:
    try:
        resp = requests.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=TIMEOUT,
        )
        if resp.status_code >= 400:
            return ""
        return (resp.json().get("email") or "").strip()
    except requests.RequestException:
        return ""


def _refresh_access_token() -> str:
    refresh = get_refresh_token()
    if not refresh:
        raise GscError("Search Console non connecté.")
    try:
        resp = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "client_id": get_client_id(),
                "client_secret": get_client_secret(),
                "refresh_token": refresh,
                "grant_type": "refresh_token",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GscError(f"Connexion à Google impossible : {exc}") from exc
    payload = _json_or_empty(resp)
    if resp.status_code >= 400 or "access_token" not in payload:
        msg = payload.get("error_description") or payload.get("error") or "Refresh token invalide."
        if payload.get("error") == "invalid_grant":
            disconnect()
            raise GscError("Session Google expirée — reconnectez Search Console.")
        raise GscError(msg)
    granted = payload.get("scope") or get_granted_scopes()
    if granted:
        _save_granted_scopes(granted)
    if granted and not _scopes_include_webmasters(granted):
        disconnect()
        raise GscError(scope_insufficient_help())
    _save_tokens(
        access_token=payload["access_token"],
        expires_in=payload.get("expires_in"),
    )
    return payload["access_token"]


def valid_access_token() -> str:
    token = get_access_token()
    if token and time.time() < get_token_expires_at():
        return token
    return _refresh_access_token()


def _json_or_empty(resp: requests.Response) -> dict:
    try:
        return resp.json()
    except ValueError:
        return {}


def _api_request(method: str, path: str, *, json_body: dict | None = None) -> dict:
    token = valid_access_token()
    url = f"{GSC_API}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        else:
            resp = requests.post(url, headers=headers, json=json_body or {}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GscError(f"API Search Console indisponible : {exc}") from exc
    payload = _json_or_empty(resp)
    if resp.status_code >= 400:
        err = payload.get("error", {})
        message = err.get("message") if isinstance(err, dict) else str(err)
        message = message or f"Erreur Search Console (HTTP {resp.status_code})."
        if "insufficient authentication scopes" in message.lower():
            disconnect()
            raise GscError(scope_insufficient_help())
        raise GscError(message)
    return payload


def list_sites() -> list[dict]:
    payload = _api_request("GET", "/sites")
    entries = payload.get("siteEntry") or []
    sites = []
    for item in entries:
        url = (item.get("siteUrl") or "").strip()
        if not url:
            continue
        sites.append({
            "site_url": url,
            "permission": item.get("permissionLevel") or "",
        })
    sites.sort(key=lambda s: s["site_url"])
    return sites


def save_site_url(site_url: str) -> None:
    from admin.store import save_settings
    save_settings({"gsc_site_url": (site_url or "").strip()})


def test_connection() -> dict:
    sites = list_sites()
    site = get_site_url()
    if not site and sites:
        save_site_url(sites[0]["site_url"])
        site = sites[0]["site_url"]
    return {
        "email": get_connected_email(),
        "sites_count": len(sites),
        "site_url": site,
    }


def _date_range(days: int) -> tuple[str, str]:
    days = max(1, min(int(days), 480))
    end = date.today() - timedelta(days=3)
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def search_analytics_query(
    site_url: str,
    *,
    start_date: str,
    end_date: str,
    dimensions: list[str] | None = None,
    row_limit: int = 250,
    start_row: int = 0,
) -> dict:
    encoded = quote(site_url, safe="")
    body: dict = {
        "startDate": start_date,
        "endDate": end_date,
        "type": "web",
        "aggregationType": "auto",
        "rowLimit": min(max(int(row_limit), 1), 25000),
        "startRow": max(int(start_row), 0),
    }
    if dimensions:
        body["dimensions"] = dimensions
    return _api_request("POST", f"/sites/{encoded}/searchAnalytics/query", json_body=body)


def _rows_to_list(payload: dict, dim_keys: list[str]) -> list[dict]:
    rows = []
    for row in payload.get("rows") or []:
        keys = row.get("keys") or []
        item = {
            dim_keys[i]: keys[i] if i < len(keys) else ""
            for i in range(len(dim_keys))
        }
        item["clicks"] = int(row.get("clicks") or 0)
        item["impressions"] = int(row.get("impressions") or 0)
        item["ctr"] = round(float(row.get("ctr") or 0) * 100, 2)
        item["position"] = round(float(row.get("position") or 0), 1)
        rows.append(item)
    return rows


def _aggregate_totals(rows: list[dict]) -> dict:
    clicks = sum(r.get("clicks", 0) for r in rows)
    impressions = sum(r.get("impressions", 0) for r in rows)
    if impressions:
        weighted_pos = sum(r.get("position", 0) * r.get("impressions", 0) for r in rows)
        avg_position = round(weighted_pos / impressions, 1)
        ctr = round(clicks / impressions * 100, 2)
    else:
        avg_position = 0.0
        ctr = 0.0
    return {
        "clicks": clicks,
        "impressions": impressions,
        "ctr": ctr,
        "position": avg_position,
    }


def build_report(days: int = 28, query_page: int = 0, query_limit: int = 500) -> dict:
    site = get_site_url()
    if not site:
        sites = list_sites()
        if not sites:
            raise GscError("Aucune propriété Search Console accessible sur ce compte Google.")
        site = sites[0]["site_url"]
        save_site_url(site)

    start_date, end_date = _date_range(days)
    totals_payload = search_analytics_query(site, start_date=start_date, end_date=end_date)
    totals_rows = _rows_to_list(totals_payload, [])
    totals = totals_rows[0] if totals_rows else {
        "clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0,
    }

    daily_payload = search_analytics_query(
        site, start_date=start_date, end_date=end_date, dimensions=["date"], row_limit=500,
    )
    daily = _rows_to_list(daily_payload, ["date"])
    daily.sort(key=lambda r: r["date"])

    queries_payload = search_analytics_query(
        site,
        start_date=start_date,
        end_date=end_date,
        dimensions=["query"],
        row_limit=query_limit,
        start_row=query_page * query_limit,
    )
    queries = _rows_to_list(queries_payload, ["query"])

    pages_payload = search_analytics_query(
        site,
        start_date=start_date,
        end_date=end_date,
        dimensions=["page"],
        row_limit=100,
    )
    pages = _rows_to_list(pages_payload, ["page"])

    devices_payload = search_analytics_query(
        site,
        start_date=start_date,
        end_date=end_date,
        dimensions=["device"],
        row_limit=10,
    )
    devices = _rows_to_list(devices_payload, ["device"])

    countries_payload = search_analytics_query(
        site,
        start_date=start_date,
        end_date=end_date,
        dimensions=["country"],
        row_limit=25,
    )
    countries = _rows_to_list(countries_payload, ["country"])

    return {
        "site_url": site,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "totals": totals,
        "daily": daily,
        "queries": queries,
        "pages": pages,
        "devices": devices,
        "countries": countries,
        "query_page": query_page,
        "query_limit": query_limit,
        "has_more_queries": len(queries) >= query_limit,
    }


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)
