"""Site configuration — SITE_URL auto-détecté (Scalingo, SITE_URL, ou PUBLIC_IP)."""

import os
from urllib.parse import urlsplit, urlunsplit

PUBLIC_IP = os.environ.get("PUBLIC_IP", "185.135.132.50").strip() or "185.135.132.50"


def _without_www(url: str) -> str:
    """Hôte canonique = apex (sans www) pour les URLs SEO.

    Ne pas en déduire un 301 HTTP www → apex : LWS redirige encore l'apex
    vers www (``Redirect /``), et les deux 301 opposés bouclent.
    """
    url = (url or "").strip().rstrip("/")
    if not url:
        return url
    parts = urlsplit(url)
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        return urlunsplit(parts._replace(netloc=host[4:])).rstrip("/")
    return url


def _resolve_site_url() -> str:
    explicit = os.environ.get("SITE_URL", "").strip()
    if explicit:
        return _without_www(explicit)
    app_name = os.environ.get("SCALINGO_APP", "").strip()
    if app_name:
        region = os.environ.get("SCALINGO_REGION", "osc-fr1").strip() or "osc-fr1"
        return f"https://{app_name}.{region}.scalingo.io"
    return f"http://{PUBLIC_IP}:5002"


SITE_NAME = "Inside Vietnam Travel"
SITE_TAGLINE = "Voyage au Vietnam : guides, itinéraires et conseils"
SITE_TAGLINE_I18N = {
    "fr": SITE_TAGLINE,
    "en": "Vietnam travel: guides, itineraries and tips",
}
SITE_URL = _resolve_site_url()
# Environnement de staging : empêche l'indexation Google du double public du site
# (X-Robots-Tag noindex + robots.txt Disallow all). Désactivé par défaut → aucun
# impact en production. Activer en posant SITE_NOINDEX=true sur l'app de staging.
SITE_NOINDEX = os.environ.get("SITE_NOINDEX", "").strip().lower() in ("1", "true", "yes", "on")
SITE_PUBLIC_DOMAIN = (
    os.environ.get("SITE_PUBLIC_DOMAIN", "insidevietnamtravel.fr")
    .strip()
    .lower()
    .removeprefix("www.")
)
SITE_CANONICAL_URL = _without_www(
    os.environ.get("SITE_CANONICAL_URL", f"https://{SITE_PUBLIC_DOMAIN}").strip()
)


def pdf_flow_base_url() -> str:
    """Base URL fiable pour checkout / téléchargement PDF (hôte canonique apex)."""
    explicit = os.environ.get("PDF_FLOW_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return (SITE_CANONICAL_URL or SITE_URL).rstrip("/")


SITE_DESCRIPTION = (
    "Voyage au Vietnam 2026 : guides, itinéraires 10 et 15 jours, visas et conseils "
    "(Hanoï, Ninh Binh, Hội An, Nha Trang) pour préparer votre séjour."
)
SITE_DESCRIPTION_I18N = {
    "fr": SITE_DESCRIPTION,
    "en": (
        "Vietnam travel 2026: guides, 10- and 15-day itineraries, visas and tips "
        "(Hanoi, Ninh Binh, Hoi An, Nha Trang) to plan your trip."
    ),
}
SITE_KEYWORDS = (
    "voyage Vietnam, guide itinéraire, guide Vietnam, itinéraire Vietnam 10 jours, "
    "itinéraire 15 jours, où dormir à Hanoï, transport Vietnam, Ninh Binh, Hội An, "
    "Nha Trang, Tam Dao, prix visa Vietnam, budget voyage Vietnam"
)
SITE_KEYWORDS_I18N = {
    "fr": SITE_KEYWORDS,
    "en": (
        "Vietnam travel, itinerary guide, Vietnam travel guide, Vietnam itinerary 10 days, "
        "15 days in Vietnam, where to stay in Hanoi, transport Vietnam, Ninh Binh, Hoi An, "
        "Nha Trang, Tam Dao, Vietnam visa price, Vietnam travel budget"
    ),
}
SITE_LANG = "fr"
SITE_TITLE = "Voyage au Vietnam 2026 | Guide Itinéraire & Conseils"
SITE_META_DESCRIPTION = "Préparez votre voyage au Vietnam avec nos guides itinéraires 10 et 15 jours, conseils pratiques et budget. Hanoï, Ninh Binh, Hội An, Nha Trang."
LEGAL_UPDATED = "8 juin 2026"
LEGAL_UPDATED_I18N = {"fr": LEGAL_UPDATED, "en": "8 June 2026"}
SITE_AUTHOR = "Inside Vietnam Travel"
LEGAL_CONTACT_EMAIL = os.environ.get("LEGAL_CONTACT_EMAIL", "contact@insidevietnamtravel.fr")
# Profils sociaux officiels (Facebook, Instagram, etc.) pour le schema Organization
# (sameAs) — séparés par des virgules dans la variable d'env SITE_SOCIAL_URLS.
SITE_SOCIAL_URLS = [
    u.strip() for u in os.environ.get("SITE_SOCIAL_URLS", "").split(",") if u.strip()
]
LEGAL_UPDATED = "8 juin 2026"
GOOGLE_ADS_ID = os.environ.get("GOOGLE_ADS_ID", "AW-18240796234").strip()