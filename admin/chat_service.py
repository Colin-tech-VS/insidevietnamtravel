"""Widget IA public « Mai » — conseillère voyage (Mistral + index dynamique du site)."""

from __future__ import annotations

import re
import time
import unicodedata
from html import unescape

import config
from i18n_utils import lang_url

# Cache mémoire des chunks (invalidé toutes les 5 min — nouvelles pages/articles incluses).
_CHUNK_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300.0
_PLACE_CORRECTIONS: dict[str, list[tuple[re.Pattern[str], str]]] = {}

# Chat public — modèle principal Mistral (qualité), pas le modèle « fast ».
CHAT_MAX_TOKENS = 1100
CHAT_TEMPERATURE = 0.62
CHAT_RETRIEVE_TOP_N = 14

# Rate limit simple par IP (best-effort, par processus).
_RATE: dict[str, list[float]] = {}
_RATE_LOCK = __import__("threading").Lock()
_RATE_WINDOW = 3600
_RATE_MAX = 40
_RATE_BURST = 6
_RATE_BURST_WINDOW = 60

_STOP = {
    "fr": {"le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "au", "aux", "pour", "sur", "avec", "est", "son", "sa", "ses"},
    "en": {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "is", "are", "your", "with"},
}


def is_enabled() -> bool:
    from admin import mistral_client
    return mistral_client.has_api_key()


def _strip_html(text: str, max_len: int = 500) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _abs(path: str) -> str:
    base = config.SITE_URL.rstrip("/")
    if not path:
        return base + "/"
    return path if path.startswith("http") else base + path


def _tokenize(text: str, lang: str) -> set[str]:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    words = re.findall(r"[a-z0-9]{3,}", text)
    stop = _STOP.get(lang, _STOP["fr"])
    return {w for w in words if w not in stop}


def _affiliate_chunks(lang: str, track_url_fn) -> list[dict]:
    """Liens affiliés trackés — l'IA ne cite que des URLs présentes dans le contexte."""
    from admin.store import get_destinations_dict
    from data.trip_planner import _affiliate_links

    dests = get_destinations_dict(lang)
    aff = _affiliate_links(lang, track_url_fn, dests)
    chunks: list[dict] = []

    global_labels = {
        "fr": {
            "esim_airalo": "eSIM Airalo — internet dès l'atterrissage au Vietnam",
            "esim_holafly": "eSIM Holafly — data mobile Vietnam sans carte SIM",
            "insurance": "Assurance voyage — couverture médicale & rapatriement",
        },
        "en": {
            "esim_airalo": "Airalo eSIM — mobile data in Vietnam from landing",
            "esim_holafly": "Holafly eSIM — Vietnam data without a physical SIM",
            "insurance": "Travel insurance — medical cover & repatriation",
        },
    }
    labels = global_labels.get(lang, global_labels["fr"])
    chunks.append({
        "id": "aff:esim_airalo",
        "title": labels["esim_airalo"],
        "url": aff["esim_airalo_url"],
        "group": "Affiliation",
        "text": labels["esim_airalo"],
        "affiliate": True,
    })
    chunks.append({
        "id": "aff:esim_holafly",
        "title": labels["esim_holafly"],
        "url": aff["esim_holafly_url"],
        "group": "Affiliation",
        "text": labels["esim_holafly"],
        "affiliate": True,
    })
    chunks.append({
        "id": "aff:insurance",
        "title": labels["insurance"],
        "url": aff["insurance_url"],
        "group": "Affiliation",
        "text": labels["insurance"],
        "affiliate": True,
    })

    city_labels = {
        "fr": {"hotel": "Hôtels à {city} (Booking)", "activity": "Activités & tours à {city}"},
        "en": {"hotel": "Hotels in {city} (Booking)", "activity": "Activities & tours in {city}"},
    }
    cl = city_labels.get(lang, city_labels["fr"])
    for slug, links in aff.get("cities", {}).items():
        name = dests.get(slug, {}).get("name", slug)
        if links.get("hotel_url"):
            chunks.append({
                "id": f"aff:hotel:{slug}",
                "title": cl["hotel"].format(city=name),
                "url": links["hotel_url"],
                "group": "Affiliation",
                "text": cl["hotel"].format(city=name),
                "affiliate": True,
            })
        if links.get("activity_url"):
            chunks.append({
                "id": f"aff:activity:{slug}",
                "title": cl["activity"].format(city=name),
                "url": links["activity_url"],
                "group": "Affiliation",
                "text": cl["activity"].format(city=name),
                "affiliate": True,
            })
    return chunks


def build_knowledge_chunks(lang: str, track_url_fn) -> list[dict]:
    """Index textuel de TOUT le site public (page_inventory + contenus enrichis)."""
    from admin.social_ai import page_inventory
    from admin.store import get_articles, get_destinations_dict

    lang = "en" if lang == "en" else "fr"
    seen: set[str] = set()
    chunks: list[dict] = []

    def add(chunk: dict) -> None:
        cid = chunk.get("id") or chunk.get("url", "")
        if cid in seen:
            return
        seen.add(cid)
        chunks.append(chunk)

    for page in page_inventory(lang):
        add({
            "id": page["id"],
            "title": page["title"],
            "url": page["url"],
            "group": page["group"],
            "text": _strip_html(page.get("summary") or page.get("title", ""), 400),
        })

    for slug, d in get_destinations_dict(lang).items():
        tips = []
        for tip in (d.get("tips") or [])[:6]:
            if isinstance(tip, dict):
                tips.append(tip.get("text") or tip.get("title") or "")
            else:
                tips.append(str(tip))
        overview = _strip_html(d.get("overview", ""), 500)
        add({
            "id": f"dest-rich:{slug}",
            "title": d.get("name", slug),
            "url": _abs(lang_url("destination_page", lang, slug=slug)),
            "group": "Destinations",
            "text": " ".join(filter(None, [d.get("tagline", ""), overview, " ".join(tips)])),
        })

    for article in get_articles(lang):
        add({
            "id": f"article-rich:{article['slug']}",
            "title": article.get("title", article["slug"]),
            "url": _abs(lang_url("article", lang, slug=article["slug"])),
            "group": "Articles",
            "text": " ".join(filter(None, [
                article.get("excerpt", ""),
                _strip_html(article.get("content", ""), 900),
            ])),
        })

    for aff in _affiliate_chunks(lang, track_url_fn):
        add(aff)

    try:
        from admin import map_service
        for mchunk in map_service.build_chat_map_chunks(lang, track_url_fn):
            add(mchunk)
    except Exception:
        pass

    try:
        from data.travel_guides import build_mai_knowledge_chunks

        def _page_url(endpoint: str, page_lang: str) -> str:
            return _abs(lang_url(endpoint, page_lang))

        for chunk in build_mai_knowledge_chunks(lang, _page_url):
            add(chunk)
    except Exception:
        pass

    for chunk in _extended_knowledge_chunks(lang, track_url_fn):
        add(chunk)

    return chunks


def _extended_knowledge_chunks(lang: str, track_url_fn) -> list[dict]:
    """Pages statiques, itinéraires détaillés, guides expérience, outils budget/eSIM."""
    from data.itineraries import ITINERARIES
    from locales.ui import t as ui_t

    lang = "en" if lang == "en" else "fr"
    chunks: list[dict] = []

    static_pages = (
        ("about", "meta.about.title", "meta.about.desc", "À propos"),
        ("contact", "contact.title", "contact.lead", "Contact"),
        ("privacy", "meta.privacy.title", "meta.privacy.desc", "Confidentialité"),
        ("legal_notices", "meta.legal.title", "meta.legal.desc", "Mentions légales"),
        ("blog_index", "blog.title", "blog.sub", "Blog"),
        ("prepare_trip", "nav.prepare", "prepare.sub", "Préparer son voyage"),
    )
    for endpoint, title_key, lead_key, group in static_pages:
        title = ui_t(title_key, lang)
        lead = ui_t(lead_key, lang)
        chunks.append({
            "id": f"page:{endpoint}",
            "title": title,
            "url": _abs(lang_url(endpoint, lang)),
            "group": group,
            "text": f"{title}. {lead}"[:900],
        })

    for slug, itin in ITINERARIES.items():
        block = (itin.get("i18n") or {}).get(lang) or itin
        highlights = block.get("highlights") or []
        if isinstance(highlights, list):
            highlights_txt = " · ".join(str(h) for h in highlights[:8])
        else:
            highlights_txt = str(highlights)
        days = block.get("days") or []
        day_cities = []
        for day in days[:10]:
            if isinstance(day, dict):
                day_cities.append(day.get("title") or day.get("city") or "")
        overview = _strip_html(block.get("overview", ""), 500)
        chunks.append({
            "id": f"itin-rich:{slug}",
            "title": block.get("title") or slug,
            "url": _abs(lang_url("itinerary", lang, slug=slug)),
            "group": "Itinéraires",
            "text": " ".join(filter(None, [
                block.get("summary", ""),
                block.get("meta_description", ""),
                overview,
                highlights_txt,
                block.get("budget_hint", ""),
                " → ".join(c for c in day_cities if c),
            ]))[:900],
        })

    try:
        from data.experience_articles import EXPERIENCE_ARTICLES
        for art in EXPERIENCE_ARTICLES:
            block = (art.get("i18n") or {}).get(lang) or art
            chunks.append({
                "id": f"experience:{art.get('slug', '')}",
                "title": block.get("title") or art.get("title", ""),
                "url": _abs(lang_url("article", lang, slug=art["slug"])),
                "group": "Guides expérience",
                "text": " ".join(filter(None, [
                    block.get("excerpt", ""),
                    _strip_html(block.get("content", ""), 700),
                ]))[:900],
            })
    except Exception:
        pass

    try:
        from data.travel_tools import build_budget, build_comparators
        budget = build_budget(lang)
        chunks.append({
            "id": "tool-rich:budget",
            "title": ui_t("tools.budget", lang),
            "url": _abs(lang_url("budget_tool", lang)),
            "group": "Outils",
            "text": ui_t("budget.lead", lang) + " " + _strip_html(
                " ".join(
                    f"{s.get('title', '')}: {' '.join(str(i) for i in (s.get('items') or [])[:4])}"
                    for s in (budget.get("sections") or [])[:6]
                    if isinstance(s, dict)
                ),
                600,
            ),
        })
        compare = build_comparators(lang)
        esim_txt = " ".join(
            f"{c.get('name', '')}: {c.get('best', '')} {c.get('price', '')}"
            for c in (compare.get("esim") or [])[:4]
            if isinstance(c, dict)
        )
        ins_txt = " ".join(str(p) for p in (compare.get("insurance_points") or [])[:4])
        chunks.append({
            "id": "tool-rich:essentials",
            "title": ui_t("compare.title", lang),
            "url": _abs(lang_url("essentials_tool", lang)),
            "group": "Outils",
            "text": (ui_t("compare.lead", lang) + " " + esim_txt + " " + ins_txt)[:900],
        })
    except Exception:
        pass

    return chunks


def get_chunks(lang: str, track_url_fn) -> list[dict]:
    lang = "en" if lang == "en" else "fr"
    now = time.monotonic()
    cached = _CHUNK_CACHE.get(lang)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    chunks = build_knowledge_chunks(lang, track_url_fn)
    _CHUNK_CACHE[lang] = (now, chunks)
    return chunks


def invalidate_cache() -> None:
    _CHUNK_CACHE.clear()
    _PLACE_CORRECTIONS.clear()


def _place_corrections(lang: str) -> list[tuple[re.Pattern[str], str]]:
    """Motifs erronés → orthographe canonique des lieux (accents vietnamiens)."""
    if lang in _PLACE_CORRECTIONS:
        return _PLACE_CORRECTIONS[lang]

    pairs: list[tuple[str, str]] = []
    from admin.store import get_destinations_dict

    for slug, d in get_destinations_dict(lang).items():
        canon = (d.get("name") or "").strip()
        if not canon:
            continue
        slug_sp = slug.replace("-", " ")
        for wrong in (slug_sp, _fold(canon)):
            if wrong and _fold(wrong) != _fold(canon):
                pairs.append((wrong, canon))

    for city in _KNOWN_CITIES:
        canon = city["name"]
        for alias in city["aliases"]:
            pairs.append((alias, canon))

    static_ascii = (
        ("da lat", "Đà Lạt"), ("dalat", "Đà Lạt"),
        ("da nang", "Đà Nẵng"), ("danang", "Đà Nẵng"),
        ("hoi an", "Hội An"), ("hoian", "Hội An"),
        ("phu quoc", "Phú Quốc"), ("phuquoc", "Phú Quốc"),
        ("ninh binh", "Ninh Bình"),
        ("can tho", "Cần Thơ"),
        ("vung tau", "Vũng Tàu"),
        ("con dao", "Côn Đảo"),
        ("mui ne", "Mũi Né"),
        ("cu chi", "Củ Chi"),
        ("cat ba", "Cát Bà"),
        ("mai chau", "Mai Châu"),
        ("quy nhon", "Quy Nhơn"),
        ("my son", "Mỹ Sơn"),
        ("ha long", "Baie d'Ha Long"),
        ("halong", "Baie d'Ha Long"),
    )
    for wrong, canon in static_ascii:
        pairs.append((wrong, canon))
    if lang == "fr":
        pairs.append(("hue", "Huế"))

    seen: set[tuple[str, str]] = set()
    compiled: list[tuple[re.Pattern[str], str]] = []
    for wrong, canon in sorted(pairs, key=lambda x: -len(x[0])):
        key = (wrong.lower(), canon)
        if key in seen:
            continue
        seen.add(key)
        try:
            pat = re.compile(rf"(?<![\wÀ-ỹ]){re.escape(wrong)}(?![\wÀ-ỹ])", re.IGNORECASE)
            compiled.append((pat, canon))
        except re.error:
            pass

    _PLACE_CORRECTIONS[lang] = compiled
    return compiled


def _fix_place_names(message: str, lang: str) -> str:
    msg = message or ""
    for pat, canon in _place_corrections(lang):
        msg = pat.sub(canon, msg)
    return msg


def _orthography_block(lang: str) -> str:
    from admin.store import get_destinations_dict

    names: list[str] = []
    seen: set[str] = set()
    for d in get_destinations_dict(lang).values():
        n = (d.get("name") or "").strip()
        if n and n not in seen:
            seen.add(n)
            names.append(n)
    for city in _KNOWN_CITIES:
        n = city["name"]
        if n not in seen:
            seen.add(n)
            names.append(n)
    sample = ", ".join(names[:28])
    if lang == "en":
        return (
            "PLACE NAME SPELLING (mandatory — copy EXACTLY from this list or CONTEXT):\n"
            f"{sample}\n"
            "Never strip Vietnamese diacritics (write Đà Lạt, Huế, Hội An, Phú Quốc, not Da Lat/Hue/Hoi An). "
            "Use the destination name from CONTEXT for the reply language."
        )
    return (
        "ORTHOGRAPHE DES LIEUX (obligatoire — copie EXACTEMENT depuis cette liste ou le CONTEXTE) :\n"
        f"{sample}\n"
        "Ne supprime JAMAIS les accents vietnamiens (Đà Lạt, Huế, Hội An, Phú Quốc… — pas « Da Lat », « Hue », « Hoi An »). "
        "Utilise le nom exact de la page destination du CONTEXTE."
    )


def _site_map_block(lang: str) -> str:
    """Vue d'ensemble du site public — aide Mai à orienter vers la bonne page."""
    from admin.social_ai import page_inventory

    by_group: dict[str, list[str]] = {}
    for page in page_inventory(lang):
        by_group.setdefault(page["group"], []).append(page["title"])
    header = (
        "PUBLIC SITE MAP (all sections Mai can link to — pick from CONTEXT URLs):"
        if lang == "en"
        else "PLAN DU SITE PUBLIC (toutes les rubriques — choisir les URL du CONTEXTE) :"
    )
    lines = [header]
    for group, titles in sorted(by_group.items()):
        preview = ", ".join(titles[:6])
        if len(titles) > 6:
            preview += f" (+{len(titles) - 6})"
        lines.append(f"- {group}: {preview}")
    lines.append(
        "Also: practical guides (safety, customs, phrases, visa, weather, budget, apps, eSIM), "
        "experience guides, blog articles, ready-made itineraries, destination pages with maps."
        if lang == "en"
        else "Aussi : guides pratiques (sécurité, coutumes, phrases, visa, météo, budget, apps, eSIM), "
        "guides expérience, articles blog, itinéraires clés en main, pages destinations avec cartes."
    )
    return "\n".join(lines)


def retrieve(query: str, lang: str, track_url_fn, top_n: int = CHAT_RETRIEVE_TOP_N, visitor_profile: dict | None = None) -> list[dict]:
    q_tokens = _tokenize(query, lang)
    profile_tags = set()
    if visitor_profile:
        try:
            from data.visitor_profile import retrieve_boost_tags
            profile_tags = retrieve_boost_tags(visitor_profile)
            q_tokens = q_tokens | _tokenize(" ".join(profile_tags), lang)
        except Exception:
            pass
    hay = query.lower()
    if any(w in hay for w in ("hotel", "hôtel", "dormir", "heberg", "héberg", "stay", "carte", "map")):
        top_n = max(top_n, 16)
    if any(w in hay for w in (
        "visa", "e-visa", "evisa", "passeport", "formalit",
        "meteo", "météo", "saison", "pluie", "climat", "weather", "when", "partir", "visit",
        "secur", "sécur", "arnaque", "scam", "sant", "vaccin", "assurance", "urgence",
        "coutume", "etiquette", "respect", "temple", "politesse",
        "phrase", "vietnamien", "vietnamese", "xin chao", "cam on",
        "budget", "prepare", "preparer", "organiser", "itinera", "circuit", "blog",
    )):
        top_n = max(top_n, 18)

    mentioned_cities = _mentioned_cities(query)
    mentioned_slugs = {_detect_destination_slug(c["name"], lang) for c in mentioned_cities}
    mentioned_slugs.discard(None)

    chunks = get_chunks(lang, track_url_fn)
    if not q_tokens:
        return chunks[:top_n]

    scored: list[tuple[int, dict]] = []
    for chunk in chunks:
        hay = f"{chunk.get('title', '')} {chunk.get('text', '')} {chunk.get('group', '')}"
        c_tokens = _tokenize(hay, lang)
        score = len(q_tokens & c_tokens)
        if chunk.get("affiliate") and any(t in hay.lower() for t in ("esim", "sim", "assurance", "insurance", "hotel", "hôtel")):
            score += 1
        if chunk.get("group") == "Carte" and any(t in q_tokens for t in _tokenize("carte map plan localisation où dormir activités", lang)):
            score += 2
        if chunk.get("group") == "Carte affiliée":
            score += 1
        if chunk.get("group") in (
            "Sécurité Vietnam", "Coutumes Vietnam", "Phrases vietnamiennes",
            "Visa Vietnam", "Météo Vietnam", "Guides pratiques",
        ):
            score += 1
        if chunk.get("id", "").startswith("guide-") and any(
            t in q_tokens for t in _tokenize("visa meteo securite coutume phrase arnaque vaccin", lang)
        ):
            score += 2
        if mentioned_slugs:
            cid = chunk.get("id", "")
            for slug in mentioned_slugs:
                if slug in cid or slug in (chunk.get("url") or ""):
                    score += 4
                if chunk.get("group") == "Destinations" and slug in _fold(chunk.get("title", "")):
                    score += 3
        if chunk.get("group") == "Itinéraires" and any(
            w in hay for w in ("itinera", "circuit", "jour", "days", "week", "semaine", "trip")
        ):
            score += 3
        if chunk.get("id", "").startswith("itin-rich:"):
            score += 1
        if chunk.get("id", "").startswith("tool-rich:budget") and any(
            w in hay for w in ("budget", "cout", "cost", "prix", "euro", "dong")
        ):
            score += 3
        if chunk.get("id") in ("tool:prepare_trip", "page:prepare_trip") and any(
            w in hay for w in ("partir", "prepare", "preparer", "organiser", "faut faire", "checklist")
        ):
            score += 4
        if chunk.get("group") in ("Articles de blog", "Guides expérience") and any(
            w in hay for w in ("blog", "article", "guide", "lire")
        ):
            score += 2
        if profile_tags and chunk.get("group") in (
            "Sécurité Vietnam", "Coutumes Vietnam", "Phrases vietnamiennes",
            "Visa Vietnam", "Météo Vietnam",
        ):
            hay_l = hay.lower()
            if any(tag in hay_l or tag.replace("-", " ") in hay_l for tag in profile_tags if len(tag) > 2):
                score += 2
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    if scored:
        return [c for _, c in scored[:top_n]]

    # Repli : pages clés + quelques destinations
    priority = ("home", "prepare", "tool:prepare_trip", "dest:hanoi", "dest:hoi-an", "dest:ho-chi-minh-city")
    fallback = []
    for pid in priority:
        for c in chunks:
            if c.get("id", "").startswith(pid) or pid in c.get("id", ""):
                fallback.append(c)
                break
    return (fallback or chunks)[:top_n]


def _check_rate(ip: str) -> str | None:
    if not ip:
        return None
    now = time.time()
    with _RATE_LOCK:
        hits = [t for t in _RATE.get(ip, []) if now - t < _RATE_WINDOW]
        burst = [t for t in hits if now - t < _RATE_BURST_WINDOW]
        if len(burst) >= _RATE_BURST:
            return "Trop de messages d'affilée — patientez une minute. ⏳"
        if len(hits) >= _RATE_MAX:
            return "Limite horaire atteinte — revenez un peu plus tard. 🙏"
        hits.append(now)
        _RATE[ip] = hits
    return None


def _normalize_chat_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        return config.SITE_URL.rstrip("/") + url
    return url


def _url_is_allowed(url: str, allowed_urls: set[str]) -> bool:
    url = _normalize_chat_url(url)
    if not url:
        return False
    if url in allowed_urls:
        return True
    base = url.split("#", 1)[0].rstrip("/")
    for allowed in allowed_urls:
        if not allowed:
            continue
        norm = _normalize_chat_url(allowed).rstrip("/")
        if url == norm or base == norm.split("#", 1)[0].rstrip("/"):
            return True
    return False


def _resolve_url(url: str, allowed_urls: set[str]) -> str:
    """Retourne l'URL canonique du contexte si elle correspond."""
    url = _normalize_chat_url(url)
    if url in allowed_urls:
        return url
    base = url.split("#", 1)[0].rstrip("/")
    fragment = url.split("#", 1)[1] if "#" in url else ""
    for allowed in allowed_urls:
        norm = _normalize_chat_url(allowed)
        if norm == url:
            return norm
        allowed_base = norm.split("#", 1)[0].rstrip("/")
        if base == allowed_base:
            return norm if not fragment else f"{allowed_base}#{fragment}"
    return url


def _message_incomplete(message: str) -> bool:
    msg = (message or "").strip()
    if not msg:
        return True
    if msg.endswith((":", "—", "-", "•", "…")):
        return True
    if re.search(r":\s*$", msg):
        return True
    if re.search(r"\n\s*[-•]\s*$", msg):
        return True
    return False


def _repair_message(message: str, lang: str, *, has_links: bool, city: str = "") -> str:
    msg = (message or "").strip()
    if not _message_incomplete(msg):
        return msg
    msg = re.sub(r"[\s:—\-•…]+$", "", msg).strip()
    if lang == "en":
        suffix = "."
    else:
        suffix = "."
    return msg + suffix


def _link_intent(text: str) -> dict[str, bool]:
    hay = _fold(text)
    return {
        "booking": any(w in hay for w in ("hotel", "dormir", "reserv", "book", "heberg", "loger", "stay", "lodging")),
        "activity": any(w in hay for w in ("activit", "tour", "excursion", "visite", "things to do")),
        "esim": any(w in hay for w in ("esim", "sim", "forfait", "data mobile", "internet mobile")),
        "insurance": any(w in hay for w in ("assurance", "insurance", "sante", "santé", "health", "medic")),
        "visa": any(w in hay for w in ("visa", "evisa", "e-visa", "passeport", "passport", "formalit")),
        "guide_page": any(w in hay for w in (
            "guide", "page", "lien", "link", "lire", "read", "outil", "article", "blog", "itinera",
        )),
        "prepare": any(w in hay for w in (
            "partir", "prepare", "preparer", "préparer", "organiser", "faut faire", "checklist",
            "before you go", "what do i need",
        )),
        "map": _wants_map(text),
    }


def _curate_links(
    user_question: str,
    site_links: list[dict],
    affiliate_links: list[dict],
    lang: str,
) -> tuple[list[dict], list[dict]]:
    """Garde 0–1 lien site et 0–1 affilié, seulement si la question le justifie."""
    intent = _link_intent(user_question)
    wants_site = intent["visa"] or intent["prepare"] or intent["guide_page"] or intent["map"]
    wants_aff = intent["booking"] or intent["activity"] or intent["esim"] or intent["insurance"]

    if not wants_site and not wants_aff:
        return [], []

    out_site: list[dict] = []
    out_aff: list[dict] = []

    if wants_site and site_links:
        if intent["visa"]:
            visa_first = next(
                (l for l in site_links if "visa" in l.get("title", "").lower() or "visa" in l.get("url", "")),
                site_links[0],
            )
            out_site = [visa_first]
        elif intent["prepare"]:
            prep = next(
                (l for l in site_links if "prepare" in l.get("url", "").lower() or "plan" in l.get("url", "")),
                site_links[0],
            )
            out_site = [prep]
        else:
            out_site = [site_links[0]]

    if wants_aff and affiliate_links:
        if intent["esim"]:
            esim = next(
                (l for l in affiliate_links if "esim" in l.get("label", "").lower() or "airalo" in l.get("url", "").lower() or "holafly" in l.get("url", "").lower()),
                affiliate_links[0],
            )
            out_aff = [esim]
        elif intent["insurance"]:
            ins = next(
                (l for l in affiliate_links if "assur" in l.get("label", "").lower() or "insur" in l.get("label", "").lower()),
                affiliate_links[0],
            )
            out_aff = [ins]
        else:
            out_aff = [affiliate_links[0]]

    return out_site[:1], out_aff[:1]


def _fold(text: str) -> str:
    """Minuscules sans accents — pour comparer noms de villes et messages."""
    # « đ » (D barré vietnamien) n'est pas décomposé par NFKD : Đà Lạt → da lat.
    text = (text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _contains_word(hay: str, needle: str) -> bool:
    """Présence en mot entier : « hue » ne matche pas « thue » ni « hueco »."""
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay))


# Villes vietnamiennes que Mai doit reconnaître — y compris SANS page destination.
# Les descriptifs ancrent le modèle sur la BONNE ville (Đà Lạt ≠ Huế…) et lui
# permettent de répondre honnêtement quand le site n'a pas encore de page dédiée.
_KNOWN_CITIES: tuple[dict, ...] = (
    {"name": "Hanoï", "aliases": ("hanoi",),
     "fr": "capitale du Vietnam, au Nord — vieux quartier des 36 corporations, lacs, street food",
     "en": "Vietnam's capital, in the North — Old Quarter, lakes, street food"},
    {"name": "Baie d'Ha Long", "aliases": ("ha long", "halong"),
     "fr": "baie classée UNESCO au Nord — croisières entre pitons karstiques",
     "en": "UNESCO bay in the North — cruises among karst peaks"},
    {"name": "Ninh Bình", "aliases": ("ninh binh", "tam coc", "trang an"),
     "fr": "« baie d'Halong terrestre » au Nord — Tam Cốc, Tràng An, barques entre rizières",
     "en": "the “inland Ha Long Bay”, North — Tam Cốc, Tràng An boat rides among rice fields"},
    {"name": "Sapa", "aliases": ("sapa", "sa pa"),
     "fr": "montagnes du Nord-Ouest — rizières en terrasses, treks, minorités ethniques",
     "en": "northwestern mountains — terraced rice fields, treks, ethnic minorities"},
    {"name": "Ha Giang", "aliases": ("ha giang",),
     "fr": "extrême Nord — boucle à moto spectaculaire, cols et villages",
     "en": "far North — spectacular motorbike loop, passes and villages"},
    {"name": "Mai Châu", "aliases": ("mai chau",),
     "fr": "vallée paisible au Nord — rizières, maisons sur pilotis",
     "en": "peaceful northern valley — rice paddies, stilt houses"},
    {"name": "Cát Bà", "aliases": ("cat ba",),
     "fr": "île au sud de la baie d'Halong — parc national, baie de Lan Hạ",
     "en": "island south of Ha Long Bay — national park, Lan Hạ Bay"},
    {"name": "Huế", "aliases": ("hue",),
     "fr": "ancienne capitale IMPÉRIALE, sur la côte Centre — citadelle, tombeaux royaux, rivière des Parfums (à ne PAS confondre avec Đà Lạt)",
     "en": "the former IMPERIAL capital on the central coast — citadel, royal tombs, Perfume River (NOT to be confused with Đà Lạt)"},
    {"name": "Hội An", "aliases": ("hoi an", "hoian"),
     "fr": "vieille ville UNESCO du Centre — lanternes, tailleurs, plages proches",
     "en": "UNESCO old town in the Center — lanterns, tailors, nearby beaches"},
    {"name": "Đà Nẵng", "aliases": ("da nang", "danang"),
     "fr": "grande ville balnéaire du Centre — plages, pont d'Or, montagnes de Marbre",
     "en": "major central beach city — beaches, Golden Bridge, Marble Mountains"},
    {"name": "Nha Trang", "aliases": ("nha trang",),
     "fr": "station balnéaire du Centre-Sud — plages, îles, plongée",
     "en": "south-central seaside resort — beaches, islands, diving"},
    {"name": "Đà Lạt", "aliases": ("da lat", "dalat"),
     "fr": "ville d'ALTITUDE des hauts plateaux du Centre (1 500 m) — air frais, pins, cascades, café (à ne PAS confondre avec Huế)",
     "en": "HIGHLAND city in the Central Highlands (1,500 m) — cool air, pine forests, waterfalls, coffee (NOT to be confused with Huế)"},
    {"name": "Quy Nhơn", "aliases": ("quy nhon", "qui nhon"),
     "fr": "littoral tranquille du Centre-Sud — plages, tours cham",
     "en": "quiet south-central coast — beaches, Cham towers"},
    {"name": "Phong Nha", "aliases": ("phong nha",),
     "fr": "parc national du Centre (Quảng Bình) — grottes géantes (Sơn Đoòng, Paradise Cave)",
     "en": "central national park (Quảng Bình) — giant caves (Sơn Đoòng, Paradise Cave)"},
    {"name": "Mỹ Sơn", "aliases": ("my son", "myson"),
     "fr": "sanctuaire cham UNESCO près de Hội An",
     "en": "UNESCO Cham sanctuary near Hội An"},
    {"name": "Ho Chi Minh-Ville", "aliases": ("saigon", "ho chi minh", "hcmv", "hcmc"),
     "fr": "métropole du Sud (Saigon) — street food, histoire, vie nocturne",
     "en": "the southern metropolis (Saigon) — street food, history, nightlife"},
    {"name": "Delta du Mékong", "aliases": ("mekong", "my tho", "ben tre"),
     "fr": "Sud — canaux, marchés flottants, vergers",
     "en": "South — canals, floating markets, orchards"},
    {"name": "Cần Thơ", "aliases": ("can tho",),
     "fr": "cœur du delta du Mékong — marché flottant de Cái Răng",
     "en": "heart of the Mekong Delta — Cái Răng floating market"},
    {"name": "Vũng Tàu", "aliases": ("vung tau",),
     "fr": "station balnéaire proche de Saigon",
     "en": "beach town near Saigon"},
    {"name": "Phú Quốc", "aliases": ("phu quoc", "phuquoc"),
     "fr": "île du golfe de Thaïlande — plages, snorkeling, couchers de soleil",
     "en": "island in the Gulf of Thailand — beaches, snorkeling, sunsets"},
    {"name": "Côn Đảo", "aliases": ("con dao",),
     "fr": "archipel sauvage du Sud — plages préservées, histoire",
     "en": "wild southern archipelago — pristine beaches, history"},
    {"name": "Mũi Né", "aliases": ("mui ne", "phan thiet"),
     "fr": "Sud-Est — dunes de sable, kitesurf",
     "en": "Southeast — sand dunes, kitesurfing"},
    {"name": "Củ Chi", "aliases": ("cu chi",),
     "fr": "tunnels de guerre près de Saigon",
     "en": "war tunnels near Saigon"},
)


def _mentioned_cities(text: str) -> list[dict]:
    hay = _fold(text)
    return [
        city for city in _KNOWN_CITIES
        if any(_contains_word(hay, a) for a in city["aliases"])
    ]


def _cities_block(text: str, lang: str) -> str:
    """Bloc « VILLES MENTIONNÉES » injecté dans le prompt : ancre le modèle sur
    les bonnes villes (jamais de confusion Đà Lạt/Huế) et lui dit honnêtement
    si le site a, ou non, une page dédiée."""
    cities = _mentioned_cities(text)[:4]
    if not cities:
        return ""
    lines = []
    for c in cities:
        desc = c.get(lang) or c["fr"]
        covered = _detect_destination_slug(c["name"], lang)
        if lang == "en":
            note = (
                " [dedicated destination page on the site]" if covered
                else " [no dedicated page on the site yet: give honest general advice, do not invent links]"
            )
        else:
            note = (
                " [page destination dédiée sur le site]" if covered
                else " [pas encore de page dédiée sur le site : donne des conseils généraux honnêtes, sans inventer de lien]"
            )
        lines.append(f"- {c['name']} : {desc}{note}")
    header = (
        "CITIES MENTIONED (factual anchors — NEVER mix these cities up):"
        if lang == "en"
        else "VILLES MENTIONNÉES (repères factuels — ne confonds JAMAIS ces villes entre elles) :"
    )
    return header + "\n" + "\n".join(lines)


def _detect_destination_slug(text: str, lang: str) -> str | None:
    from admin.store import get_destinations_dict

    hay = _fold(text)
    for slug, dest in get_destinations_dict(lang).items():
        name_norm = _fold(dest.get("name", ""))
        if name_norm and _contains_word(hay, name_norm):
            return slug
        if _contains_word(hay, slug.replace("-", " ")):
            return slug
    aliases = {
        "hanoi": ("hanoi", "hanoï"),
        "ho-chi-minh-city": ("saigon", "ho chi minh"),
        "hoi-an": ("hoi an", "hoian"),
        "da-nang": ("da nang", "danang"),
        "phu-quoc": ("phu quoc", "phuquoc"),
        "delta-du-mekong": ("mekong", "delta du mekong"),
        "halong": ("ha long", "halong"),
        "sapa": ("sapa",),
        "hue": ("hue",),
    }
    for slug, keys in aliases.items():
        if any(_contains_word(hay, k) for k in keys):
            return slug
    return None


# Mots (sans accents, minuscules) qui rendent la carte pertinente : se loger,
# manger, se repérer, organiser sur place. Sans eux, pas de carte dans la bulle.
_MAP_INTENT_WORDS = (
    "carte", "map", "itinerair", "dormir", "loger", "heberg", "hotel", "hostel",
    "auberge", "guesthouse", "quartier", "localis", "emplacement", "se reperer",
    "ou dormir", "ou loger", "ou manger", "ou sortir", "ou aller", "ou se trouve",
    "ou est", "que faire", "quoi faire", "a faire", "activit", "visiter", "a voir",
    "restaurant", "manger",
    "stay", "sleep", "neighborhood", "neighbourhood", "district", "where",
    "located", "location", "what to do", "things to do", "to visit", "itinerary",
    "eat",
)


def _wants_map(message: str) -> bool:
    """Carte interactive UNIQUEMENT quand la question s'y prête — pas à chaque message."""
    hay = _fold(message)
    return any(w in hay for w in _MAP_INTENT_WORDS)


def _slug_from_map_url(url: str) -> str | None:
    """Extrait le slug destination depuis une URL page carte (#dest-map)."""
    if not url:
        return None
    from urllib.parse import urlparse

    path = urlparse(url).path.strip("/")
    if not path:
        return None
    parts = [p for p in path.split("/") if p]
    if parts and parts[0] == "en":
        parts = parts[1:]
    if not parts:
        return None
    slug = parts[-1]
    try:
        from admin.store import get_destinations_dict
        if slug in get_destinations_dict():
            return slug
    except Exception:
        pass
    return None


def _build_map_cards_for_response(
    site_links: list[dict],
    affiliate_links: list[dict],
    slug: str | None,
    lang: str,
    track_url_fn,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Construit cartes carte pour Mai et retire les liens redondants."""
    from admin.map_service import build_chat_map_card

    slugs: set[str] = set()
    if slug:
        slugs.add(slug)
    for link in site_links:
        s = _slug_from_map_url(link.get("url", ""))
        if s:
            slugs.add(s)

    aff_urls = {l.get("url") for l in affiliate_links if l.get("url")}
    cards: list[dict] = []
    for s in sorted(slugs):
        card = build_chat_map_card(s, lang, track_url_fn, highlight_urls=aff_urls)
        if card:
            cards.append(card)

    card_slugs = {c["slug"] for c in cards}
    filtered_site = [
        l for l in site_links
        if not (_slug_from_map_url(l.get("url", "")) in card_slugs)
    ]

    card_aff_urls: set[str] = set()
    for card in cards:
        for pt in card.get("points") or []:
            u = pt.get("affiliate_url")
            if u:
                card_aff_urls.add(u)
    filtered_aff = [l for l in affiliate_links if l.get("url") not in card_aff_urls]

    return cards, filtered_site, filtered_aff


def _auto_enrich_links(
    message: str,
    chunks: list[dict],
    *,
    lang: str,
    site_links: list[dict],
    affiliate_links: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Complète au plus 1 lien site + 1 affilié, uniquement si la question le demande."""
    intent = _link_intent(message)
    if not any(intent[k] for k in ("booking", "activity", "esim", "insurance", "visa", "prepare", "guide_page", "map")):
        return [], []

    slug = _detect_destination_slug(message, lang)
    existing_site = {l["url"] for l in site_links}
    existing_aff = {l["url"] for l in affiliate_links}

    def add_site(chunk: dict) -> None:
        if len(site_links) >= 1:
            return
        url = chunk.get("url", "")
        if not url or url in existing_site:
            return
        site_links.append({"title": (chunk.get("title") or url)[:120], "url": url})
        existing_site.add(url)

    def add_aff(chunk: dict, label: str | None = None) -> None:
        if len(affiliate_links) >= 1:
            return
        url = chunk.get("url", "")
        if not url or url in existing_aff:
            return
        affiliate_links.append({
            "label": (label or chunk.get("title") or url)[:100],
            "url": url,
            "teaser": "",
        })
        existing_aff.add(url)

    for chunk in chunks:
        if len(site_links) >= 1 and len(affiliate_links) >= 1:
            break
        cid = chunk.get("id", "")
        if intent["visa"] and cid.startswith("guide-visa"):
            add_site(chunk)
        elif intent["prepare"] and cid in ("tool:prepare_trip", "page:prepare_trip"):
            add_site(chunk)
        elif intent["map"] and slug and cid == f"dest-rich:{slug}":
            add_site(chunk)
        elif intent["booking"] and slug and cid == f"aff:hotel:{slug}":
            add_aff(chunk)
        elif intent["activity"] and slug and cid == f"aff:activity:{slug}":
            add_aff(chunk)
        elif intent["esim"] and cid in ("aff:esim_airalo", "aff:esim_holafly"):
            add_aff(chunk)
        elif intent["insurance"] and cid == "aff:insurance":
            add_aff(chunk)

    return site_links[:1], affiliate_links[:1]


def _emph_count(message: str) -> int:
    return len(re.findall(r"\*\*[^*]+\*\*", message or ""))


def _wrap_highlight_once(message: str, pattern: str) -> str:
    """Entoure la première occurrence d'un motif avec ** si pas déjà mis en valeur."""

    def repl(m: re.Match) -> str:
        start, end = m.start(), m.end()
        before = message[max(0, start - 2): start]
        after = message[end: end + 2]
        if before.endswith("**") or after.startswith("**"):
            return m.group(0)
        return f"**{m.group(0)}**"

    return re.sub(pattern, repl, message, count=1, flags=re.IGNORECASE)


def _highlight_phrases_for_intent(message: str, user_question: str, lang: str) -> str:
    """Applique des surlignages contextuels si le modèle oublie les **."""
    if _emph_count(message) >= 4:
        return message

    hay = _fold(f"{user_question} {message}")
    phrases: list[str] = []

    prepare_q = any(
        w in hay for w in (
            "partir", "preparer", "prepare", "organiser", "checklist", "before you go",
            "what do i need", "what to do", "faire pour", "faut faire", "quoi faire avant",
            "comment partir", "premiers pas", "getting ready",
        )
    )
    visa_q = any(w in hay for w in ("visa", "evisa", "e-visa", "passeport", "passport", "formalit"))
    hotel_q = any(w in hay for w in ("hotel", "dormir", "heberg", "loger", "stay", "lodging"))
    activity_q = any(w in hay for w in ("activit", "faire", "visit", "excursion", "things to do"))
    weather_q = any(w in hay for w in ("meteo", "saison", "pluie", "climat", "when to go", "quand partir"))
    safety_q = any(w in hay for w in ("secur", "arnaque", "scam", "sant", "urgence"))
    esim_q = any(w in hay for w in ("esim", "sim", "forfait", "data mobile", "internet"))

    if lang == "en":
        if prepare_q or visa_q:
            phrases.extend([
                r"obtain(?:ing)? a visa",
                r"apply(?:ing)? (?:for a visa )?online",
                r"e-?visa",
                r"visa(?:-free| exemption)",
                r"travel insurance",
                r"(?:get|buy) travel insurance",
                r"valid passport",
                r"entry requirements",
                r"health and safety",
            ])
        if hotel_q:
            phrases.extend([r"book(?:ing)? (?:a )?hotel", r"where to stay", r"Old Quarter"])
        if activity_q:
            phrases.extend([r"things to do", r"must-?see", r"day trip"])
        if weather_q:
            phrases.extend([r"dry season", r"best time to go", r"November to April"])
        if safety_q:
            phrases.extend([r"travel safety", r"common scams", r"emergency"])
        if esim_q:
            phrases.extend([r"eSIM", r"mobile data"])
    else:
        if prepare_q or visa_q:
            phrases.extend([
                r"obtenir (?:un |le )?visa",
                r"demander (?:un |le )?visa",
                r"visa en ligne",
                r"e-?visa",
                r"exemption(?:s)? de visa",
                r"souscrire (?:à )?(?:une )?assurance(?: voyage)?",
                r"assurance voyage",
                r"passeport(?: valide)?",
                r"formalités(?: d['']entrée)?",
                r"conditions d['']entrée",
                r"santé et sécurité",
            ])
        if hotel_q:
            phrases.extend([r"où dormir", r"réserver (?:un )?hôtel", r"quartier des 36"])
        if activity_q:
            phrases.extend([r"que faire", r"quoi faire", r"incontournables"])
        if weather_q:
            phrases.extend([r"saison sèche", r"meilleure période", r"novembre à avril", r"mousson"])
        if safety_q:
            phrases.extend([r"sécurité", r"arnaques", r"numéros d['']urgence"])
        if esim_q:
            phrases.extend([r"eSIM", r"forfait mobile", r"carte SIM"])

    msg = message
    target = 5 if _emph_count(msg) < 2 else 3
    for pat in phrases:
        if _emph_count(msg) >= target:
            break
        if not re.search(pat, msg, flags=re.IGNORECASE):
            continue
        new_msg = _wrap_highlight_once(msg, pat)
        if new_msg != msg:
            msg = new_msg

    return msg


def _clean_message_body(message: str, lang: str) -> str:
    """Retire les URL brutes du corps — elles sont dans les cartes de liens."""
    msg = (message or "").strip()
    if not msg:
        return msg

    msg = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", msg)
    msg = re.sub(r"<\s*(https?://[^>]+)\s*>", r"\1", msg)
    msg = re.sub(r"https?://[^\s\]\)<>«»;,]+", "", msg)
    msg = re.sub(
        r"\b(?:www\.)?[a-z0-9][-a-z0-9]*\.(?:gov(?:t)?\.vn|go\.vn|gov\.vn|evisa\.gov\.vn)[^\s,;]*",
        "",
        msg,
        flags=re.IGNORECASE,
    )
    below = "voir les liens ci-dessous" if lang != "en" else "see links below"
    msg = re.sub(
        r"(?:via|sur|on|at)\s+(?:le\s+)?site\s+officiel\s*(?:<)?\s*",
        f"({below}). ",
        msg,
        flags=re.IGNORECASE,
    )
    msg = re.sub(r"\(\s*\)", "", msg)
    msg = _normalize_message_layout(msg)
    msg = re.sub(r"\s+([.,;:!?])", r"\1", msg)
    msg = re.sub(r";\s*;", ";", msg)
    return msg.strip()


def _normalize_message_layout(msg: str) -> str:
    """Garde les paragraphes et aère les pavés sans retours à la ligne."""
    msg = re.sub(r"\r\n?", "\n", msg or "")
    msg = re.sub(r"\n{3,}", "\n\n", msg)
    blocks: list[str] = []
    for block in msg.split("\n\n"):
        block = re.sub(r"[ \t]+", " ", block).strip()
        if block:
            blocks.append(block)
    msg = "\n\n".join(blocks)
    if "\n\n" in msg or len(msg) < 200:
        return msg
    sentences = re.split(r"(?<=[.!?…»\"])\s+(?=\S)", msg)
    if len(sentences) < 3:
        return msg
    paragraphs: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for sentence in sentences:
        buf.append(sentence)
        buf_len += len(sentence)
        if len(buf) >= 2 and buf_len >= 70:
            paragraphs.append(" ".join(buf))
            buf = []
            buf_len = 0
    if buf:
        paragraphs.append(" ".join(buf))
    return "\n\n".join(paragraphs) if len(paragraphs) > 1 else msg


def _ensure_context_highlights(message: str, user_question: str, lang: str) -> str:
    return _highlight_phrases_for_intent(message, user_question, lang)


def _format_context(chunks: list[dict]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        aff = " [affilié]" if c.get("affiliate") else ""
        lines.append(
            f"{i}. [{c.get('group', '?')}] {c.get('title', '')}{aff}\n"
            f"   URL: {c.get('url', '')}\n"
            f"   {c.get('text', '')[:480]}"
        )
    return "\n".join(lines)


def _system_prompt(lang: str) -> str:
    site_scope_en = (
        "SCOPE: you are the public travel assistant for the entire Inside Vietnam Travel website "
        "(FR + EN). You know ALL public pages: home, prepare-your-trip hub, destinations with interactive maps, "
        "ready-made itineraries (3/7/10/15 days), blog & experience guides, practical tools (visa, weather, "
        "budget calculator, safety, customs, phrases, apps, eSIM & insurance), about & contact. "
        "You do NOT manage /admin (that is Linh, the internal admin copilot) — for site ownership or "
        "partnerships, point to the contact page."
    )
    site_scope_fr = (
        "PÉRIMÈTRE : tu es l'assistante voyage du site public Inside Vietnam Travel (FR + EN). "
        "Tu connais TOUTES les pages publiques : accueil, hub préparer son voyage, destinations avec cartes "
        "interactives, itinéraires clés en main (3/7/10/15 jours), blog & guides expérience, outils pratiques "
        "(visa, météo, calculateur budget, sécurité, coutumes, phrases, apps, eSIM & assurance), à propos & contact. "
        "Tu ne gères PAS /admin (c'est Linh, copilote interne) — pour la rédaction du site ou un partenariat, "
        "oriente vers la page contact."
    )
    if lang == "en":
        return (
            site_scope_en + " "
            "You are Mai 🌸, the friendly AI travel advisor — an independent Vietnam travel guide (not a travel agency). "
            "LANGUAGE: always reply in ENGLISH on /en pages; never mix French in the message body. "
            "KNOWLEDGE: use ONLY facts and URLs from CONTEXT + SITE MAP. If missing, say so honestly — never invent. "
            "GOLDEN RULE: answer the user's QUESTION first, directly and precisely, from the very first sentence. "
            "STYLE (ChatGPT-like): natural conversation, clear and precise — short paragraphs separated by a "
            "blank line, no filler, no link lists in the message. Answer like a smart travel friend, not a brochure. "
            "BREVITY: simple question → 1–2 sentences (~60 words); advice → 3–5 sentences (~120 words max). "
            "LINKS (sparse): in MOST replies set site_links=[] and affiliate_links=[]. Add AT MOST 1 site_link "
            "OR 1 affiliate_link only when the user clearly needs it (visa page, prepare trip, book a hotel, "
            "eSIM, insurance, activity). Never both unless they explicitly asked for two things. "
            "Never add links to casual or follow-up questions. "
            "The site has dedicated guides: travel safety & scams, customs & etiquette, useful Vietnamese phrases, "
            "visa checker (evisa.gov.vn), weather planner by region/destination, useful apps (Grab), eSIM & insurance — "
            "recommend the matching page from CONTEXT when relevant. "
            "CITIES — absolute rule: when a CITIES MENTIONED block is present, your answer is about THOSE exact "
            "cities and matches their factual anchors. NEVER mix up two distinct cities (Đà Lạt, the highland city, "
            "is NOT Huế, the imperial capital; Đà Nẵng is not Đà Lạt). If the site has no page for a requested "
            "city, say so honestly and still give your best general advice. "
            "SPELLING: copy Vietnamese place names EXACTLY as in ORTHOGRAPHY block / CONTEXT (Đà Lạt, Huế, Hội An, "
            "Phú Quốc, Ninh Bình…) — never strip diacritics. "
            "When a VISITOR PROFILE block is present, prioritize advice and links aligned with their "
            "travel style, cities, duration and pages already viewed — without mentioning tracking. "
            "PERSONALITY: warm, enthusiastic and expert, with a touch of light, friendly humor when the topic "
            "lends itself to it — a witty aside, a cultural wink (egg coffee, the scooter ballet, crossing the "
            "street like a local…), never at the expense of clarity and never on serious topics (visa, health, "
            "safety). Congratulate sincerely when deserved: a great city or season pick, booked flights, a smart "
            "itinerary (“Great choice!”, “Well done — that's the best time to go!”). Encourage the hesitant, "
            "reassure the worried, and vary your wording from one answer to the next. "
            "A few well-placed emojis — never cheesy. "
            "HIGHLIGHTS: wrap 2–3 key phrases in **double asterisks** — sparingly, for names and essentials only. "
            "PHOTOS: the system automatically attaches a beautiful photo of the place you talk about "
            "(several when the user asks for photos/images — then answer briefly); never invent image URLs "
            "and never describe the attached photos. "
            "Write a COMPLETE message (never end with a colon or an unfinished list). "
            "Always answer in ENGLISH. Be honest: if the answer is not in CONTEXT, say so plainly — never invent prices or visa rules. "
            "ONLY use URLs from CONTEXT for site_links and affiliate_links. "
            'Reply in JSON: {"message":"...","site_links":[{"title","url"}],"affiliate_links":[{"label","url","teaser"}]}'
        )
    return (
        site_scope_fr + " "
        "Tu es Mai 🌸, la conseillère voyage IA — guide indépendant Vietnam (pas une agence). "
        "LANGUE : réponds TOUJOURS en FRANÇAIS sur les pages FR ; ne mélange jamais l'anglais dans le message. "
        "CONNAISSANCE : utilise UNIQUEMENT les faits et URL du CONTEXTE + PLAN DU SITE. Si l'info manque, dis-le "
        "honnêtement — n'invente jamais. "
        "RÈGLE D'OR : réponds D'ABORD, DIRECTEMENT et précisément à la QUESTION posée, dès la première phrase. "
        "STYLE (type ChatGPT) : conversation naturelle, claire et précise — paragraphes courts séparés par une "
        "ligne vide, pas de remplissage, pas de liste de liens dans le message. Tu parles comme une amie experte, "
        "pas comme une brochure. "
        "CONCISION : question simple → 1–2 phrases (~60 mots) ; conseils → 3–5 phrases (~120 mots max). "
        "LIENS (rares) : dans la PLUPART des réponses site_links=[] et affiliate_links=[]. Ajoute AU PLUS "
        "1 site_link OU 1 affiliate_link seulement si le voyageur en a clairement besoin (page visa, préparer "
        "son voyage, réserver un hôtel, eSIM, assurance, activité). Jamais les deux sauf demande explicite. "
        "Pas de lien sur les questions bavardes ou de suivi. "
        "Adapte la longueur à la question — utilise l'HISTORIQUE pour les relances. "
        "Le site propose des guides dédiés : sécurité & arnaques, coutumes & étiquette, phrases utiles en vietnamien, "
        "test visa (evisa.gov.vn), météo par région/ville avec planificateur, apps utiles (Grab), eSIM & assurance — "
        "orientez vers la page correspondante du CONTEXTE quand c'est pertinent. "
        "VILLES — règle absolue : quand un bloc VILLES MENTIONNÉES est présent, ta réponse porte sur CES villes "
        "précises et respecte leurs repères factuels. Ne confonds JAMAIS deux villes distinctes (Đà Lạt, la ville "
        "d'altitude des hauts plateaux, n'est PAS Huế, la capitale impériale ; Đà Nẵng n'est pas Đà Lạt). "
        "Si le site n'a pas de page pour une ville demandée, dis-le honnêtement et donne quand même tes "
        "meilleurs conseils généraux. "
        "ORTHOGRAPHE : copie les noms de lieux EXACTEMENT comme dans le bloc ORTHOGRAPHE / CONTEXTE (Đà Lạt, Huế, "
        "Hội An, Phú Quốc, Ninh Bình…) — ne supprime jamais les accents. "
        "Si un bloc VISITOR PROFILE est présent, priorisez conseils et liens alignés avec "
        "son style, ses villes, sa durée et les pages déjà consultées — sans parler de tracking. "
        "PERSONNALITÉ : chaleureuse, enthousiaste et experte, avec une pointe d'humour léger et complice quand le "
        "sujet s'y prête — un trait d'esprit, un clin d'œil culturel (café à l'œuf, le ballet des scooters, "
        "traverser la rue comme un local…), jamais au détriment de la clarté ni sur les sujets sérieux (visa, "
        "santé, sécurité). Félicite sincèrement quand c'est mérité : bon choix de ville ou de saison, billets "
        "réservés, itinéraire malin (« Excellent choix ! », « Bravo, c'est la meilleure période ! »). Encourage "
        "les hésitants, rassure les inquiets, et varie tes formulations d'une réponse à l'autre. "
        "Quelques emojis bien placés — jamais lourd. "
        "MISE EN VALEUR : entoure 2 à 3 expressions clés avec **double astérisques** — avec parcimonie (noms, dates, "
        "conseils essentiels). "
        "Ne mets JAMAIS d'URL brute dans message. "
        "PHOTOS : le système joint automatiquement une belle photo du lieu dont tu parles "
        "(plusieurs si l'utilisateur demande des photos/images — réponds alors brièvement) ; "
        "n'invente pas d'URL d'image et ne décris pas les photos jointes. "
        "Rédige un message COMPLET (ne termine jamais par « : » ni une liste inachevée). "
        "Réponds TOUJOURS en FRANÇAIS. Reste honnête : si la réponse n'est pas dans le CONTEXTE, dis-le simplement — "
        "n'invente jamais de prix ni de règles visa. "
        "Utilise UNIQUEMENT les URL du CONTEXTE pour site_links et affiliate_links. "
        'Réponds en JSON : {"message":"...","site_links":[{"title","url"}],"affiliate_links":[{"label","url","teaser"}]}'
    )


def chat_reply(
    message: str,
    history: list[dict],
    lang: str,
    *,
    client_ip: str = "",
    track_url_fn,
    visitor_profile: dict | None = None,
    seen_photo_urls: list[str] | None = None,
) -> dict:
    from admin import ai_client, mistral_client

    if not is_enabled():
        raise ValueError("Chat indisponible — clé MISTRAL_API_KEY manquante.")

    message = (message or "").strip()
    if len(message) < 2:
        raise ValueError("Message trop court.")
    if len(message) > 900:
        raise ValueError("Message trop long (900 caractères max).")

    rate_err = _check_rate(client_ip)
    if rate_err:
        raise ValueError(rate_err)

    lang = "en" if lang == "en" else "fr"
    user_question = message

    # Les questions de suivi (« et en décembre ? ») n'ont souvent aucun mot-clé :
    # on enrichit la requête de récupération avec les derniers messages utilisateur.
    prev_user = [
        (turn.get("content") or "").strip()
        for turn in (history or [])
        if turn.get("role") == "user" and (turn.get("content") or "").strip()
    ]
    retrieval_query = " ".join(prev_user[-2:] + [message])
    chunks = retrieve(retrieval_query, lang, track_url_fn, visitor_profile=visitor_profile)
    context = _format_context(chunks)

    profile_block = ""
    if visitor_profile:
        try:
            from data.visitor_profile import profile_for_mai
            from locales.ui import t as ui_t
            profile_block = profile_for_mai(visitor_profile, lang, ui_t)
        except Exception:
            pass

    hist_lines = []
    for turn in (history or [])[-6:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()[:600]
        if role in ("user", "assistant") and content:
            hist_lines.append(f"{role.upper()}: {content}")

    # Ancres factuelles sur les villes citées (question + suivi) : Mai ne doit
    # JAMAIS confondre deux villes (ex. Đà Lạt ≠ Huế), même sans page dédiée.
    cities_block = _cities_block(retrieval_query, lang)
    ortho_block = _orthography_block(lang)
    site_map = _site_map_block(lang)

    user_block = (
        f"{site_map}\n\n"
        f"{ortho_block}\n\n"
        f"CONTEXTE SITE (pages & liens affiliés autorisés):\n{context}\n\n"
        + (f"{profile_block}\n\n" if profile_block else "")
        + (f"{cities_block}\n\n" if cities_block else "")
        + f"HISTORIQUE:\n" + ("\n".join(hist_lines) if hist_lines else "(premier message)") + "\n\n"
        f"QUESTION:\n{message}"
    )

    messages = [
        {"role": "system", "content": _system_prompt(lang)},
        {"role": "user", "content": user_block},
    ]

    try:
        resp = ai_client.chat_completion(
            messages=messages,
            max_tokens=CHAT_MAX_TOKENS,
            temperature=CHAT_TEMPERATURE,
            json_mode=True,
            fast=False,
            deadline=55,
        )
    except Exception as exc:
        raise ValueError(mistral_client.friendly_error(exc)) from exc

    raw = resp.choices[0].message.content
    data = ai_client.parse_json(raw)

    allowed_urls = {c.get("url") for c in chunks if c.get("url")}
    site_links = []
    for link in data.get("site_links") or []:
        url = _resolve_url((link.get("url") or "").strip(), allowed_urls)
        if _url_is_allowed(url, allowed_urls) and not any(
            c.get("url") == url and c.get("affiliate") for c in chunks
        ):
            site_links.append({"title": (link.get("title") or url)[:120], "url": url})

    affiliate_links = []
    for link in data.get("affiliate_links") or []:
        url = _resolve_url((link.get("url") or "").strip(), allowed_urls)
        if _url_is_allowed(url, allowed_urls):
            affiliate_links.append({
                "label": (link.get("label") or link.get("title") or "")[:100],
                "url": url,
                "teaser": (link.get("teaser") or "")[:160],
            })

    message = (data.get("message") or "").strip()
    message = _clean_message_body(message, lang)
    message = _ensure_context_highlights(message, user_question, lang)
    message = _fix_place_names(message, lang)
    enrich_text = message + "\n" + message + "\n" + "\n".join(
        (turn.get("content") or "") for turn in (history or [])[-4:]
    )
    slug = _detect_destination_slug(enrich_text, lang)
    city_name = ""
    if slug:
        from admin.store import get_destinations_dict
        city_name = get_destinations_dict(lang).get(slug, {}).get("name", "")

    site_links, affiliate_links = _auto_enrich_links(
        enrich_text,
        chunks,
        lang=lang,
        site_links=site_links,
        affiliate_links=affiliate_links,
    )
    site_links, affiliate_links = _curate_links(
        user_question,
        site_links,
        affiliate_links,
        lang,
    )
    # Pas de carte Leaflet lourde dans le chat — lien discret vers la page destination si besoin.
    map_cards: list[dict] = []
    photos: list[dict] = []
    try:
        from admin.chat_photos import build_chat_photos
        photos = build_chat_photos(
            user_question,
            enrich_text,
            lang,
            slug,
            detect_slug_fn=_detect_destination_slug,
            exclude_urls=seen_photo_urls,
        )
    except Exception:
        pass
    if _message_incomplete(message):
        message = _repair_message(
            message,
            lang,
            has_links=bool(site_links or affiliate_links),
            city=city_name,
        )

    return {
        "ok": True,
        "message": message,
        "site_links": site_links[:1],
        "affiliate_links": affiliate_links[:1],
        "map_cards": map_cards,
        "photos": photos[:3],
    }
