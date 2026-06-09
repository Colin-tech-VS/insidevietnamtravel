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


def retrieve(query: str, lang: str, track_url_fn, top_n: int = 8) -> list[dict]:
    q_tokens = _tokenize(query, lang)
    hay = query.lower()
    if any(w in hay for w in ("hotel", "hôtel", "dormir", "heberg", "héberg", "stay", "carte", "map")):
        top_n = max(top_n, 12)
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
    place = city or ("Hanoï" if lang != "en" else "Hanoi")
    if lang == "en":
        suffix = (
            " See the links below for our picks and the interactive map."
            if has_links
            else f" Browse our {place} destination guide for hotel ideas."
        )
    else:
        suffix = (
            " Retrouvez nos sélections et la carte interactive juste en dessous."
            if has_links
            else f" Consultez notre guide {place} pour des idées d'hébergement."
        )
    return msg + suffix


def _detect_destination_slug(text: str, lang: str) -> str | None:
    from admin.store import get_destinations_dict

    hay = unicodedata.normalize("NFKD", (text or "").lower())
    hay = "".join(c for c in hay if not unicodedata.combining(c))
    for slug, dest in get_destinations_dict(lang).items():
        name = dest.get("name", "")
        name_norm = unicodedata.normalize("NFKD", name.lower())
        name_norm = "".join(c for c in name_norm if not unicodedata.combining(c))
        if name_norm and name_norm in hay:
            return slug
        if slug.replace("-", " ") in hay:
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
        "hue": ("hue", "huế"),
    }
    for slug, keys in aliases.items():
        if any(k in hay for k in keys):
            return slug
    return None


def _auto_enrich_links(
    message: str,
    chunks: list[dict],
    *,
    lang: str,
    site_links: list[dict],
    affiliate_links: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Complète site_links / affiliate_links si l'IA oublie ou si les URLs ne matchent pas."""
    hay = message.lower()
    hotel_q = any(w in hay for w in ("hotel", "hôtel", "dormir", "heberg", "héberg", "stay", "lodging"))
    activity_q = any(w in hay for w in ("activit", "faire", "visit", "tour", "excursion"))
    slug = _detect_destination_slug(message, lang)

    existing_site = {l["url"] for l in site_links}
    existing_aff = {l["url"] for l in affiliate_links}

    def add_site(chunk: dict) -> None:
        url = chunk.get("url", "")
        if not url or url in existing_site:
            return
        site_links.append({"title": (chunk.get("title") or url)[:120], "url": url})
        existing_site.add(url)

    def add_aff(chunk: dict, label: str | None = None) -> None:
        url = chunk.get("url", "")
        if not url or url in existing_aff:
            return
        affiliate_links.append({
            "label": (label or chunk.get("title") or url)[:100],
            "url": url,
            "teaser": (chunk.get("text") or "")[:160],
        })
        existing_aff.add(url)

    if not slug and not (hotel_q or activity_q):
        return site_links[:4], affiliate_links[:3]

    for chunk in chunks:
        cid = chunk.get("id", "")
        if slug and cid == f"map:page:{slug}":
            add_site(chunk)
        elif slug and cid == f"dest-rich:{slug}":
            add_site(chunk)
        elif slug and hotel_q and cid == f"aff:hotel:{slug}":
            add_aff(chunk)
        elif slug and activity_q and cid == f"aff:activity:{slug}":
            add_aff(chunk)
        elif slug and hotel_q and cid.startswith("map:pin:") and chunk.get("affiliate"):
            from admin.store import get_destinations_dict
            dest_name = get_destinations_dict(lang).get(slug, {}).get("name", "")
            title = chunk.get("title", "")
            if dest_name and dest_name.lower() in title.lower():
                add_aff(chunk, label=title.split("—")[0].strip() or title)

    return site_links[:4], affiliate_links[:3]


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
    if lang == "en":
        return (
            "You are Mai 🌸, the friendly AI travel advisor for Inside Vietnam Travel — "
            "an independent Vietnam travel guide (not a travel agency). "
            "Your mission: inspire people to travel to Vietnam, give concrete practical advice, "
            "and recommend relevant pages from the site CONTEXT plus affiliate partner links "
            "when they genuinely help (eSIM, insurance, hotels, activities). "
            "Each destination page has an interactive map (#dest-map) with affiliate pins — recommend it when "
            "the user asks where to stay, what to do, or wants a visual plan. "
            "Tone: warm, enthusiastic, expert, with a few well-placed emojis — never cheesy. "
            "Highlight 2–5 key terms per answer with **double asterisks** (destinations, seasons, durations, practical tips). "
            "Write a COMPLETE message (never end with a colon or an unfinished list). "
            "Name 2–3 concrete picks in the message; put Booking/map links in affiliate_links and site_links using EXACT URLs from CONTEXT. "
            "Always answer in ENGLISH. Be honest about limits; never invent prices or visas rules. "
            "ONLY use URLs from CONTEXT for site_links and affiliate_links. "
            'Reply in JSON: {"message":"...","site_links":[{"title","url"}],"affiliate_links":[{"label","url","teaser"}]}'
        )
    return (
        "Tu es Mai 🌸, la conseillère voyage IA d'Inside Vietnam Travel — "
        "guide indépendant Vietnam (pas une agence). "
        "Ta mission : donner envie de voyager au Vietnam, conseiller concrètement quoi faire, "
        "quand y aller, comment s'organiser, et orienter vers les pages du site (CONTEXTE) "
        "ainsi que les liens affiliés pertinents (eSIM, assurance, hôtels, activités) quand "
        "cela aide vraiment le voyageur. "
        "Chaque page destination a une carte interactive (#dest-map) avec pins affiliés — recommandez-la quand "
        "l'utilisateur demande où dormir, quoi faire ou un plan visuel. "
        "Ton : chaleureux, enthousiaste, expert, quelques emojis bien placés — jamais lourd. "
        "Mets en valeur 2 à 5 mots-clés par réponse avec **double astérisques** (destinations, saisons, durées, conseils pratiques). "
        "Rédige un message COMPLET (ne termine jamais par « : » ni une liste inachevée). "
        "Cite 2–3 hébergements ou activités concrètes dans le message ; mets les liens Booking/carte dans affiliate_links et site_links avec les URL EXACTES du CONTEXTE. "
        "Réponds TOUJOURS en FRANÇAIS. Reste honnête ; n'invente pas de prix ni de règles visa. "
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
    chunks = retrieve(message, lang, track_url_fn)
    context = _format_context(chunks)

    hist_lines = []
    for turn in (history or [])[-6:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()[:600]
        if role in ("user", "assistant") and content:
            hist_lines.append(f"{role.upper()}: {content}")

    user_block = (
        f"CONTEXTE SITE (pages & liens affiliés autorisés):\n{context}\n\n"
        f"HISTORIQUE:\n" + ("\n".join(hist_lines) if hist_lines else "(premier message)") + "\n\n"
        f"QUESTION:\n{message}"
    )

    messages = [
        {"role": "system", "content": _system_prompt(lang)},
        {"role": "user", "content": user_block},
    ]

    try:
        resp = mistral_client.chat_completion(
            messages=messages,
            max_tokens=1600,
            temperature=0.72,
            json_mode=True,
            fast=True,
        )
    except Exception as exc:
        from admin import ai_client as _ai
        if _ai._has_key("groq"):
            resp = _ai.chat_completion(
                messages=messages,
                max_tokens=1600,
                temperature=0.72,
                json_mode=True,
                fast=True,
                deadline=55,
            )
        else:
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
        "site_links": site_links[:4],
        "affiliate_links": affiliate_links[:3],
    }
