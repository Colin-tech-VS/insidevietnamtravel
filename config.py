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
SITE_TAGLINE_I18N = {
    "fr": SITE_TAGLINE,
    "en": "Guides, itineraries and tips for travelling in Vietnam",
}
SITE_URL = _resolve_site_url()
SITE_DESCRIPTION = (
    "Préparez votre voyage au Vietnam : itinéraires jour par jour, guides Hanoï, Hội An, "
    "Saigon et Đà Nẵng, visa, budget, eSIM et conseils pour voyageurs français."
)
SITE_DESCRIPTION_I18N = {
    "fr": SITE_DESCRIPTION,
    "en": (
        "Plan your Vietnam trip: day-by-day itineraries, Hanoi, Hội An, "
        "Saigon and Đà Nẵng guides, visa, budget, eSIM and travel tips."
    ),
}
SITE_KEYWORDS = (
    "voyage Vietnam, guide Vietnam, itinéraire Vietnam, préparer voyage Vietnam, "
    "Hanoï, Hội An, Ho Chi Minh, Đà Nẵng, budget Vietnam, visa Vietnam, voyageurs français"
)
SITE_KEYWORDS_I18N = {
    "fr": SITE_KEYWORDS,
    "en": (
        "Vietnam travel, Vietnam guide, Vietnam itinerary, plan Vietnam trip, "
        "Hanoi, Hội An, Ho Chi Minh, Đà Nẵng, Vietnam budget, Vietnam visa"
    ),
}
SITE_LANG = "fr"
LEGAL_UPDATED = "8 juin 2026"
LEGAL_UPDATED_I18N = {"fr": LEGAL_UPDATED, "en": "8 June 2026"}
SITE_AUTHOR = "Inside Vietnam Travel"
LEGAL_CONTACT_EMAIL = os.environ.get("LEGAL_CONTACT_EMAIL", "contact@insidevietnamtravel.fr")
LEGAL_UPDATED = "8 juin 2026"
