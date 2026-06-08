"""Site configuration — SITE_URL auto-détecté sur Scalingo."""

import os


def _resolve_site_url() -> str:
    explicit = os.environ.get("SITE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    app_name = os.environ.get("SCALINGO_APP", "").strip()
    if app_name:
        region = os.environ.get("SCALINGO_REGION", "osc-fr1").strip() or "osc-fr1"
        return f"https://{app_name}.{region}.scalingo.io"
    return "http://localhost:5002"


SITE_NAME = "Inside Vietnam Travel"
SITE_TAGLINE = "Guides, itinéraires et conseils pour voyager au Vietnam"
SITE_URL = _resolve_site_url()
SITE_DESCRIPTION = (
    "Préparez votre voyage au Vietnam : itinéraires jour par jour, guides Hanoï, Hội An, "
    "Saigon et Đà Nẵng, visa, budget, eSIM et conseils pour voyageurs français."
)
SITE_KEYWORDS = (
    "voyage Vietnam, guide Vietnam, itinéraire Vietnam, préparer voyage Vietnam, "
    "Hanoï, Hội An, Ho Chi Minh, Đà Nẵng, budget Vietnam, visa Vietnam, voyageurs français"
)
SITE_LANG = "fr"
SITE_AUTHOR = "Inside Vietnam Travel"
