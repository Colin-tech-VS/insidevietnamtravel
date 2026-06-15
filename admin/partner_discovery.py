"""Découverte partenaires : destinations, recommandations, recherche Mai."""

from __future__ import annotations

import re

from admin.partner_portal_service import list_public_partners
from admin.partner_seo import _city_slug, partner_hero_image, profile_type_label
from i18n_utils import lang_url

_PARTNER_QUERY_WORDS = re.compile(
    r"\b(guide|guides|partenaire|partenaires|partner|partners|influenceur|influencer|"
    r"blogueur|blogger|agence|agency|local|expert|hébergeur|hebergeur|accommodation|"
    r"francophone|french.?speaking)\b",
    re.I,
)

_PROFILE_BOOST = {
    "guide": ("guide", "guide local", "excursion", "tour privé", "private tour"),
    "influenceur": ("influenceur", "influencer", "instagram", "créateur", "creator"),
    "blogueur": ("blogueur", "blogger", "blog"),
    "agence": ("agence", "agency", "circuit", "sur mesure", "dmc"),
    "hotel": ("hôtel", "hotel", "hébergement", "accommodation", "dormir", "stay"),
}


def destination_choices(lang: str = "fr") -> list[dict[str, str]]:
    """Destinations publiées du site — pour les sélecteurs partenaires."""
    from admin.store import get_destinations_dict

    lang = "en" if lang == "en" else "fr"
    dests = get_destinations_dict(lang)
    return sorted(
        [{"slug": slug, "name": (d.get("name") or slug).strip()} for slug, d in dests.items()],
        key=lambda x: x["name"].lower(),
    )


def location_from_destination(value: str, *, lang: str = "fr", required: bool = False) -> dict | None:
    """Valide une ville/slug et renvoie {slug, name} canoniques."""
    from admin.store import get_destinations_dict

    raw = (value or "").strip()
    if not raw:
        if required:
            raise ValueError("Choisissez une destination de la liste.")
        return None

    dests = get_destinations_dict("fr")
    if raw in dests:
        name = get_destinations_dict(lang).get(raw, dests[raw]).get("name") or dests[raw].get("name") or raw
        return {"slug": raw, "name": name.strip()}

    slug = _city_slug(raw)
    if slug and slug in dests:
        name = get_destinations_dict(lang).get(slug, dests[slug]).get("name") or dests[slug].get("name") or raw
        return {"slug": slug, "name": name.strip()}

    if required:
        raise ValueError("Choisissez une destination parmi celles proposées sur le site.")
    return {"slug": slug or "", "name": raw}


def partner_destination_slug(entry: dict) -> str | None:
    """Slug destination associé à une fiche partenaire publiée."""
    extra = entry.get("extra") or {}
    slug = (extra.get("destination_slug") or "").strip()
    if slug:
        from admin.store import get_destinations_dict
        if slug in get_destinations_dict("fr"):
            return slug
    partner = entry.get("partner") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    return _city_slug(city)


def partner_card(entry: dict, lang: str) -> dict:
    """Carte légère pour annuaire, destination ou recommandations."""
    lang = "en" if lang == "en" else "fr"
    partner = entry.get("partner") or {}
    extra = entry.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    slug = entry.get("slug") or ""
    ptype = partner.get("profile_type") or "autre"
    return {
        "slug": slug,
        "title": entry.get("title") or partner.get("business_name") or slug,
        "tagline": entry.get("tagline") or extra.get("pitch") or "",
        "city": city,
        "destination_slug": partner_destination_slug(entry) or "",
        "profile_type": ptype,
        "profile_label": profile_type_label(partner, lang),
        "image": entry.get("image_url") or partner_hero_image(entry, partner, city=city),
        "url": lang_url("partner_public", lang, slug=slug),
    }


def partners_for_destination(dest_slug: str, lang: str = "fr", *, limit: int = 6) -> list[dict]:
    """Partenaires publiés actifs sur une destination."""
    dest_slug = (dest_slug or "").strip()
    if not dest_slug:
        return []
    cards = [
        partner_card(entry, lang)
        for entry in list_public_partners()
        if partner_destination_slug(entry) == dest_slug
    ]
    order = {"guide": 0, "agence": 1, "influenceur": 2, "blogueur": 3, "hotel": 4, "autre": 5}
    cards.sort(key=lambda c: (order.get(c.get("profile_type"), 9), c.get("title", "").lower()))
    return cards[:limit]


def _score_partner_entry(
    entry: dict,
    *,
    destination_slugs: set[str],
    profile_types: set[str],
    query_tokens: set[str],
    lang: str,
) -> int:
    partner = entry.get("partner") or {}
    extra = entry.get("extra") or {}
    ptype = (partner.get("profile_type") or "").strip()
    dest_slug = partner_destination_slug(entry) or ""
    city = (extra.get("city") or partner.get("city") or "").strip().lower()
    hay = " ".join(filter(None, [
        entry.get("title", ""),
        entry.get("tagline", ""),
        extra.get("pitch", ""),
        partner.get("business_name", ""),
        partner.get("bio", ""),
        city,
        ptype,
        profile_type_label(partner, lang),
    ])).lower()
    hay_tokens = set(re.findall(r"[a-z0-9àâäéèêëïîôùûüçœæ]+", hay, re.I))

    score = 0
    if dest_slug and dest_slug in destination_slugs:
        score += 5
    if ptype and ptype in profile_types:
        score += 3
    if query_tokens:
        score += len(query_tokens & hay_tokens) * 2
        if any(tok in hay for tok in query_tokens):
            score += 1
    for ptype_key, needles in _PROFILE_BOOST.items():
        if ptype == ptype_key and any(n in " ".join(query_tokens) for n in needles):
            score += 2
    return score


def recommend_partners(
    *,
    destination_slugs: list[str] | None = None,
    profile_types: list[str] | None = None,
    query: str = "",
    lang: str = "fr",
    exclude_slug: str = "",
    limit: int = 4,
) -> list[dict]:
    """Recommande des partenaires selon villes, type de profil ou requête."""
    lang = "en" if lang == "en" else "fr"
    dest_set = {s.strip() for s in (destination_slugs or []) if s}
    type_set = {t.strip() for t in (profile_types or []) if t}
    q_tokens = set(re.findall(r"[a-z0-9àâäéèêëïîôùûüçœæ]+", (query or "").lower(), re.I))
    exclude = (exclude_slug or "").strip().lower()

    scored: list[tuple[int, dict]] = []
    for entry in list_public_partners():
        slug = (entry.get("slug") or "").lower()
        if not slug or slug == exclude:
            continue
        score = _score_partner_entry(
            entry,
            destination_slugs=dest_set,
            profile_types=type_set,
            query_tokens=q_tokens,
            lang=lang,
        )
        if score > 0 or (dest_set and partner_destination_slug(entry) in dest_set):
            scored.append((score, entry))

    if not scored and query and _PARTNER_QUERY_WORDS.search(query):
        for entry in list_public_partners():
            slug = (entry.get("slug") or "").lower()
            if slug and slug != exclude:
                scored.append((1, entry))

    scored.sort(key=lambda x: (-x[0], (x[1].get("title") or "").lower()))
    return [partner_card(entry, lang) for _s, entry in scored[:limit]]


def partner_knowledge_chunks(lang: str) -> list[dict]:
    """Chunks RAG enrichis pour Mai (guides, agences, influenceurs…)."""
    from admin.store import get_destinations_dict

    lang = "en" if lang == "en" else "fr"
    dests = get_destinations_dict(lang)
    chunks: list[dict] = []

    for entry in list_public_partners():
        slug = entry.get("slug") or ""
        if not slug:
            continue
        partner = entry.get("partner") or {}
        extra = entry.get("extra") or {}
        dest_slug = partner_destination_slug(entry) or ""
        dest_name = dests.get(dest_slug, {}).get("name", "") if dest_slug else ""
        city = (extra.get("city") or partner.get("city") or dest_name or "").strip()
        ptype = partner.get("profile_type") or "autre"
        label = profile_type_label(partner, lang)
        text_parts = [
            label,
            city,
            entry.get("title") or partner.get("business_name") or "",
            entry.get("tagline") or "",
            extra.get("pitch") or "",
            partner.get("bio") or "",
        ]
        overview = (entry.get("overview_html") or "").replace("<", " ").replace(">", " ")
        if overview:
            text_parts.append(overview[:1200])
        services = (entry.get("services_html") or "").replace("<", " ").replace(">", " ")
        if services:
            text_parts.append(services[:800])
        for svc in partner.get("services") or []:
            if isinstance(svc, str) and svc.strip():
                text_parts.append(svc.strip())

        chunks.append({
            "id": f"partner-rich:{slug}",
            "title": entry.get("title") or partner.get("business_name") or slug,
            "url": lang_url("partner_public", lang, slug=slug),
            "group": "Partenaires",
            "text": " ".join(p for p in text_parts if p)[:2200],
            "destination_slug": dest_slug,
            "profile_type": ptype,
        })
    return chunks


def is_partner_search_query(query: str) -> bool:
    return bool(_PARTNER_QUERY_WORDS.search(query or ""))
