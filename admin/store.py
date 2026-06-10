"""Store contenu & réglages — Supabase (JSONB) ou fichiers JSON locaux."""

import logging
import re
import threading
from copy import deepcopy
from datetime import date

from data.affiliates import AFFILIATE_IDS as DEFAULT_AFFILIATE_IDS
from data.articles import ARTICLES as DEFAULT_ARTICLES
from data.experience_articles import EXPERIENCE_ARTICLES
from data.articles import CATEGORIES as DEFAULT_CATEGORIES
from data.destinations import DESTINATIONS as DEFAULT_DESTINATIONS

from admin.kv_store import get_json, set_json
from i18n_utils import (
    DEFAULT_LANG,
    localize_article,
    localize_category,
    localize_destination,
    wrap_article_i18n,
    wrap_destination_i18n,
)


def get_settings() -> dict:
    defaults = {
        "ga4_measurement_id": "",
        # Moteur IA : "groq" (défaut) ou "mistral", choisi depuis l'admin. Volontairement
        # ABSENT des défauts pour que, tant qu'aucun choix n'est enregistré, ai_client
        # puisse retomber sur la variable d'env AI_PROVIDER puis sur "groq".
        "groq_model": "llama-3.3-70b-versatile",
        "mistral_model": "mistral-small-latest",
        "mistral_fast_model": "open-mistral-nemo",
        # Image IA (Pollinations Flux) OPT-IN : par défaut on utilise des photos
        # Vietnam réelles (immédiates et fiables). Flux est lent et faisait pendre
        # la génération. Passer à true pour réactiver la génération d'image par IA.
        "ai_image_enabled": False,
        "commission_estimates": {
            "booking": 8.0,
            "agoda": 6.0,
            "getyourguide": 4.0,
            "viator": 4.0,
            "esim_airalo": 2.0,
            "esim_holafly": 2.0,
            "travel_insurance": 5.0,
            "pdf": 9.0,
        },
    }
    stored = get_json("settings", {}, file_name="settings.json")
    if stored is None:
        stored = {}
    return {**defaults, **stored}


def save_settings(data: dict):
    current = get_settings()
    current.update(data)
    set_json("settings", current, file_name="settings.json")


def get_affiliate_ids() -> dict:
    stored = get_json("affiliate_ids", {}, file_name="affiliate_ids.json")
    if stored is None:
        stored = {}
    merged = {**DEFAULT_AFFILIATE_IDS, **stored}
    # Migration World Nomads → Heymondo (ancienne clé)
    legacy = (merged.pop("worldnomads_affiliate", None) or "").strip()
    if legacy and legacy.upper() != "PLACEHOLDER":
        if legacy.lower().startswith("http"):
            merged.setdefault("heymondo_ref", legacy)
        elif not merged.get("heymondo_ref") or merged.get("heymondo_ref") == "PLACEHOLDER":
            merged["heymondo_ref"] = legacy
    return merged


def save_affiliate_ids(data: dict):
    set_json("affiliate_ids", data, file_name="affiliate_ids.json")


def get_custom_partners() -> list:
    stored = get_json("custom_partners", [], file_name="custom_partners.json")
    return stored if stored is not None else []


def save_custom_partners(partners: list):
    set_json("custom_partners", partners, file_name="custom_partners.json")


def add_custom_partner(partner: dict):
    partners = get_custom_partners()
    partners = [p for p in partners if p["id"] != partner["id"]]
    partners.append(partner)
    save_custom_partners(partners)


def delete_custom_partner(partner_id: str):
    partners = [p for p in get_custom_partners() if p["id"] != partner_id]
    save_custom_partners(partners)


def is_configured(value: str) -> bool:
    if not value or value.startswith("#"):
        return value.startswith("http")
    return "PLACEHOLDER" not in value.upper()


_BUILTIN_ARTICLES_SYNCED = False
_builtin_sync_lock = threading.Lock()
logger = logging.getLogger(__name__)


_EXPERIENCE_SLUGS = {a.get("slug") for a in EXPERIENCE_ARTICLES if a.get("slug")}
_DEFAULT_SLUGS = {a.get("slug") for a in DEFAULT_ARTICLES if a.get("slug")}
_BUILTIN_SLUGS = _EXPERIENCE_SLUGS | _DEFAULT_SLUGS

_IMAGE_META_KEYS = (
    "image", "image_photo_id", "image_placeholder", "image_alt", "image_source_url",
)


def _preserve_image_meta(builtin: dict, existing: dict | None) -> dict:
    """Garde les métadonnées image / traduction EN du store lors d'un overlay embarqué."""
    if not existing:
        return builtin
    for key in _IMAGE_META_KEYS:
        if existing.get(key) is not None:
            builtin[key] = existing[key]
    en = (existing.get("i18n") or {}).get("en") or {}
    if en.get("content"):
        builtin.setdefault("i18n", {})["en"] = en
    return builtin


def _overlay_builtin_articles(stored: list) -> list:
    """Fusionne guides expérience + articles embarqués (sauf édition manuelle admin)."""
    by_slug = {a.get("slug"): a for a in stored if a.get("slug")}
    merged: list = []

    for builtin in EXPERIENCE_ARTICLES:
        slug = builtin.get("slug")
        if not slug:
            continue
        existing = by_slug.get(slug)
        if existing and existing.get("admin_edited"):
            merged.append(existing)
        elif not existing or existing.get("builtin_version") != builtin.get("builtin_version"):
            merged.append(_preserve_image_meta(deepcopy(builtin), existing))
        else:
            merged.append(existing)

    for builtin in DEFAULT_ARTICLES:
        slug = builtin.get("slug")
        if not slug or slug in _EXPERIENCE_SLUGS:
            continue
        existing = by_slug.get(slug)
        if existing and existing.get("admin_edited"):
            merged.append(existing)
        else:
            merged.append(_preserve_image_meta(wrap_article_i18n(deepcopy(builtin)), existing))

    rest = [a for a in stored if a.get("slug") not in _BUILTIN_SLUGS]
    return merged + rest


def _raw_stored_articles() -> list:
    """Lecture KV brute (sans overlay expérience)."""
    try:
        stored = get_json("articles", None, file_name="articles.json")
    except Exception:
        return []
    return list(stored) if stored is not None else []


def replace_published_article(editing_slug: str, article: dict) -> dict:
    """Remplace un article publié (édition manuelle admin)."""
    article = wrap_article_i18n(article)
    article["admin_edited"] = True
    article["updated_at"] = date.today().isoformat()
    stored = _raw_stored_articles()
    stored = [a for a in stored if a.get("slug") not in (editing_slug, article["slug"])]
    stored.insert(0, article)
    save_articles(stored)
    return article


def ensure_builtin_articles() -> int:
    """Persiste en arrière-plan les guides expérience manquants dans le store KV.

    Ne doit pas être appelé sur le chemin HTTP : l'écriture Postgres du tableau
    articles complet peut dépasser le timeout Scalingo (~30 s).
    """
    global _BUILTIN_ARTICLES_SYNCED
    with _builtin_sync_lock:
        if _BUILTIN_ARTICLES_SYNCED:
            return 0
        try:
            builtins = [*EXPERIENCE_ARTICLES, *DEFAULT_ARTICLES]
            stored = get_json("articles", None, file_name="articles.json")
            if stored is None:
                set_json("articles", builtins, file_name="articles.json")
                _BUILTIN_ARTICLES_SYNCED = True
                return len(builtins)

            known = {a.get("slug") for a in stored if a.get("slug")}
            to_add = [a for a in builtins if a.get("slug") and a["slug"] not in known]
            if to_add:
                set_json("articles", [*to_add, *stored], file_name="articles.json")
            _BUILTIN_ARTICLES_SYNCED = True
            return len(to_add)
        except Exception:
            logger.exception("Échec synchronisation articles embarqués")
            _BUILTIN_ARTICLES_SYNCED = True
            return 0


def _raw_articles() -> list:
    try:
        stored = get_json("articles", None, file_name="articles.json")
    except Exception:
        logger.exception("Lecture articles KV impossible — repli sur contenu embarqué")
        return deepcopy([*EXPERIENCE_ARTICLES, *DEFAULT_ARTICLES])
    if stored is None:
        return deepcopy([*EXPERIENCE_ARTICLES, *DEFAULT_ARTICLES])
    return _overlay_builtin_articles(stored)


def get_articles(lang: str | None = None) -> list:
    articles = [wrap_article_i18n(a) for a in _raw_articles()]
    if lang:
        return [localize_article(a, lang) for a in articles]
    return articles


_CATEGORY_SYNC_DONE = False


def _stored_categories() -> dict:
    """Catégories personnalisées (admin/Linh) — KV `categories`."""
    try:
        stored = get_json("categories", {}, file_name="categories.json")
    except Exception:
        logger.exception("Lecture catégories KV impossible — repli sur catégories embarquées")
        return {}
    return dict(stored) if stored else {}


def save_custom_categories(categories: dict):
    set_json("categories", categories, file_name="categories.json")


def build_category(label_fr: str, label_en: str = "", description_fr: str = "", description_en: str = "") -> dict:
    label_fr = (label_fr or "").strip()
    label_en = (label_en or "").strip() or label_fr
    description_fr = (description_fr or "").strip() or (
        f"Articles « {label_fr} » — conseils et idées pour votre voyage au Vietnam."
    )
    description_en = (description_en or "").strip() or (
        f"“{label_en}” articles — tips and ideas for your Vietnam trip."
    )
    return {
        "label": label_fr,
        "description": description_fr,
        "i18n": {
            "fr": {"label": label_fr, "description": description_fr},
            "en": {"label": label_en, "description": description_en},
        },
    }


def sync_categories_with_articles() -> int:
    """Crée les catégories référencées par des articles mais encore inexistantes.

    Répare p.ex. un article publié en « tendances » sans page /categorie/tendances :
    la catégorie est créée depuis son category_label et apparaît aussitôt dans le
    menu du blog, la page catégorie et le sitemap.
    """
    global _CATEGORY_SYNC_DONE
    try:
        known = {**DEFAULT_CATEGORIES, **_stored_categories()}
        missing: dict = {}
        for raw in _raw_articles():
            article = wrap_article_i18n(raw)
            key = (article.get("category") or "").strip()
            if not key or key in known or key in missing:
                continue
            i18n = article.get("i18n") or {}
            label_fr = (
                (i18n.get("fr") or {}).get("category_label")
                or article.get("category_label")
                or key.replace("-", " ").title()
            ).strip()
            label_en = ((i18n.get("en") or {}).get("category_label") or "").strip()
            missing[key] = build_category(label_fr, label_en)
        if missing:
            stored = _stored_categories()
            stored.update(missing)
            save_custom_categories(stored)
        _CATEGORY_SYNC_DONE = True
        return len(missing)
    except Exception:
        logger.exception("Échec synchronisation catégories ↔ articles")
        _CATEGORY_SYNC_DONE = True
        return 0


def get_categories(lang: str | None = None) -> dict:
    if not _CATEGORY_SYNC_DONE:
        sync_categories_with_articles()
    merged = {**DEFAULT_CATEGORIES, **_stored_categories()}
    if not lang:
        return merged
    return {
        key: localize_category(cat, lang)
        for key, cat in merged.items()
    }


def add_category(label_fr: str, *, key: str = "", label_en: str = "",
                 description_fr: str = "", description_en: str = "") -> tuple[str, dict]:
    """Crée (ou met à jour) une catégorie de blog — clé slug auto depuis le nom FR."""
    label_fr = (label_fr or "").strip()
    if not label_fr:
        raise ValueError("Le nom (FR) de la catégorie est obligatoire.")
    key = slugify((key or "").strip() or label_fr)
    if not key:
        raise ValueError("Impossible de dériver une clé d'URL depuis ce nom.")
    cat = build_category(label_fr, label_en, description_fr, description_en)
    stored = _stored_categories()
    stored[key] = cat
    save_custom_categories(stored)
    return key, cat


def delete_category(key: str):
    key = (key or "").strip()
    if key in DEFAULT_CATEGORIES:
        raise ValueError(f"« {key} » est une catégorie intégrée — impossible de la supprimer.")
    used = sum(1 for a in _raw_articles() if (a.get("category") or "").strip() == key)
    if used:
        raise ValueError(f"{used} article(s) utilisent encore « {key} » — changez d'abord leur catégorie.")
    stored = _stored_categories()
    if key not in stored:
        raise ValueError(f"Catégorie introuvable : {key}")
    stored.pop(key)
    save_custom_categories(stored)


def category_usage_counts() -> dict:
    counts: dict[str, int] = {}
    for a in _raw_articles():
        key = (a.get("category") or "").strip()
        if key:
            counts[key] = counts.get(key, 0) + 1
    return counts


def _auto_translate_article(article: dict) -> dict:
    article = wrap_article_i18n(article)
    en = article.get("i18n", {}).get("en", {})
    if en.get("content"):
        return article
    try:
        from admin.groq_translate import translate_article_block
        fr = article["i18n"]["fr"]
        translated = translate_article_block({**article, **fr})
        article["i18n"]["en"] = {k: translated.get(k, fr.get(k, "")) for k in fr}
    except Exception:
        pass
    return article


def _auto_translate_destination(dest: dict) -> dict:
    dest = wrap_destination_i18n(dest)
    en = dest.get("i18n", {}).get("en", {})
    if en.get("overview"):
        return dest
    try:
        from admin.groq_translate import translate_destination_block
        fr = dest["i18n"]["fr"]
        translated = translate_destination_block({**dest, **fr})
        dest["i18n"]["en"] = {k: translated.get(k, fr.get(k, "")) for k in fr}
    except Exception:
        pass
    return dest


def save_articles(articles: list):
    global _CATEGORY_SYNC_DONE
    normalized = [_auto_translate_article(wrap_article_i18n(a)) for a in articles]
    set_json("articles", normalized, file_name="articles.json")
    # Un nouvel article peut référencer une catégorie inconnue : re-synchroniser
    # à la prochaine lecture (page catégorie, menu blog et sitemap à jour).
    _CATEGORY_SYNC_DONE = False


def get_article_by_slug(slug: str, lang: str | None = None) -> dict | None:
    article = next((a for a in _raw_articles() if a["slug"] == slug), None)
    if not article:
        return None
    article = wrap_article_i18n(article)
    return localize_article(article, lang) if lang else article


def add_article(article: dict):
    articles = _raw_articles()
    article = wrap_article_i18n(article)
    articles = [wrap_article_i18n(a) for a in articles if a["slug"] != article["slug"]]
    articles.insert(0, article)
    save_articles(articles)


def _raw_destinations() -> dict:
    stored = get_json("destinations", None, file_name="destinations.json")
    if stored is None:
        set_json("destinations", DEFAULT_DESTINATIONS, file_name="destinations.json")
        return deepcopy(DEFAULT_DESTINATIONS)
    return stored


def get_destinations_dict(lang: str | None = None) -> dict:
    raw = _raw_destinations()
    wrapped = {slug: wrap_destination_i18n(d) for slug, d in raw.items()}
    if not lang:
        return wrapped
    return {
        slug: localize_destination(d, lang)
        for slug, d in wrapped.items()
    }


def save_destinations(destinations: dict):
    normalized = {
        slug: _auto_translate_destination(wrap_destination_i18n(d))
        for slug, d in destinations.items()
    }
    set_json("destinations", normalized, file_name="destinations.json")


def get_destination_by_slug(slug: str, lang: str | None = None) -> dict | None:
    dest = _raw_destinations().get(slug)
    if not dest:
        return None
    dest = wrap_destination_i18n(dest)
    return localize_destination(dest, lang) if lang else dest


# Alias courants (erreurs de slug par Linh ou libellés ville ≠ slug publié).
_DESTINATION_SLUG_ALIASES: dict[str, str] = {
    "hu": "hue",
    "m-tho-delta-mekong": "delta-du-mekong",
    "my-tho-delta-mekong": "delta-du-mekong",
    "my-tho": "delta-du-mekong",
    "mekong-delta": "delta-du-mekong",
    "delta-mekong": "delta-du-mekong",
}


def find_destination_slug(hint: str) -> str | None:
    """Résout un slug, alias ou libellé vers le slug destination publié."""
    hint = (hint or "").strip().strip("/")
    if not hint:
        return None
    data = _raw_destinations()
    if hint in data:
        return hint
    slug_hint = slugify(hint)
    if slug_hint in data:
        return slug_hint
    if slug_hint in _DESTINATION_SLUG_ALIASES:
        return _DESTINATION_SLUG_ALIASES[slug_hint]
    hint_tokens = {t for t in slug_hint.split("-") if t and t not in ("du", "de", "the", "and", "le", "la")}
    best_slug: str | None = None
    best_score = 0
    for slug, raw in data.items():
        dest = wrap_destination_i18n(raw)
        names = {dest.get("name", "")}
        for lang in ("fr", "en"):
            loc = localize_destination(dest, lang)
            names.add(loc.get("name", ""))
        for name in names:
            if slugify(name) == slug_hint:
                return slug
        slug_tokens = set(slug.split("-"))
        score = len(hint_tokens & slug_tokens)
        if score > best_score:
            best_score = score
            best_slug = slug
    if best_score >= 2 and best_slug:
        return best_slug
    return None


def add_or_update_destination(dest: dict):
    from admin.image_service import (
        _align_destination_pool_image,
        _local_pool_path,
        attach_image_to_destination,
        destination_image_resolves,
        photo_id_matches_destination,
        pool_image_url,
    )

    dest = wrap_destination_i18n(dest)
    if not destination_image_resolves(dest):
        photo_id = (dest.get("image_photo_id") or "").strip()
        if photo_id and _local_pool_path(photo_id).exists() and photo_id_matches_destination(dest["slug"], photo_id):
            dest["image"] = pool_image_url(photo_id)
        else:
            dest.update(attach_image_to_destination(
                dest,
                dest.get("image_prompt"),
                image_nonce=abs(hash(dest["slug"])) % 9999,
            ))
    else:
        aligned = _align_destination_pool_image(dest)
        if aligned:
            dest.update(aligned)
    data = _raw_destinations()
    data[dest["slug"]] = dest
    save_destinations(data)
    try:
        from admin.map_service import defer_sync_destination
        defer_sync_destination(dest["slug"])
    except Exception:
        pass


def delete_destination(slug: str):
    data = _raw_destinations()
    data.pop(slug, None)
    save_destinations(data)


# Champs texte FR modifiables sur une destination publiée (admin & Linh).
DESTINATION_EDITABLE_FIELDS = ("name", "tagline", "meta_title", "meta_description", "overview")
DESTINATION_LIST_FIELDS = ("things_to_do", "hotels", "activities")

# Champs texte FR modifiables sur un article/guide publié (admin & Linh).
ARTICLE_EDITABLE_FIELDS = (
    "title", "meta_title", "meta_description", "excerpt", "content", "tags", "focus_keyword",
)


def set_destination_region(slug: str, region: str) -> dict:
    """Place une destination publiée dans la section Nord / Centre / Sud."""
    from data.trip_planner import REGION_ORDER

    region = (region or "").strip().lower()
    if region not in REGION_ORDER:
        raise ValueError("Région invalide — choisir north (Nord), central (Centre) ou south (Sud).")
    data = _raw_destinations()
    dest = data.get(slug)
    if not dest:
        raise ValueError(f"Destination introuvable : {slug}")
    dest["region"] = region
    save_destinations(data)
    return wrap_destination_i18n(dest)


def update_destination_fields(slug: str, fields: dict) -> dict:
    """Met à jour une destination publiée : textes FR, conseils et/ou région.

    Les champs FR modifiés sont aussi écrits dans i18n.fr, et le bloc EN est
    vidé pour être retraduit automatiquement à l'enregistrement.
    """
    data = _raw_destinations()
    raw = data.get(slug)
    if not raw:
        raise ValueError(f"Destination introuvable : {slug}")
    dest = wrap_destination_i18n(raw)

    changed_fr = False
    for key in DESTINATION_EDITABLE_FIELDS:
        value = fields.get(key)
        if value is None or not str(value).strip():
            continue
        value = str(value).strip()
        if key == "meta_description":
            value = value[:160]
        dest[key] = value
        dest["i18n"]["fr"][key] = value
        changed_fr = True

    tips = fields.get("tips")
    if isinstance(tips, str):
        tips = [ln.strip() for ln in tips.splitlines() if ln.strip()]
    if isinstance(tips, list):
        tips = [str(t).strip() for t in tips if str(t).strip()]
        if tips:
            dest["tips"] = tips
            dest["i18n"]["fr"]["tips"] = tips
            changed_fr = True

    for key in DESTINATION_LIST_FIELDS:
        value = fields.get(key)
        if not isinstance(value, list) or not value:
            continue
        dest[key] = value
        dest["i18n"]["fr"][key] = value
        changed_fr = True

    region = (fields.get("region") or "").strip().lower()
    if region:
        from data.trip_planner import REGION_ORDER
        if region not in REGION_ORDER:
            raise ValueError("Région invalide — choisir north, central ou south.")
        dest["region"] = region

    if changed_fr:
        dest["i18n"]["en"] = {}
        dest["updated_at"] = date.today().isoformat()

    data[slug] = dest
    save_destinations(data)
    return dest


# Champs image stockés au niveau racine (hors i18n) d'un article/destination.
_IMAGE_META_FIELDS = ("image", "image_photo_id", "image_source_url", "image_placeholder")


def _apply_image_meta(item: dict, meta: dict) -> None:
    """Applique les champs image d'un `meta` sur un item i18n (image_alt → fr+en)."""
    for key in _IMAGE_META_FIELDS:
        if key in meta:
            item[key] = meta[key]
    alt = meta.get("image_alt")
    if alt:
        item["image_alt"] = alt
        item.setdefault("i18n", {}).setdefault("fr", {})["image_alt"] = alt
        item.setdefault("i18n", {}).setdefault("en", {})["image_alt"] = alt


def update_article_fields(slug: str, fields: dict) -> dict:
    """Met à jour un article/guide publié : textes FR (retraduction EN automatique)."""
    data = _raw_articles()
    for i, raw in enumerate(data):
        if raw.get("slug") != slug:
            continue
        article = wrap_article_i18n(raw)
        changed_fr = False
        for key in ARTICLE_EDITABLE_FIELDS:
            value = fields.get(key)
            if value is None:
                continue
            if key == "tags":
                if isinstance(value, str):
                    value = [t.strip() for t in value.split(",") if t.strip()]
                if not isinstance(value, list):
                    continue
                value = [str(t).strip() for t in value if str(t).strip()]
            else:
                value = str(value).strip()
                if not value:
                    continue
                if key in ("meta_title",):
                    value = value[:70]
                if key in ("meta_description", "excerpt"):
                    value = value[:160]
            article[key] = value
            article["i18n"]["fr"][key] = value
            changed_fr = True
        category = (fields.get("category") or "").strip()
        if category and category != article.get("category"):
            cats = {**DEFAULT_CATEGORIES, **_stored_categories()}
            if category not in cats:
                raise ValueError(
                    f"Catégorie inconnue : « {category} » — créez-la d'abord (admin ou Linh)."
                )
            article["category"] = category
            label_fr = localize_category(cats[category], "fr").get("label", category)
            label_en = localize_category(cats[category], "en").get("label", category)
            article["category_label"] = label_fr
            article["i18n"]["fr"]["category_label"] = label_fr
            if article["i18n"].get("en"):
                article["i18n"]["en"]["category_label"] = label_en
        if changed_fr:
            article["i18n"]["en"] = {}
            article["date"] = date.today().isoformat()
        article["admin_edited"] = True
        article["updated_at"] = date.today().isoformat()
        data[i] = article
        save_articles(data)
        return article
    raise ValueError(f"Article introuvable : {slug}")


def apply_improved_article(slug: str, improved: dict) -> dict:
    """Enregistre le résultat d'un improve_guide IA sur un article publié."""
    data = _raw_articles()
    for i, raw in enumerate(data):
        if raw.get("slug") != slug:
            continue
        article = wrap_article_i18n(raw)
        for key in ARTICLE_EDITABLE_FIELDS:
            if improved.get(key):
                val = improved[key]
                if key in ("meta_title",):
                    val = str(val)[:70]
                if key in ("meta_description", "excerpt"):
                    val = str(val)[:160]
                article[key] = val
                article["i18n"]["fr"][key] = val
        for extra in ("word_count", "read_time", "image_prompt"):
            if improved.get(extra):
                article[extra] = improved[extra]
        article["i18n"]["en"] = {}
        article["date"] = date.today().isoformat()
        article["admin_edited"] = True
        article["updated_at"] = date.today().isoformat()
        data[i] = article
        save_articles(data)
        return article
    raise ValueError(f"Article introuvable : {slug}")


def apply_improved_destination(slug: str, improved: dict) -> dict:
    """Enregistre le résultat d'un improve_destination IA sur une page publiée."""
    fields = {
        k: improved[k]
        for k in (*DESTINATION_EDITABLE_FIELDS, *DESTINATION_LIST_FIELDS, "tips")
        if improved.get(k)
    }
    return update_destination_fields(slug, fields)


def update_article_image(slug: str, meta: dict) -> dict:
    """Met à jour l'image (et l'alt) d'un article publié, sans toucher au contenu."""
    data = _raw_articles()
    for i, raw in enumerate(data):
        if raw.get("slug") != slug:
            continue
        article = wrap_article_i18n(raw)
        _apply_image_meta(article, meta)
        data[i] = article
        save_articles(data)
        return article
    raise ValueError(f"Article introuvable : {slug}")


def update_destination_image(slug: str, meta: dict) -> dict:
    """Met à jour l'image (et l'alt) d'une destination publiée."""
    data = _raw_destinations()
    raw = data.get(slug)
    if not raw:
        raise ValueError(f"Destination introuvable : {slug}")
    dest = wrap_destination_i18n(raw)
    _apply_image_meta(dest, meta)
    data[slug] = dest
    save_destinations(data)
    return dest


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[àâä]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"ç", "c", text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def count_newsletter_subscribers() -> int:
    from admin.newsletter_service import get_newsletter_subscribers
    return len(get_newsletter_subscribers())


# ── Avis voyageurs ────────────────────────────────────────────────────
def get_reviews() -> list:
    from data.reviews import DEFAULT_REVIEWS

    stored = get_json("reviews", None, file_name="reviews.json")
    if stored is None:
        return deepcopy(DEFAULT_REVIEWS)
    return stored


def save_reviews(reviews: list):
    set_json("reviews", reviews, file_name="reviews.json")


def localized_reviews(lang: str) -> list:
    out = []
    for r in get_reviews():
        text = r.get("text", {})
        if isinstance(text, dict):
            body = text.get(lang) or text.get(DEFAULT_LANG) or ""
        else:
            body = text
        out.append({**r, "body": body})
    return out
