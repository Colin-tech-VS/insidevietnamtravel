"""Photos pour le chat Mai — priorité au site, complément Pixabay qualité.

Mai propose spontanément UNE belle photo de la destination dont elle parle
(et jusqu'à trois quand on lui demande des images). Les URLs déjà affichées
dans la conversation sont exclues : jamais deux fois la même photo.
"""

from __future__ import annotations

import config

_PHOTO_INTENT_WORDS = (
    "photo", "photos", "image", "images", "picture", "pictures", "pic", "pics",
    "montre", "montrer", "montrez", "voir", "illustre", "illustrer", "aperçu",
    "aperçu", "visuel", "envoie", "envoyer", "show me", "look at", "gallery",
    "photograph", "photographie",
)

# Cache des candidats Pixabay par requête (les exclusions s'appliquent ensuite,
# au moment de la sélection — le cache reste donc valable pour toute la session).
_PIXABAY_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 600.0


def wants_photos(text: str) -> bool:
    hay = (text or "").lower()
    return any(w in hay for w in _PHOTO_INTENT_WORDS)


def _abs_url(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return config.SITE_URL.rstrip("/") + (path if path.startswith("/") else "/" + path)


def _url_key(url: str) -> str:
    """Clé de déduplication : sans query string, sans origine du site.

    Le front renvoie les URLs absolues telles qu'affichées ; les photos du site
    sont construites en relatif puis absolutisées — on compare donc sur le chemin.
    """
    url = (url or "").split("?")[0].strip()
    site = config.SITE_URL.rstrip("/")
    if site and url.startswith(site + "/"):
        url = url[len(site):]
    return url


def _site_photos(
    slug: str | None,
    lang: str,
    *,
    max_n: int = 2,
    exclude: set[str] | None = None,
) -> list[dict]:
    from admin.image_service import (
        _photo_id_from_pool_url,
        _photo_ids_for_destination,
        persistent_image_url,
        photo_id_matches_destination,
        pool_image_url,
    )
    from admin.store import get_articles, get_destinations_dict

    lang = "en" if lang == "en" else "fr"
    out: list[dict] = []
    seen: set[str] = set(exclude or ())

    def _pool_key(pid: str) -> str:
        return _url_key(pool_image_url(pid))

    # Une même photo du pool peut être servie sous une autre URL (fichier blog/ ou
    # destinations/ généré depuis elle) : on étend l'exclusion à la forme pool pour
    # ne jamais remontrer le même visuel sous une URL différente.
    if seen:
        for art in get_articles(lang):
            pid = art.get("image_photo_id") or ""
            if pid and _url_key(art.get("image") or "") in seen:
                seen.add(_pool_key(pid))
        for d in get_destinations_dict(lang).values():
            pid = d.get("image_photo_id") or ""
            if pid and _url_key(d.get("image") or "") in seen:
                seen.add(_pool_key(pid))

    def add(
        url: str | None,
        alt: str,
        *,
        caption: str = "",
        page_url: str = "",
        photo_id: str = "",
    ) -> None:
        if not url or len(out) >= max_n:
            return
        resolved = persistent_image_url(url, None, url if url.startswith("http") else None)
        if not resolved:
            resolved = url
        key = _url_key(resolved)
        pid = photo_id or _photo_id_from_pool_url(resolved)
        keys = {key} | ({_pool_key(pid)} if pid else set())
        if not key or keys & seen:
            return
        seen.update(keys)
        item: dict = {
            "url": _abs_url(resolved) if resolved.startswith("/") else resolved,
            "alt": (alt or "Vietnam")[:140],
            "source": "site",
            "credit": "Inside Vietnam Travel",
        }
        if caption:
            item["caption"] = caption[:120]
        if page_url:
            item["page_url"] = _abs_url(page_url)
        out.append(item)

    if slug:
        dest = get_destinations_dict(lang).get(slug, {})
        name = dest.get("name") or slug.replace("-", " ")
        img = persistent_image_url(
            dest.get("image"),
            dest.get("image_photo_id"),
            dest.get("image_source_url"),
        )
        from i18n_utils import lang_url
        page = _abs_url(lang_url("destination_page", lang, slug=slug))
        add(
            img,
            name,
            caption=dest.get("tagline", "") or name,
            page_url=page,
            photo_id=dest.get("image_photo_id") or "",
        )

        for pid in _photo_ids_for_destination(slug):
            if len(out) >= max_n:
                break
            add(pool_image_url(pid), name, caption=name, page_url=page)

    name_fold = ""
    if slug:
        from admin.store import get_destinations_dict
        name_fold = (get_destinations_dict(lang).get(slug, {}).get("name") or "").lower()

    for art in get_articles(lang):
        if len(out) >= max_n:
            break
        hay = f"{art.get('title', '')} {art.get('excerpt', '')} {art.get('city', '')}".lower()
        if slug and name_fold and name_fold not in hay and slug.replace("-", " ") not in hay:
            continue
        # L'image doit MONTRER la destination, pas seulement illustrer un article
        # qui la mentionne (ex. rizières de Sapa sur un guide « Hanoï en 7 jours »).
        pid = art.get("image_photo_id") or ""
        if slug and pid and not photo_id_matches_destination(slug, pid):
            continue
        img = persistent_image_url(
            art.get("image"),
            art.get("image_photo_id"),
            art.get("image_source_url"),
        )
        if not img:
            continue
        from i18n_utils import lang_url
        add(
            img,
            art.get("image_alt") or art.get("title", ""),
            caption=art.get("title", "")[:120],
            page_url=_abs_url(lang_url("article", lang, slug=art["slug"])),
            photo_id=pid,
        )

    return out


def _pixabay_candidates(query: str) -> list[dict]:
    """Candidats Pixabay triés qualité : sélection éditoriale d'abord, puis populaires.

    Une seule passe réseau par requête (cache 10 min) — la sélection finale filtre
    les URLs déjà montrées, le cache reste donc réutilisable toute la conversation.
    """
    import time
    now = time.monotonic()
    cached = _PIXABAY_CACHE.get(query)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    import requests

    from admin.image_service import (
        PIXABAY_API_URL,
        PIXABAY_CONNECT_TIMEOUT,
        PIXABAY_READ_TIMEOUT,
        _pixabay_api_key,
    )

    key = _pixabay_api_key()
    hits: list[dict] = []
    if key:
        seen_ids: set = set()
        # Deux passes : la sélection éditoriale Pixabay (photos primées, très
        # « vendeuses ») puis, en complément, les plus populaires en grand format.
        for editors_choice in ("true", "false"):
            if len(hits) >= 12:
                break
            try:
                resp = requests.get(
                    PIXABAY_API_URL,
                    params={
                        "key": key,
                        "q": query,
                        "image_type": "photo",
                        "orientation": "horizontal",
                        "safesearch": "true",
                        "editors_choice": editors_choice,
                        "order": "popular",
                        "min_width": 1200,
                        "per_page": 24,
                        "lang": "en",
                    },
                    timeout=(PIXABAY_CONNECT_TIMEOUT, PIXABAY_READ_TIMEOUT),
                    headers={"User-Agent": "InsideVietnamTravel/1.0"},
                )
                resp.raise_for_status()
                for hit in resp.json().get("hits", []):
                    hid = hit.get("id")
                    url = hit.get("largeImageURL") or hit.get("webformatURL")
                    if not url or hid in seen_ids:
                        continue
                    seen_ids.add(hid)
                    hits.append({"url": url, "tags": (hit.get("tags") or "")})
            except Exception:
                break
    _PIXABAY_CACHE[query] = (now, hits)
    return hits


def _web_photos(
    query: str,
    slug: str | None,
    lang: str,
    *,
    max_n: int,
    exclude: set[str] | None = None,
) -> list[dict]:
    if max_n <= 0:
        return []

    from admin.image_service import destination_pixabay_query
    from admin.store import get_destinations_dict

    q = query.strip()
    if slug:
        dest = get_destinations_dict(lang).get(slug, {})
        q = destination_pixabay_query(slug, dest)
    elif len(q) < 8:
        q = f"{q} Vietnam travel"

    out: list[dict] = []
    seen: set[str] = set(exclude or ())
    for hit in _pixabay_candidates(q):
        if len(out) >= max_n:
            break
        key = _url_key(hit.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({
            "url": hit["url"],
            "alt": q[:140],
            "source": "web",
            "credit": "Pixabay",
        })
    return out


def build_chat_photos(
    user_question: str,
    context_text: str,
    lang: str,
    slug: str | None,
    *,
    detect_slug_fn=None,
    exclude_urls: list[str] | None = None,
) -> list[dict]:
    """Photos de la réponse : 1 spontanée si destination détectée, 3 si demandées.

    `exclude_urls` = photos déjà affichées dans la conversation → jamais réutilisées.
    """
    exclude = {_url_key(u) for u in (exclude_urls or []) if u}
    exclude.discard("")

    if not slug and detect_slug_fn:
        slug = detect_slug_fn(user_question, lang) or detect_slug_fn(context_text, lang)

    # Demande explicite (« montre-moi des photos… ») jugée sur la QUESTION seule :
    # « à voir » dans la réponse de Mai ne doit pas déclencher une galerie complète.
    explicit = wants_photos(user_question)
    if not explicit and not slug:
        return []
    max_total = 3 if explicit else 1

    site = _site_photos(slug, lang, max_n=min(2, max_total), exclude=exclude)
    need_web = max(0, max_total - len(site))
    web: list[dict] = []
    if need_web:
        q = user_question
        if slug:
            from admin.store import get_destinations_dict
            name = get_destinations_dict(lang).get(slug, {}).get("name", "")
            if name and name.lower() not in q.lower():
                q = f"{name} {q}"
        already = exclude | {_url_key(p.get("url", "")) for p in site}
        web = _web_photos(q, slug, lang, max_n=need_web, exclude=already)

    combined = site + web
    seen: set[str] = set()
    unique: list[dict] = []
    for p in combined:
        key = _url_key(p.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique[:max_total]
