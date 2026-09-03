"""Flux RSS 2.0 + titres / meta descriptions dynamiques (pages + syndication)."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape, unescape
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import config
from admin.store import get_articles
from i18n_utils import lang_url

# Nombre d'articles publiés dans le flux (les plus récents).
FEED_LIMIT = 30

# SERP : titre ≤ 60, description ≤ 150, CTA obligatoire.
TITLE_MAX = 60
DESC_MAX = 150

# Angles distincts par page principale — pas de cannibalisation de mots-clés.
MAIN_PAGE_SEO: dict[str, dict[str, dict[str, str]]] = {
    "home": {
        "fr": {
            "title": "Voyage Vietnam : Circuit Hanoï-Ho Chi Minh",
            "description": (
                "Voyage Vietnam 2026 : circuit Hanoï-Ho Chi Minh, visas et conseils. "
                "Découvrez nos itinéraires sur mesure."
            ),
        },
        "en": {
            "title": "Vietnam travel: Hanoi-Ho Chi Minh circuit",
            "description": (
                "Vietnam travel 2026: Hanoi-Ho Chi Minh circuit, visas and tips. "
                "Discover our tailor-made itineraries."
            ),
        },
    },
    "voyages": {
        "fr": {
            "title": "Circuits Vietnam : 10 et 15 jours Nord-Sud",
            "description": (
                "Circuits Vietnam 10 et 15 jours, de Hanoï à Saigon. "
                "Comparez et composez votre itinéraire sur mesure."
            ),
        },
        "en": {
            "title": "Vietnam circuits: 10 and 15-day routes",
            "description": (
                "Vietnam circuits of 10 and 15 days, Hanoi to Saigon. "
                "Compare options and build your trip now!"
            ),
        },
    },
    "guides": {
        "fr": {
            "title": "Guides Vietnam : visa, budget et saison",
            "description": (
                "Guides pratiques Vietnam : visa, budget, saison et eSIM. "
                "Consultez nos checklists et préparez-vous."
            ),
        },
        "en": {
            "title": "Vietnam guides: visa, budget and season",
            "description": (
                "Practical Vietnam guides: visa, budget, season and eSIM. "
                "Follow the checklists and get ready to go."
            ),
        },
    },
}

_DEFAULT_SEO = {
    "fr": {
        "title": "Inside Vietnam Travel : guides et circuits",
        "description": (
            "Guides indépendants pour préparer un voyage au Vietnam. "
            "Découvrez nos itinéraires sur mesure."
        ),
    },
    "en": {
        "title": "Inside Vietnam Travel: guides and circuits",
        "description": (
            "Independent guides to plan a trip to Vietnam. "
            "Discover our tailor-made itineraries."
        ),
    },
}

# Libellé SEO court pour les villes (ex. tâche : « Voyage Dalat »).
_PLACE_SEO_NAME = {
    "da lat": "Dalat",
    "dalat": "Dalat",
    "da lat / lam dong": "Dalat",
    "da lat lam dong": "Dalat",
}


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"\s+", " ", text.lower()).strip()


def clip_title(title: str, max_len: int = TITLE_MAX) -> str:
    title = re.sub(r"\s+", " ", (title or "").strip())
    if len(title) <= max_len:
        return title
    cut = title[: max_len - 1].rsplit(" ", 1)[0]
    return cut or title[:max_len]


def clip_description(text: str, max_len: int = DESC_MAX) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return (cut or text[: max_len - 1]) + "…"


def page_seo(page_key: str, lang: str = "fr") -> tuple[str, str]:
    """Titre + description d'une page principale (`home`, `voyages`, `guides`)."""
    lang = "en" if lang == "en" else "fr"
    pack = MAIN_PAGE_SEO.get(page_key) or _DEFAULT_SEO
    loc = pack.get(lang) or pack.get("fr") or _DEFAULT_SEO[lang]
    return clip_title(loc["title"]), clip_description(loc["description"])


def default_seo(lang: str = "fr") -> tuple[str, str]:
    lang = "en" if lang == "en" else "fr"
    loc = _DEFAULT_SEO[lang]
    return clip_title(loc["title"]), clip_description(loc["description"])


def seo_place_name(place: str) -> str:
    raw = (place or "").strip()
    if not raw:
        return ""
    folded = _fold(raw)
    if folded in _PLACE_SEO_NAME:
        return _PLACE_SEO_NAME[folded]
    head = raw.split("/")[0].strip()
    folded_head = _fold(head)
    return _PLACE_SEO_NAME.get(folded_head, head)


def place_keyword(place: str, lang: str = "fr", *, kind: str = "voyage") -> str:
    """Mot-clé dynamique : « Voyage Dalat » / « Circuit Dalat » (ou trip/circuit EN)."""
    name = seo_place_name(place)
    if not name:
        return "Vietnam trip" if lang == "en" else "Voyage Vietnam"
    if lang == "en":
        return f"{name} trip" if kind == "voyage" else f"{name} circuit"
    return f"Voyage {name}" if kind == "voyage" else f"Circuit {name}"


def destination_seo(place: str, lang: str = "fr") -> tuple[str, str]:
    """Titre / description d'une fiche ville (Dalat → Voyage Dalat)."""
    lang = "en" if lang == "en" else "fr"
    kw = place_keyword(place, lang, kind="voyage")
    if lang == "en":
        title = f"{kw}: circuit and travel guide"
        desc = (
            f"{kw} in Vietnam: things to do, where to stay, how to get there. "
            "Discover our tailor-made itineraries."
        )
    else:
        title = f"{kw} : circuit et guide"
        desc = (
            f"{kw} au Vietnam : que faire, où dormir, comment y aller. "
            "Découvrez nos itinéraires sur mesure."
        )
    return clip_title(title), clip_description(desc)


def itinerary_seo(duration: int | str, lang: str = "fr") -> tuple[str, str]:
    lang = "en" if lang == "en" else "fr"
    days = str(duration).strip()
    if lang == "en":
        title = f"Vietnam circuit: {days} days north to south"
        desc = (
            f"{days}-day Vietnam circuit from Hanoi to Ho Chi Minh. "
            "Discover our tailor-made itineraries."
        )
    else:
        title = f"Circuit Vietnam {days} jours : Nord-Sud"
        desc = (
            f"Circuit Vietnam {days} jours, Hanoï à Ho Chi Minh. "
            "Découvrez nos itinéraires sur mesure."
        )
    return clip_title(title), clip_description(desc)


def enrich_title_with_place(title: str, place: str | None, lang: str = "fr") -> str:
    """Ajoute « Voyage {ville} » / « Circuit {ville} » si la page vise un lieu."""
    title = (title or "").strip()
    place = (place or "").strip()
    if not place or place in ("Tout le Vietnam", "All Vietnam"):
        return clip_title(title)
    folded_title = _fold(title)
    name = seo_place_name(place)
    has_place = bool(name) and (
        _fold(name) in folded_title or _fold(place.split("/")[0]) in folded_title
    )
    has_intent = any(
        token in folded_title
        for token in ("voyage ", " circuit", "circuit ", "trip", "itinerary")
    )
    kw = place_keyword(place, lang, kind="voyage")
    if has_place and has_intent:
        return clip_title(title)
    if _fold(kw) in folded_title:
        return clip_title(title)
    if title:
        return clip_title(f"{kw} : {title}")
    return clip_title(kw)


def _extract_title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html or "", re.I | re.S)
    if not match:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", match.group(1)))).strip()


def _extract_description(html: str) -> str:
    match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
        html or "",
        re.I,
    )
    return unescape(match.group(1)).strip() if match else ""


def check_url(
    path: str,
    *,
    client=None,
    base_url: str | None = None,
    timeout: float = 10,
    follow_redirects: bool = True,
) -> dict:
    """Lit `<title>` et `<meta name="description">` du HTML rendu.

    - chemin relatif + `client` Flask (tests)
    - URL absolue ou `base_url` (contrôle après déploiement)
    """
    path = (path or "").strip() or "/"
    status = 0
    html = ""
    final_url = path
    if client is not None:
        resp = client.get(path, follow_redirects=follow_redirects)
        status = resp.status_code
        html = resp.get_data(as_text=True)
        final_url = getattr(resp, "request", None)
        final_url = getattr(final_url, "path", path) if final_url is not None else path
    else:
        url = path if path.startswith("http") else urljoin(
            (base_url or config.SITE_URL).rstrip("/") + "/",
            path.lstrip("/"),
        )
        req = Request(url, headers={"User-Agent": "InsideVietnamTravel-seo-check/1.0"})
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — URL contrôlée (site ou test)
            status = getattr(resp, "status", 200)
            html = resp.read().decode("utf-8", errors="replace")
            final_url = resp.geturl()
    title = _extract_title(html)
    description = _extract_description(html)
    return {
        "url": final_url,
        "status": status,
        "title": title,
        "description": description,
        "title_len": len(title),
        "description_len": len(description),
        "ok": bool(title and description and status == 200),
    }


def _site_base() -> str:
    return config.SITE_URL.rstrip("/")


def _strip_html(text: str, max_len: int = 320) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", unescape(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


def _parse_date(value: str | None) -> datetime:
    """Best-effort parsing d'une date d'article → datetime aware (UTC)."""
    if value:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value[: len(fmt) + 2], fmt).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
    return datetime.now(timezone.utc)


def _abs_image(path: str | None) -> str | None:
    if not path:
        return None
    path = path.strip()
    if not path:
        return None
    if "://" in path:
        return path
    return _site_base() + "/" + path.lstrip("/")


def render_blog_feed(lang: str = "fr") -> str:
    base = _site_base()
    lang = lang if lang in ("fr", "en") else "fr"
    self_url = base + ("/en/feed.xml" if lang == "en" else "/feed.xml")
    blog_url = base + lang_url("blog_index", lang)

    if lang == "en":
        title = clip_title("Vietnam travel blog: guides and news")
        description = clip_description(
            config.SITE_DESCRIPTION_I18N.get("en", config.SITE_DESCRIPTION)
        )
        language = "en"
    else:
        title = clip_title("Blog voyage Vietnam : guides et actualités")
        description = clip_description(
            config.SITE_DESCRIPTION_I18N.get("fr", config.SITE_DESCRIPTION)
        )
        language = "fr"

    articles = get_articles(lang)[:FEED_LIMIT]
    build_date = format_datetime(datetime.now(timezone.utc))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "  <channel>",
        f"    <title>{escape(title)}</title>",
        f"    <link>{escape(blog_url)}</link>",
        f"    <description>{escape(description)}</description>",
        f"    <language>{language}</language>",
        f"    <lastBuildDate>{build_date}</lastBuildDate>",
        f"    <generator>{escape(config.SITE_NAME)}</generator>",
        f'    <atom:link href="{escape(self_url)}" rel="self" type="application/rss+xml" />',
    ]

    for article in articles:
        slug = article.get("slug")
        if not slug:
            continue
        url = base + lang_url("article", lang, slug=slug)
        item_title = enrich_title_with_place(
            _strip_html(article.get("title", slug), 180),
            article.get("city"),
            lang,
        )
        summary = clip_description(
            _strip_html(
                article.get("excerpt") or article.get("meta_description") or "", 320
            )
        )
        pub_date = format_datetime(_parse_date(article.get("date") or article.get("updated_at")))
        category = article.get("category") or article.get("city")

        lines.append("    <item>")
        lines.append(f"      <title>{escape(item_title)}</title>")
        lines.append(f"      <link>{escape(url)}</link>")
        lines.append(f'      <guid isPermaLink="true">{escape(url)}</guid>')
        lines.append(f"      <pubDate>{pub_date}</pubDate>")
        if category:
            lines.append(f"      <category>{escape(str(category))}</category>")
        lines.append(f"      <description>{escape(summary)}</description>")
        image = _abs_image(article.get("image"))
        if image:
            mime = (
                "image/webp" if image.endswith(".webp")
                else "image/png" if image.endswith(".png")
                else "image/jpeg"
            )
            lines.append(
                f'      <enclosure url="{escape(image)}" type="{mime}" length="0" />'
            )
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"
