"""SEO, schéma JSON-LD et maillage interne — pages partenaires publiques."""

from __future__ import annotations

import re

import config
from admin.partner_portal_service import (
    PROFILE_TYPE_LABELS,
    list_public_partners,
    page_public_highlights,
)
from admin.partner_seo_keywords import (
    _contains_vietnam_intent,
    _truncate,
    city_keyword_phrases,
    seed_keywords,
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
        "fr": "guide local Vietnam, guide francophone Vietnam, excursion Vietnam, tour privé Vietnam, visite guidée Vietnam, circuit sur mesure Vietnam, guide Hanoï, guide Hội An, préparer voyage Vietnam",
        "en": "local guide Vietnam, French speaking guide Vietnam, Vietnam private tour, Vietnam day trip, guided tour Vietnam, bespoke Vietnam trip, Hanoi guide, Hoi An guide, plan Vietnam trip",
    },
    "influenceur": {
        "fr": "influenceur voyage Vietnam, créateur contenu Vietnam, Instagram Vietnam voyage, TikTok Vietnam, partenaire voyage Vietnam, conseils voyage Vietnam",
        "en": "Vietnam travel influencer, Vietnam content creator, Vietnam travel Instagram, Vietnam travel tips, Vietnam travel partner",
    },
    "blogueur": {
        "fr": "blogueur voyage Vietnam, blog voyage Vietnam, conseils voyage Vietnam, itinéraire Vietnam blog, guide pratique Vietnam, partenaire Vietnam",
        "en": "Vietnam travel blogger, Vietnam travel blog, Vietnam travel tips, Vietnam itinerary blog, Vietnam travel guide, Vietnam partner",
    },
    "agence": {
        "fr": "agence locale Vietnam, agence voyage Vietnam, circuit sur mesure Vietnam, DMC Vietnam, séjour Vietnam organisé, voyage Vietnam tout compris, partenaire agence Vietnam",
        "en": "local travel agency Vietnam, Vietnam tour operator, bespoke Vietnam trip, Vietnam DMC, organized Vietnam tour, Vietnam travel agency partner",
    },
    "hotel": {
        "fr": "hébergement Vietnam, hôtel Vietnam, guesthouse Vietnam, où dormir Vietnam, séjour Vietnam, hébergement authentique Vietnam",
        "en": "Vietnam accommodation, Vietnam hotel, guesthouse Vietnam, where to stay Vietnam, Vietnam stay, authentic Vietnam lodging",
    },
    "autre": {
        "fr": "partenaire Inside Vietnam Travel, expert voyage Vietnam, services voyage Vietnam, professionnel tourisme Vietnam, voyage au Vietnam",
        "en": "Inside Vietnam Travel partner, Vietnam travel expert, Vietnam travel services, Vietnam tourism professional, trip to Vietnam",
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
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    title = (page.get("title") or partner.get("business_name") or "").strip()
    parts = [base, city_keyword_phrases(city, lang)]
    for kw in seed_keywords(lang)[:6]:
        parts.append(kw)
    if city:
        parts.append(f"{city} Vietnam" if lang == "en" else f"voyage {city} Vietnam")
    if title:
        parts.append(title)
    parts.append("Inside Vietnam Travel")
    return ", ".join(dict.fromkeys(p.strip() for p in parts if p and p.strip()))


def _profile_type_seo_label(ptype: str, lang: str) -> str:
    labels_fr = {
        "guide": "guide local Vietnam",
        "influenceur": "créateur voyage Vietnam",
        "blogueur": "blogueur voyage Vietnam",
        "agence": "agence locale Vietnam",
        "hotel": "hébergement Vietnam",
        "autre": "partenaire voyage Vietnam",
    }
    labels_en = {
        "guide": "Vietnam local guide",
        "influenceur": "Vietnam travel creator",
        "blogueur": "Vietnam travel blogger",
        "agence": "Vietnam travel agency",
        "hotel": "Vietnam accommodation",
        "autre": "Vietnam travel partner",
    }
    labels = labels_en if lang == "en" else labels_fr
    return labels.get(ptype, labels["autre"])


def optimize_partner_meta(page: dict, partner: dict, lang: str) -> dict[str, str]:
    """Titre & description SEO optimisés pour voyageurs cherchant le Vietnam."""
    lang = "en" if lang == "en" else "fr"
    ptype = (partner or {}).get("profile_type") or "autre"
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    name = (page.get("title") or partner.get("business_name") or "").strip()
    if not name:
        name = f"{partner.get('first_name', '')} {partner.get('last_name', '')}".strip() or "Partner"

    raw_title = (page.get("seo_title") or "").strip()
    raw_desc = (page.get("seo_description") or page.get("tagline") or "").strip()
    type_label = _profile_type_seo_label(ptype, lang)

    if raw_title and _contains_vietnam_intent(raw_title, lang) and 35 <= len(raw_title) <= 68:
        meta_title = raw_title
    elif lang == "en":
        if city:
            meta_title = f"{name} — {type_label} in {city}"
        else:
            meta_title = f"{name} — {type_label}"
        meta_title = _truncate(meta_title, 60)
    else:
        if city:
            meta_title = f"{name} — {type_label} à {city}"
        else:
            meta_title = f"{name} — {type_label}"
        meta_title = _truncate(meta_title, 60)

    if raw_desc and _contains_vietnam_intent(raw_desc, lang) and 120 <= len(raw_desc) <= 165:
        meta_description = raw_desc
    elif lang == "en":
        if city:
            meta_description = (
                f"Plan your Vietnam trip with {name}, verified {type_label} in {city}. "
                f"Tours, local expertise and travel tips — Inside Vietnam Travel partner page."
            )
        else:
            meta_description = (
                f"Plan your trip to Vietnam with {name}, verified {type_label}. "
                f"Local expertise, experiences and travel advice on Inside Vietnam Travel."
            )
    else:
        if city:
            meta_description = (
                f"Préparez votre voyage au Vietnam avec {name}, {type_label} vérifié à {city}. "
                f"Excursions, expertise locale et conseils — fiche partenaire Inside Vietnam Travel."
            )
        else:
            meta_description = (
                f"Préparez votre voyage Vietnam avec {name}, {type_label} vérifié. "
                f"Expériences, expertise locale et conseils pratiques — Inside Vietnam Travel."
            )
    meta_description = _truncate(meta_description, 158)

    return {
        "meta_title": meta_title,
        "meta_description": meta_description,
        "og_image_alt": (
            f"{name} — {type_label}" + (f", {city}" if city else "") + ", Vietnam travel"
            if lang == "en"
            else f"{name} — {type_label}" + (f", {city}" if city else "") + ", voyage Vietnam"
        ),
    }


def partner_page_faq_schema(page: dict, partner: dict, lang: str, *, canonical_url: str) -> dict:
    lang = "en" if lang == "en" else "fr"
    name = (page.get("title") or partner.get("business_name") or "Partner").strip()
    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    ptype = profile_type_label(partner, lang).lower()

    if lang == "en":
        items = [
            {
                "q": f"Who is {name} on Inside Vietnam Travel?",
                "a": f"{name} is a verified Vietnam travel {ptype} featured on Inside Vietnam Travel, "
                f"helping travellers plan authentic trips to Vietnam"
                + (f" with a focus on {city}." if city else "."),
            },
            {
                "q": f"How do I contact {name} for a Vietnam trip?",
                "a": "Use the contact button on this page to email the partner directly. "
                "Inside Vietnam Travel validates partner profiles but bookings are handled by the partner.",
            },
            {
                "q": "Are Inside Vietnam Travel partners verified?",
                "a": "Yes. Each partner page is reviewed editorially before publication to ensure "
                "relevant Vietnam travel content and professional presentation.",
            },
        ]
        if city:
            items.insert(1, {
                "q": f"Does {name} offer experiences in {city}, Vietnam?",
                "a": f"This partner profile highlights services and expertise related to {city} "
                f"and Vietnam travel. See the experiences section for details.",
            })
    else:
        items = [
            {
                "q": f"Qui est {name} sur Inside Vietnam Travel ?",
                "a": f"{name} est un {ptype} voyage Vietnam vérifié sur Inside Vietnam Travel, "
                f"pour aider les voyageurs à préparer un séjour authentique au Vietnam"
                + (f" avec une expertise à {city}." if city else "."),
            },
            {
                "q": f"Comment contacter {name} pour un voyage au Vietnam ?",
                "a": "Utilisez le bouton contact sur cette page pour envoyer un email au partenaire. "
                "Inside Vietnam Travel valide les fiches mais la réservation se fait avec le partenaire.",
            },
            {
                "q": "Les partenaires Inside Vietnam Travel sont-ils vérifiés ?",
                "a": "Oui. Chaque fiche est relue éditorialement avant publication pour garantir "
                "un contenu utile aux voyageurs et une présentation professionnelle.",
            },
        ]
        if city:
            items.insert(1, {
                "q": f"{name} propose-t-il des expériences à {city}, Vietnam ?",
                "a": f"Cette fiche met en avant les prestations et l'expertise liées à {city} "
                f"et au voyage au Vietnam. Consultez la section expériences pour le détail.",
            })

    return {
        "@type": "FAQPage",
        "@id": f"{canonical_url}#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in items
        ],
    }


def partners_index_faq_schema(lang: str, *, canonical_url: str) -> dict:
    is_en = lang == "en"
    if is_en:
        items = [
            ("What is the Inside Vietnam Travel partner directory?",
             "A curated list of verified local guides, travel influencers, bloggers and agencies "
             "in Vietnam to help you plan your trip with trusted on-the-ground experts."),
            ("How do I find a local guide in Vietnam?",
             "Browse partners by type and city, open a profile and contact the guide directly. "
             "Each page is editorially reviewed for Vietnam travel relevance."),
            ("Are these partners official Inside Vietnam Travel employees?",
             "No. They are independent professionals we collaborate with. "
             "Inside Vietnam Travel provides the platform and editorial validation."),
            ("I'm a guide or agency in Vietnam — how do I join?",
             "Apply via the partnership program page. After validation, you get a free partner profile "
             "and access to the /partners dashboard."),
        ]
    else:
        items = [
            ("Qu'est-ce que l'annuaire partenaires Inside Vietnam Travel ?",
             "Une sélection de guides locaux, influenceurs voyage, blogueurs et agences vérifiés "
             "au Vietnam pour préparer votre séjour avec des experts terrain de confiance."),
            ("Comment trouver un guide local au Vietnam ?",
             "Parcourez les partenaires par type et ville, ouvrez une fiche et contactez le guide. "
             "Chaque page est validée éditorialement pour le voyage au Vietnam."),
            ("Ces partenaires sont-ils des employés d'Inside Vietnam Travel ?",
             "Non. Ce sont des professionnels indépendants avec lesquels nous collaborons. "
             "Inside Vietnam Travel fournit la plateforme et la validation éditoriale."),
            ("Je suis guide ou agence au Vietnam — comment rejoindre le réseau ?",
             "Candidatez via la page devenir partenaire. Après validation, vous obtenez une fiche "
             "gratuite et l'espace /partners."),
        ]
    return {
        "@type": "FAQPage",
        "@id": f"{canonical_url}#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in items
        ],
    }



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
    links.append({
        "url": lang_url("blog_index", lang),
        "title": "Vietnam travel blog & tips" if lang == "en" else "Blog voyage Vietnam — conseils",
        "hint": "Blog" if lang == "en" else "Blog",
    })
    links.append({
        "url": lang_url("itinerary", lang, slug="10-days-vietnam"),
        "title": "10-day Vietnam itinerary" if lang == "en" else "Itinéraire Vietnam 10 jours",
        "hint": "Itinerary" if lang == "en" else "Itinéraire",
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
        "description": optimize_partner_meta(page, partner, lang)["meta_description"],
        "url": canonical_url,
        "inLanguage": "en-GB" if lang == "en" else "fr-FR",
        "knowsAbout": seed_keywords(lang)[:8],
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

    return [profile_page, entity, partner_page_faq_schema(page, partner, lang, canonical_url=canonical_url)]


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
    from admin.partner_content import public_content_sections
    from admin.partner_portal_service import ensure_page_profile_highlights

    extra = page.get("extra") or {}
    city = (extra.get("city") or partner.get("city") or "").strip()
    highlights = ensure_page_profile_highlights(page, persist=True)
    hero_image = partner_hero_image(page, partner, city=city)
    contact = partner_contact_context(page, partner)
    services_html = _services_html_for_display(page, highlights)
    seo = optimize_partner_meta(page, partner, lang)
    faq = partner_page_faq_schema(page, partner, lang, canonical_url=canonical_url)
    return {
        "profile_badge": profile_badge(partner, lang),
        "profile_label": profile_type_label(partner, lang),
        "meta_keywords": meta_keywords(page, partner, lang),
        "optimized_meta": seo,
        "partner_faq": faq.get("mainEntity", []),
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
        "og_image_alt": seo.get("og_image_alt") or page.get("seo_title") or page.get("title") or "",
        "partner_city": city,
        "partner_languages": format_partner_languages(partner.get("languages") or ""),
        "partner_highlights": highlights,
        "services_html_display": services_html,
        "hero_image": hero_image,
        "profile_content_sections": public_content_sections(page, partner, lang=lang),
        **contact,
    }


def partners_index_meta(lang: str) -> dict[str, str]:
    is_en = lang == "en"
    seeds = ", ".join(seed_keywords("en" if is_en else "fr")[:10])
    return {
        "meta_title": (
            "Vietnam travel partners: local guides, agencies & creators"
            if is_en
            else "Partenaires voyage Vietnam : guides, agences & créateurs"
        ),
        "meta_description": (
            "Find verified Vietnam travel partners — local guides, agencies, bloggers and creators. "
            "Plan your trip to Vietnam with trusted experts in Hanoi, Hoi An, Ho Chi Minh City and more."
            if is_en
            else "Trouvez des partenaires voyage Vietnam vérifiés — guides locaux, agences, blogueurs et créateurs. "
            "Préparez votre voyage au Vietnam avec des experts à Hanoï, Hội An, Ho Chi Minh-Ville et plus."
        ),
        "meta_keywords": (
            "Vietnam travel partners, local guide Vietnam, Vietnam travel agency, plan Vietnam trip, "
            "Vietnam itinerary, Inside Vietnam Travel partners, " + seeds
            if is_en
            else "partenaires voyage Vietnam, guide local Vietnam, agence voyage Vietnam, voyage au Vietnam, "
            "itinéraire Vietnam, préparer voyage Vietnam, Inside Vietnam Travel, " + seeds
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
    return [collection, partners_index_faq_schema(lang, canonical_url=canonical_url)]
