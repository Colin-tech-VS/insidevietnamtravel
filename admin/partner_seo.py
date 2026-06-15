"""SEO, schéma JSON-LD et maillage interne — pages partenaires publiques."""

from __future__ import annotations

import re

import config
from admin.partner_portal_service import (
    PROFILE_TYPE_LABELS,
    list_public_partners,
    page_public_highlights,
)
from i18n_utils import lang_url

PROFILE_TYPE_I18N = {
    "guide": {"fr": "Guide local Vietnam", "en": "Local Vietnam guide"},
    "influenceur": {"fr": "Influenceur voyage Vietnam", "en": "Vietnam travel influencer"},
    "blogueur": {"fr": "Blogueur voyage Vietnam", "en": "Vietnam travel blogger"},
    "agence": {"fr": "Agence locale Vietnam", "en": "Local Vietnam travel agency"},
    "hotel": {"fr": "Hébergement Vietnam", "en": "Vietnam accommodation"},
    "autre": {"fr": "Partenaire voyage Vietnam", "en": "Vietnam travel partner"},
}

PROFILE_SCHEMA_TYPE = {
    "guide": "TouristGuide",
    "influenceur": "Person",
    "blogueur": "Person",
    "agence": "TravelAgency",
    "hotel": "LodgingBusiness",
    "autre": "LocalBusiness",
}

# Hero par défaut si le partenaire n'a pas uploadé d'image
_CITY_HERO_IMAGES: list[tuple[str, str]] = [
    ("ho chi minh", "/static/images/destinations/ho-chi-minh-city-960.webp"),
    ("hô chi minh", "/static/images/destinations/ho-chi-minh-city-960.webp"),
    ("saigon", "/static/images/destinations/ho-chi-minh-city-960.webp"),
    ("hanoi", "/static/images/destinations/hanoi-960.webp"),
    ("hà nội", "/static/images/destinations/hanoi-960.webp"),
    ("hoi an", "/static/images/destinations/hoi-an-960.webp"),
    ("hội an", "/static/images/destinations/hoi-an-960.webp"),
    ("da nang", "/static/images/destinations/da-nang-960.webp"),
    ("đà nẵng", "/static/images/destinations/da-nang-960.webp"),
    ("hue", "/static/images/destinations/hue-960.webp"),
    ("huế", "/static/images/destinations/hue-960.webp"),
    ("halong", "/static/images/destinations/halong-960.webp"),
    ("ha long", "/static/images/destinations/halong-960.webp"),
    ("sapa", "/static/images/destinations/sapa-960.webp"),
    ("phu quoc", "/static/images/destinations/phu-quoc-960.webp"),
    ("phú quốc", "/static/images/destinations/phu-quoc-960.webp"),
    ("mekong", "/static/images/destinations/delta-du-mekong-960.webp"),
    ("can tho", "/static/images/destinations/delta-du-mekong-960.webp"),
    ("cần thơ", "/static/images/destinations/delta-du-mekong-960.webp"),
]
_DEFAULT_PARTNER_HERO = "/static/images/destinations/hanoi-960.webp"

_HIGHLIGHTS_H2 = re.compile(
    r"<h2[^>]*>\s*(?:Pourquoi|Why|Points?\s+forts|Highlights?|Atouts(?:\s+du\s+partenaire)?).*?</h2>\s*"
    r"(?:<ul[^>]*>.*?</ul>\s*)?",
    re.I | re.S,
)

KEYWORDS_BY_TYPE = {
    "guide": {
        "fr": "guide local Vietnam, guide francophone Vietnam, excursion Vietnam, tour privé Vietnam, guide Hanoï, guide Hội An",
        "en": "local guide Vietnam, French speaking guide Vietnam, Vietnam private tour, Vietnam day trip, Hanoi guide, Hoi An guide",
    },
    "influenceur": {
        "fr": "influenceur voyage Vietnam, créateur contenu Vietnam, Instagram Vietnam, partenaire voyage Vietnam",
        "en": "Vietnam travel influencer, Vietnam content creator, Vietnam travel partner, Vietnam Instagram",
    },
    "blogueur": {
        "fr": "blogueur voyage Vietnam, blog voyage Vietnam, conseils voyage Vietnam, partenaire Vietnam",
        "en": "Vietnam travel blogger, Vietnam travel blog, Vietnam travel tips, Vietnam partner",
    },
    "agence": {
        "fr": "agence locale Vietnam, agence voyage Vietnam, circuit sur mesure Vietnam, DMC Vietnam",
        "en": "local travel agency Vietnam, Vietnam tour operator, bespoke Vietnam trip, Vietnam DMC",
    },
    "hotel": {
        "fr": "hébergement Vietnam, hôtel Vietnam, guesthouse Vietnam, où dormir Vietnam",
        "en": "Vietnam accommodation, Vietnam hotel, guesthouse Vietnam, where to stay Vietnam",
    },
    "autre": {
        "fr": "partenaire Inside Vietnam Travel, expert voyage Vietnam, services voyage Vietnam",
        "en": "Inside Vietnam Travel partner, Vietnam travel expert, Vietnam travel services",
    },
}


def profile_badge(partner: dict, lang: str) -> str:
    key = (partner or {}).get("profile_type") or "autre"
    if lang == "en":
        return PROFILE_TYPE_I18N.get(key, PROFILE_TYPE_I18N["autre"])["en"]
    return PROFILE_TYPE_I18N.get(key, PROFILE_TYPE_I18N["autre"])["fr"]


def profile_type_label(partner: dict, lang: str) -> str:
    key = (partner or {}).get("profile_type") or "autre"
    if lang == "en":
        labels = {
            "guide": "Local guide",
            "influenceur": "Travel influencer",
            "blogueur": "Travel blogger",
            "agence": "Local agency",
            "hotel": "Accommodation",
            "autre": "Partner",
        }
        return labels.get(key, "Partner")
    return PROFILE_TYPE_LABELS.get(key, "Partenaire")


def meta_keywords(page: dict, partner: dict, lang: str) -> str:
    lang = "en" if lang == "en" else "fr"
    ptype = (partner or {}).get("profile_type") or "autre"
    base = KEYWORDS_BY_TYPE.get(ptype, KEYWORDS_BY_TYPE["autre"])[lang]
    extra = (page.get("extra") or {})
    city = (extra.get("city") or partner.get("city") or "").strip()
    title = (page.get("title") or partner.get("business_name") or "").strip()
    parts = [base]
    if city:
        parts.append(f"{city} Vietnam" if lang == "en" else f"{city} Vietnam voyage")
    if title:
        parts.append(title)
    parts.append("Inside Vietnam Travel")
    return ", ".join(dict.fromkeys(p.strip() for p in parts if p.strip()))


def _abs_url(path: str | None) -> str | None:
    if not path:
        return None
    path = path.strip()
    if not path:
        return None
    if path.startswith("http"):
        return path
    return config.SITE_URL.rstrip("/") + ("/" + path.lstrip("/"))


def _city_slug(city: str) -> str | None:
    from admin.store import slugify
    from admin.store import get_destinations_dict

    city = (city or "").strip()
    if not city:
        return None
    dests = get_destinations_dict("fr")
    for slug, d in dests.items():
        if city.lower() in (d.get("name") or "").lower() or city.lower() in slug.replace("-", " "):
            return slug
    alt = slugify(city)
    return alt if alt in dests else None


def maillage_links(page: dict, partner: dict, lang: str, *, limit: int = 6) -> list[dict]:
    """Liens internes contextuels pour la page partenaire."""
    lang = "en" if lang == "en" else "fr"
    links: list[dict] = []
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    slug = page.get("slug") or ""

    dest_slug = _city_slug(city)
    if dest_slug:
        links.append({
            "url": lang_url("destination_page", lang, slug=dest_slug),
            "title": (
                f"Vietnam travel guide — {city}"
                if lang == "en"
                else f"Guide voyage {city}, Vietnam"
            ),
            "hint": "Destination" if lang == "en" else "Destination",
        })

    links.append({
        "url": lang_url("become_partner", lang),
        "title": "Become a partner" if lang == "en" else "Devenir partenaire",
        "hint": "Program" if lang == "en" else "Programme",
    })
    links.append({
        "url": lang_url("partners_index", lang),
        "title": "Our Vietnam partners" if lang == "en" else "Nos partenaires Vietnam",
        "hint": "Directory" if lang == "en" else "Annuaire",
    })
    links.append({
        "url": lang_url("prepare_trip", lang),
        "title": "Plan your Vietnam trip" if lang == "en" else "Préparer son voyage Vietnam",
        "hint": "Guide" if lang == "en" else "Guide",
    })

    ptype = partner.get("profile_type") or ""
    tool_map = {
        "guide": "best_season",
        "agence": "budget_tool",
        "hotel": "essentials_tool",
    }
    tool_ep = tool_map.get(ptype)
    if tool_ep:
        links.append({
            "url": lang_url(tool_ep, lang),
            "title": "Travel tools" if lang == "en" else "Outils voyage",
            "hint": "Tool" if lang == "en" else "Outil",
        })

    for other in related_partners(slug, city, partner.get("profile_type"), lang, limit=4):
        links.append(other)

    seen: set[str] = set()
    out: list[dict] = []
    for item in links:
        url = item.get("url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
        if len(out) >= limit:
            break
    return out


def related_partners(
    current_slug: str,
    city: str,
    profile_type: str | None,
    lang: str,
    *,
    limit: int = 4,
) -> list[dict]:
    from admin.partner_discovery import partner_destination_slug

    lang = "en" if lang == "en" else "fr"
    current_slug = (current_slug or "").strip().lower()
    city = (city or "").strip().lower()
    ptype = (profile_type or "").strip()
    scored: list[tuple[int, dict]] = []

    for entry in list_public_partners():
        slug = (entry.get("slug") or "").lower()
        if not slug or slug == current_slug:
            continue
        partner = entry.get("partner") or {}
        extra = entry.get("extra") or {}
        entry_city = (extra.get("city") or partner.get("city") or "").strip().lower()
        entry_dest = partner_destination_slug(entry) or ""
        score = 0
        if ptype and partner.get("profile_type") == ptype:
            score += 2
        if city and entry_city and city == entry_city:
            score += 3
        elif city and entry_city and city in entry_city:
            score += 1
        dest_slug = _city_slug(city) if city else None
        if dest_slug and entry_dest == dest_slug:
            score += 4
        scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], x[1].get("title") or ""))
    out: list[dict] = []
    for _score, entry in scored[:limit]:
        slug = entry.get("slug") or ""
        out.append({
            "url": lang_url("partner_public", lang, slug=slug),
            "title": entry.get("title") or slug,
            "hint": profile_type_label(entry.get("partner") or {}, lang),
        })
    return out


def json_ld_graph(page: dict, partner: dict, lang: str, *, canonical_url: str) -> list[dict]:
    lang = "en" if lang == "en" else "fr"
    ptype = (partner or {}).get("profile_type") or "autre"
    schema_type = PROFILE_SCHEMA_TYPE.get(ptype, "LocalBusiness")
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()

    entity: dict = {
        "@type": schema_type,
        "name": page.get("title") or partner.get("business_name") or "Partner",
        "description": page.get("seo_description") or page.get("tagline") or "",
        "url": canonical_url,
        "inLanguage": "en-GB" if lang == "en" else "fr-FR",
    }
    image = _abs_url(page.get("image_url"))
    if image:
        entity["image"] = image
    if city:
        entity["areaServed"] = {"@type": "City", "name": city}
    if partner.get("website"):
        entity["sameAs"] = partner["website"]

    profile_page = {
        "@type": "ProfilePage",
        "name": page.get("seo_title") or page.get("title") or entity["name"],
        "description": entity["description"],
        "url": canonical_url,
        "inLanguage": entity["inLanguage"],
        "mainEntity": {"@id": f"{canonical_url}#partner"},
    }
    entity["@id"] = f"{canonical_url}#partner"

    return [profile_page, entity]


def partner_hero_image(page: dict, partner: dict, *, city: str = "") -> str:
    """Image hero — upload partenaire ou photo destination par défaut."""
    custom = (page.get("image_url") or "").strip()
    if custom:
        return custom
    city_low = (city or "").lower()
    for needle, path in _CITY_HERO_IMAGES:
        if needle in city_low:
            return path
    return _DEFAULT_PARTNER_HERO


def partner_contact_context(page: dict, partner: dict) -> dict:
    """Email / site pour la colonne contact."""
    extra = page.get("extra") or {}
    note = (extra.get("contact_note") or "").strip()
    email = (partner.get("email") or "").strip()
    website = (partner.get("website") or "").strip()
    if not email:
        match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", note)
        if match:
            email = match.group(0)
    return {
        "contact_note": note,
        "contact_note_display": contact_note_display(note, email=email, website=website),
        "contact_email": email,
        "contact_website": website,
    }


def contact_note_display(note: str, *, email: str = "", website: str = "") -> str:
    """Texte contact sans email/URL bruts — le bouton mail suffit."""
    text = (note or "").strip()
    if not text:
        return ""
    if email:
        text = re.sub(re.escape(email), "", text, flags=re.I)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.\w+", "", text)
    if website:
        text = re.sub(re.escape(website), "", text, flags=re.I)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(
        r"(?i)\b("
        r"contactez?[-\s]?moi(?: par email)?(?: à| a)?|"
        r"ou via le formulaire sur|"
        r"send an email to|"
        r"contact me (?:by email )?(?:at|à|a)?|"
        r"reach (?:out )?(?:at|à|a)?"
        r")\b",
        "",
        text,
    )
    text = re.sub(r"\s{2,}", " ", text).strip(" .,;—–-|")
    pour = re.search(r"(?i)\b(pour [^.!?]+[.!?]?)\s*$", text)
    if pour:
        text = pour.group(1).strip()
    if len(text) < 12:
        return ""
    return text[0].upper() + text[1:] if text else ""


def format_partner_languages(raw: str) -> str:
    """Affichage propre des langues (Français, Anglais…)."""
    if not (raw or "").strip():
        return ""
    labels = {
        "francais": "Français",
        "français": "Français",
        "french": "Français",
        "anglais": "Anglais",
        "english": "Anglais",
        "vietnamien": "Vietnamien",
        "vietnamese": "Vietnamien",
    }
    parts = re.split(r"[,;/|]+", raw)
    out: list[str] = []
    seen: set[str] = set()
    for part in parts:
        key = part.strip().lower()
        if not key:
            continue
        label = labels.get(key, part.strip().capitalize())
        low = label.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(label)
    return ", ".join(out)


def _services_html_for_display(page: dict, highlights: list[str]) -> str:
    """HTML prestations — retire seulement un bloc « Pourquoi choisir » dupliqué."""
    html = (page.get("services_html") or "").strip()
    if not html:
        return html
    if highlights and _HIGHLIGHTS_H2.search(html):
        cleaned = _HIGHLIGHTS_H2.sub("", html, count=1).strip()
        if cleaned:
            return cleaned
    return html


def build_public_page_context(page: dict, partner: dict, lang: str, *, canonical_url: str) -> dict:
    """Variables template pour partner_public.html."""
    from admin.partner_portal_service import ensure_page_profile_highlights

    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    highlights = ensure_page_profile_highlights(page, persist=True)
    hero_image = partner_hero_image(page, partner, city=city)
    contact = partner_contact_context(page, partner)
    services_html = _services_html_for_display(page, highlights)
    return {
        "profile_badge": profile_badge(partner, lang),
        "profile_label": profile_type_label(partner, lang),
        "meta_keywords": meta_keywords(page, partner, lang),
        "maillage_links": maillage_links(page, partner, lang),
        "related_partners": related_partners(
            page.get("slug") or "",
            city,
            partner.get("profile_type"),
            lang,
            limit=4,
        ),
        "json_ld_schemas": json_ld_graph(page, partner, lang, canonical_url=canonical_url),
        "og_image": hero_image if hero_image.startswith("http") else hero_image or None,
        "og_image_alt": page.get("seo_title") or page.get("title") or "",
        "partner_city": city,
        "partner_languages": format_partner_languages(partner.get("languages") or ""),
        "partner_highlights": highlights,
        "services_html_display": services_html,
        "hero_image": hero_image,
        **contact,
    }


def partners_index_meta(lang: str) -> dict[str, str]:
    is_en = lang == "en"
    return {
        "meta_title": (
            "Vietnam travel partners — local guides, influencers & agencies"
            if is_en
            else "Partenaires voyage Vietnam — guides, influenceurs et agences"
        ),
        "meta_description": (
            "Meet Inside Vietnam Travel's verified partners: local guides, travel influencers, "
            "bloggers and agencies across Vietnam. Find the right expert for your trip."
            if is_en
            else "Découvrez les partenaires vérifiés Inside Vietnam Travel : guides locaux, "
            "influenceurs voyage, blogueurs et agences au Vietnam. Trouvez l'expert idéal pour votre séjour."
        ),
        "meta_keywords": (
            "Vietnam travel partners, local guide Vietnam, Vietnam influencer, Vietnam travel blogger, "
            "Vietnam travel agency, Inside Vietnam Travel partners"
            if is_en
            else "partenaires voyage Vietnam, guide local Vietnam, influenceur Vietnam, blogueur voyage Vietnam, "
            "agence locale Vietnam, annuaire partenaires Vietnam, Inside Vietnam Travel"
        ),
    }


def partners_index_json_ld(partners: list[dict], lang: str, *, canonical_url: str) -> list[dict]:
    is_en = lang == "en"
    items = []
    for idx, entry in enumerate(partners[:50], start=1):
        slug = entry.get("slug") or ""
        if not slug:
            continue
        items.append({
            "@type": "ListItem",
            "position": idx,
            "name": entry.get("title") or slug,
            "url": config.SITE_URL.rstrip("/") + lang_url("partner_public", lang, slug=slug),
        })
    collection = {
        "@type": "CollectionPage",
        "name": partners_index_meta(lang)["meta_title"],
        "description": partners_index_meta(lang)["meta_description"],
        "url": canonical_url,
        "inLanguage": "en-GB" if is_en else "fr-FR",
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(items),
            "itemListElement": items,
        },
    }
    return [collection]
