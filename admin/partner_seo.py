"""SEO, schéma JSON-LD et maillage interne — pages partenaires publiques."""

from __future__ import annotations

import config
from admin.partner_portal_service import PROFILE_TYPE_LABELS, list_public_partners
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
        score = 0
        if ptype and partner.get("profile_type") == ptype:
            score += 2
        if city and entry_city and city == entry_city:
            score += 3
        elif city and entry_city and city in entry_city:
            score += 1
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


def build_public_page_context(page: dict, partner: dict, lang: str, *, canonical_url: str) -> dict:
    """Variables template pour partner_public.html."""
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    image = page.get("image_url") or ""
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
        "og_image": image if image.startswith("http") else image or None,
        "og_image_alt": page.get("seo_title") or page.get("title") or "",
        "partner_city": city,
        "partner_languages": (partner.get("languages") or "").strip(),
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
