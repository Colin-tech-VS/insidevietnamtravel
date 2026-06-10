"""Réseaux sociaux — inventaire des pages publiables + rédaction IA du post.

`page_inventory()` liste TOUTES les pages publiques sélectionnables (accueil, piliers,
destinations, itinéraires, articles, outils) avec leur URL absolue, un résumé et une
image — sert au sélecteur de l'admin, à la génération IA et au lien publié.

`generate_post()` rédige le texte du post Facebook, soit À PROPOS d'une page choisie
(même thème/sujet, obligatoire), soit à partir d'un brief libre (contenu nouveau).
"""

from __future__ import annotations

import json
from datetime import date

import config
from i18n_utils import lang_url

DEFAULT_OG = "/static/images/pool/1583417319070-4a69db38a482.webp"


def _abs(path: str) -> str:
    base = config.SITE_URL.rstrip("/")
    if not path:
        return base + "/"
    return path if path.startswith("http") else base + path


def _img(url: str | None) -> str:
    if not url:
        return _abs(DEFAULT_OG)
    return _abs(url)


def page_inventory(lang: str = "fr") -> list[dict]:
    """Pages publiables groupées (id, group, label, url, title, summary, image)."""
    from admin.store import get_articles, get_destinations_dict
    from admin.image_service import destination_image_url, persistent_image_url
    from data.itineraries import ITINERARIES
    from data import pillars as P
    from locales.ui import t

    items: list[dict] = []

    # Accueil
    items.append({
        "id": "home", "group": "Accueil",
        "label": "Page d'accueil",
        "url": _abs(lang_url("index", lang)),
        "title": config.SITE_NAME,
        "summary": config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION),
        "image": _img(DEFAULT_OG),
    })

    # Piliers (hubs) + page apps
    for it in P.thematic_list(lang, lang_url):
        if it.get("is_hub"):
            items.append({
                "id": f"pillar:{it['key']}", "group": "Guides (piliers)",
                "label": it["title"], "url": _abs(it["url"]),
                "title": it["title"], "summary": it["lede"],
                "image": _img(f"/static/images/pool/{it['photo_id']}.webp"),
            })
    items.append({
        "id": "apps", "group": "Guides (piliers)",
        "label": t("apps.title", lang), "url": _abs(lang_url("useful_apps", lang)),
        "title": t("apps.title", lang), "summary": t("apps.lead", lang),
        "image": _img("/static/images/pool/1521993117367-b7f70ccd029d.webp"),
    })

    # Destinations
    for slug, d in get_destinations_dict(lang).items():
        items.append({
            "id": f"dest:{slug}", "group": "Destinations",
            "label": d.get("name", slug), "url": _abs(lang_url("destination_page", lang, slug=slug)),
            "title": d.get("name", slug), "summary": d.get("tagline", ""),
            "image": _img(destination_image_url(d.get("image"), d.get("image_photo_id"), d.get("image_source_url"))),
        })

    # Itinéraires
    for slug, itin in ITINERARIES.items():
        block = itin.get("i18n", {}).get(lang, itin) if isinstance(itin, dict) else {}
        title = block.get("title") or itin.get("title", slug)
        items.append({
            "id": f"itinerary:{slug}", "group": "Itinéraires",
            "label": title, "url": _abs(lang_url("itinerary", lang, slug=slug)),
            "title": title, "summary": block.get("meta_description") or itin.get("meta_description", ""),
            "image": _img(itin.get("image")),
        })

    # Articles
    for a in get_articles(lang):
        items.append({
            "id": f"article:{a['slug']}", "group": "Articles de blog",
            "label": a.get("title", a["slug"]), "url": _abs(lang_url("article", lang, slug=a["slug"])),
            "title": a.get("title", ""), "summary": a.get("excerpt", ""),
            "image": _img(persistent_image_url(a.get("image"), a.get("image_photo_id"), a.get("image_source_url"))),
        })

    # Outils & guides pratiques
    tool_pages = (
        ("best_season", "season.title", "season.lead"),
        ("budget_tool", "tools.budget", "budget.lead"),
        ("visa_tool", "visa.title", "visa.lead"),
        ("essentials_tool", "compare.title", "compare.lead"),
        ("useful_apps", "apps.title", "apps.lead"),
        ("safety_guide", "safety.title", "safety.lead"),
        ("customs_guide", "customs.title", "customs.lead"),
        ("phrases_guide", "phrases.title", "phrases.lead"),
        ("prepare_trip", "nav.prepare", "prepare.sub"),
    )
    for endpoint, title_key, lead_key in tool_pages:
        title = t(title_key, lang)
        summary = t(lead_key, lang)
        items.append({
            "id": f"tool:{endpoint}", "group": "Outils",
            "label": title, "url": _abs(lang_url(endpoint, lang)),
            "title": title, "summary": summary,
            "image": _img(DEFAULT_OG),
        })

    return items


def find_page(page_id: str, lang: str = "fr") -> dict | None:
    return next((p for p in page_inventory(lang) if p["id"] == page_id), None)


def default_campaign(page: dict | None, brief: str | None) -> str:
    """Nomenclature de campagne par défaut, cohérente et stable."""
    from admin.facebook_service import sanitize_campaign
    if page:
        return sanitize_campaign("fb-" + page["id"].replace(":", "-"))
    base = (brief or "post")[:40]
    return sanitize_campaign(f"fb-{date.today():%Y%m}-{base}")


# ── Rédaction IA ──────────────────────────────────────────────────────────

def _compose(message: str, hashtags: list[str]) -> str:
    tags = " ".join(h if h.startswith("#") else f"#{h}" for h in hashtags if h)
    message = (message or "").strip()
    return f"{message}\n\n{tags}".strip() if tags else message


def generate_post(*, page: dict | None = None, brief: str | None = None,
                  lang: str = "fr") -> str:
    """Rédige le texte d'un post Facebook (≈ 3-5 lignes + hashtags + emojis)."""
    from admin import ai_client

    ai_client.require_api_key()
    is_fr = lang != "en"

    if page:
        subject = (
            f"PAGE DU SITE à mettre en avant :\n"
            f"- Titre : {page['title']}\n- Résumé : {page['summary']}\n- URL : {page['url']}\n"
            "Le post DOIT parler de CETTE page (même thème, même sujet) et inciter à la visiter."
        )
    else:
        subject = (
            f"SUJET (contenu nouveau) demandé par l'admin :\n{brief}\n"
            "Rédige un post original sur ce sujet, lié au voyage au Vietnam."
        )

    lang_line = ("Rédige en FRANÇAIS." if is_fr else "Write in ENGLISH.")
    system = (
        "Tu es community manager pour « Inside Vietnam Travel », un site de voyage au "
        "Vietnam. Tu écris des posts Facebook engageants, authentiques et utiles."
    )
    user = (
        f"{subject}\n\n{lang_line}\n"
        "Contraintes du post :\n"
        "- Une accroche forte en 1re ligne (emoji possible).\n"
        "- 2 à 4 lignes courtes, concrètes, sans clickbait ni promesse exagérée.\n"
        "- Un appel à l'action clair en fin (ex. « Lien en commentaire » ou « Découvrez le guide »).\n"
        "- 3 à 6 hashtags pertinents (Vietnam, voyage, thème).\n"
        "- Quelques emojis bien placés, ton chaleureux et expert.\n"
        'Réponds STRICTEMENT en JSON : {"message": "...", "hashtags": ["#...", "..."]}'
    )

    resp = ai_client.chat_completion(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        max_tokens=900, temperature=0.8, json_mode=True, fast=True, deadline=60,
    )
    raw = resp.choices[0].message.content
    data = ai_client.parse_json(raw)
    return _compose(data.get("message", ""), data.get("hashtags", []) or [])
