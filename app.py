"""Inside Vietnam Travel — affiliate travel guide (Flask)."""

import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
from flask import (
    Flask, render_template, abort, Response, url_for,
    request, redirect, flash,
)
from flask_compress import Compress

import config
from i18n_utils import (
    canonical_for_request,
    detect_lang_from_path,
    get_lang,
    hreflang_urls,
    lang_url,
    localize_itinerary,
    set_lang,
    page_url_in_lang,
    switch_lang_url,
)
from locales.ui import t
from seo_sitemap import render_sitemap_xml
from seo_utils import (
    article_meta_description,
    article_meta_title,
    breadcrumb_schema,
    build_meta_title,
    extract_faq_from_html,
    faq_schema,
    item_list_schema,
    organization_schema,
    truncate_text,
    webpage_schema,
    website_schema,
)
from admin import admin_bp
from admin import db as analytics_db
from admin.image_service import persistent_image_url
from admin.store import get_articles, get_article_by_slug, get_categories, get_settings, get_destinations_dict
from data.trip_planner import destinations_by_region
from data.affiliate_urls import (
    LOCATION_META,
    build_activity_link,
    build_hotel_link,
    esim_airalo,
    esim_holafly,
    get_location_meta,
    pdf_checkout,
    transport_12go,
    travel_insurance,
    visa_ivisa,
)
from data.itineraries import ITINERARIES
from data.affiliates import PDF_GUIDE, NEWSLETTER
from data import pillars

RESERVED_SLUGS = frozenset({
    "blog", "admin", "go", "itineraries", "a-propos", "newsletter",
    "politique-confidentialite", "mentions-legales",
    "robots.txt", "sitemap.xml", "llms.txt", "llms-full.txt",
    "AgodaPartnerVerification.htm",
    "categorie", "category", "static", "favicon.ico", "guide",
    "en", "about", "privacy", "legal", "unsubscribe", "contact", "guide-pdf",
    "preparer-mon-voyage", "plan-my-trip",
    "quand-partir-au-vietnam", "best-time-to-visit-vietnam",
    "calculateur-budget-vietnam", "vietnam-budget-calculator",
    "visa-vietnam", "vietnam-visa",
    "esim-assurance-vietnam", "esim-insurance-vietnam",
    "applications-utiles-vietnam", "useful-apps-vietnam",
})

load_dotenv()

import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-change-in-production")
app.config.from_object(config)

if os.environ.get("PORT") or os.environ.get("SCALINGO_APP"):
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config["COMPRESS_MIMETYPES"] = [
    "text/html", "text/css", "text/javascript", "application/javascript",
    "application/json", "image/svg+xml",
]
app.config["COMPRESS_LEVEL"] = 6
app.config["COMPRESS_MIN_SIZE"] = 256
Compress(app)
app.register_blueprint(admin_bp)


# Heure de démarrage du process : un nouveau déploiement redémarre le serveur, donc
# si /healthz affiche une heure ancienne, c'est que le code en ligne n'a PAS été
# redéployé (cause n°1 des « ça bloque encore » alors que le correctif est sur main).
APP_BOOT_TIME = datetime.utcnow()


@app.route("/healthz")
def healthz():
    """Sonde de santé + repère de déploiement (heure de boot, version)."""
    return {
        "status": "ok",
        "boot_time_utc": APP_BOOT_TIME.isoformat() + "Z",
        "version": (
            os.environ.get("CONTAINER_VERSION")
            or os.environ.get("SOURCE_VERSION")
            or "unknown"
        ),
    }



def _articles(lang=None):
    articles = get_articles(lang or get_lang())
    for a in articles:
        a["image"] = persistent_image_url(a.get("image"), a.get("image_photo_id"), a.get("image_source_url"))
    return articles


def _categories(lang=None):
    return get_categories(lang or get_lang())


def _destinations(lang=None):
    """Destinations publiques — image admin + repli source_url si fichier local absent."""
    lang = lang or get_lang()
    out = {}
    for slug, d in get_destinations_dict(lang).items():
        dest = dict(d)
        dest["image"] = persistent_image_url(
            dest.get("image"),
            dest.get("image_photo_id"),
            dest.get("image_source_url"),
        )
        out[slug] = dest
    return out


def _itineraries(lang=None):
    lang = lang or get_lang()
    return {
        slug: localize_itinerary(it, lang)
        for slug, it in ITINERARIES.items()
    }


def _localized_block(block: dict, lang: str) -> dict:
    result = {k: v for k, v in block.items() if k != "i18n"}
    if lang == "en" and block.get("i18n", {}).get("en"):
        result.update(block["i18n"]["en"])
    return result


def _log_page_view_async(path: str, referrer: str, user_agent: str, ip_hash: str,
                         client_ip: str, utm_source: str = "", utm_campaign: str = ""):
    try:
        from admin.geoip import resolve_location

        country_code, country_name, city = resolve_location(client_ip)
        analytics_db.log_page_view(
            path=path,
            referrer=referrer,
            user_agent=user_agent,
            ip_hash=ip_hash,
            country_code=country_code,
            country_name=country_name,
            city=city,
            utm_source=utm_source,
            utm_campaign=utm_campaign,
        )
    except Exception:
        pass


@app.before_request
def prepare_request():
    set_lang(detect_lang_from_path())


@app.before_request
def track_page_view():
    from admin.analytics_filters import analytics_ip_hash, should_track_page_view

    if request.method != "GET":
        return
    path = request.path
    if path.startswith(("/admin", "/static", "/go/", "/favicon", "/api/")):
        return
    client_ip = (request.remote_addr or "").strip()
    user_agent = (request.user_agent.string or "")[:200]
    if not should_track_page_view(path=path, user_agent=user_agent, client_ip=client_ip):
        return
    ip_hash = analytics_ip_hash(client_ip)
    utm_source = (request.args.get("utm_source") or "")[:60]
    utm_campaign = (request.args.get("utm_campaign") or "")[:120]
    threading.Thread(
        target=_log_page_view_async,
        args=(
            path,
            request.referrer or "",
            user_agent,
            ip_hash,
            client_ip,
            utm_source,
            utm_campaign,
        ),
        daemon=True,
    ).start()


@app.url_defaults
def add_static_version(endpoint, values):
    """Cache-busting des assets statiques : ajoute ?v=<mtime> à chaque URL static.

    Les statiques sont servis en `immutable` pendant 1 an (perf), donc sans ce
    paramètre le navigateur garde l'ANCIEN CSS/JS en cache et ne revoit jamais une
    correction (ex. le responsive) — sauf en navigation privée, qui part sans cache.
    Le mtime change à chaque modif du fichier → nouvelle URL → le navigateur la
    recharge ; les fichiers inchangés gardent leur cache long.
    """
    if endpoint != "static" or "v" in values:
        return
    filename = values.get("filename")
    if not filename:
        return
    try:
        mtime = os.stat(os.path.join(app.static_folder, filename)).st_mtime
        values["v"] = int(mtime)
    except OSError:
        pass


@app.after_request
def add_performance_headers(response):
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    if request.path.startswith("/go/"):
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.context_processor
def inject_globals():
    settings = get_settings()
    lang = get_lang()
    dests = _destinations(lang)
    return {
        "site": app.config,
        "lang": lang,
        "categories": _categories(lang),
        "current_year": datetime.now().year,
        "destinations": dests,
        "destinations_by_region": destinations_by_region(dests, lang, t),
        "itineraries": _itineraries(lang),
        "pillars": pillars.thematic_list(lang, lang_url),
        "pdf": {"PDF_GUIDE": _localized_block(PDF_GUIDE, lang)},
        "newsletter": {"NEWSLETTER": _localized_block(NEWSLETTER, lang)},
        "ga4_id": settings.get("ga4_measurement_id", ""),
        "canonical_url": canonical_for_request(lang),
        "hreflang_urls": hreflang_urls(),
        "switch_lang_url": switch_lang_url(),
        "page_url_in_lang": page_url_in_lang,
        # Valeurs SEO par défaut : garantissent que TOUTE page (même future ou qui
        # oublierait de les passer) expédie des balises meta/OG cohérentes. Les routes
        # qui passent ces kwargs à render_template les remplacent automatiquement.
        "meta_title": f"{config.SITE_NAME} — {config.SITE_TAGLINE_I18N.get(lang, config.SITE_TAGLINE)}",
        "meta_description": config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION),
        "meta_keywords": config.SITE_KEYWORDS_I18N.get(lang, config.SITE_KEYWORDS),
        "og_image": None,
        "legal_contact_email": config.LEGAL_CONTACT_EMAIL,
        "legal_updated": config.LEGAL_UPDATED_I18N.get(lang, config.LEGAL_UPDATED),
        "site_tagline": config.SITE_TAGLINE_I18N.get(lang, config.SITE_TAGLINE),
        "site_description": config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION),
        "site_keywords": config.SITE_KEYWORDS_I18N.get(lang, config.SITE_KEYWORDS),
        "t": t,
        "lang_url": lang_url,
        "html_lang": "en" if lang == "en" else "fr",
        "og_locale": "en_GB" if lang == "en" else "fr_FR",
        "llms_txt_url": config.SITE_URL.rstrip("/") + "/llms.txt",
        "chat_enabled": _chat_enabled(),
    }


def _chat_enabled() -> bool:
    try:
        from admin import chat_service
        return chat_service.is_enabled()
    except Exception:
        return False


@app.template_global()
def seo_faq_from_html(html: str):
    return extract_faq_from_html(html)


@app.template_global()
def seo_breadcrumb(items):
    return breadcrumb_schema(items)


@app.template_global()
def seo_faq(items):
    return faq_schema(items)


@app.template_global()
def seo_item_list(name: str, items: list):
    return item_list_schema(name, items)


@app.template_global()
def seo_organization():
    return organization_schema(get_lang())


@app.template_global()
def seo_website():
    return website_schema(get_lang())


@app.template_global()
def seo_webpage(name=None, description=None, url=None, image=None):
    """Noeud WebPage de la page courante (émis globalement par base.html)."""
    return webpage_schema(name, description, url or canonical_for_request(get_lang()),
                          image, get_lang())


@app.template_global()
def pillar_backlinks(endpoint: str, slug: str | None = None) -> list[dict]:
    """Maillage retour : pilier(s) de silo référençant cette page (contenu → pilier)."""
    return pillars.find_pillars_for(endpoint, slug, get_lang(), lang_url)


@app.template_global()
def geo_faq_items():
    from geo_utils import geo_faq_for_lang
    return geo_faq_for_lang(get_lang())


@app.template_global()
def traveller_reviews():
    from admin.store import localized_reviews
    return localized_reviews(get_lang())


@app.template_global()
def reviews_aggregate():
    from admin.store import get_reviews
    reviews = get_reviews()
    ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
    if not ratings:
        return {"count": 0, "average": 0}
    return {"count": len(ratings), "average": round(sum(ratings) / len(ratings), 1)}


@app.template_global()
def is_article_new(article, days: int = 14) -> bool:
    """Badge « Nouveau » pour les articles publiés récemment."""
    try:
        from datetime import date as date_cls
        pub = date_cls.fromisoformat(str(article.get("date", "")))
        return (date_cls.today() - pub).days <= days
    except (TypeError, ValueError):
        return False


@app.template_global()
def article_image_url(article) -> str:
    return article.get("image") or url_for("static", filename="images/og-default.jpg")


def _variant_exists(static_rel: str) -> bool:
    return (Path(app.static_folder) / static_rel).is_file()


@app.template_global()
def responsive_image(image_url: str, *, card: bool = False) -> dict:
    """src + srcset pour images WebP locales avec variantes -640/-960."""
    fallback = url_for("static", filename="images/og-default.jpg")
    if not image_url:
        return {"src": fallback, "srcset": "", "sizes": ""}
    if image_url.startswith(("http://", "https://")):
        return {"src": image_url, "srcset": "", "sizes": ""}
    if not image_url.endswith(".webp") or "/static/images/" not in image_url:
        return {"src": fallback, "srcset": "", "sizes": ""}

    rel = image_url.removeprefix("/static/")
    full_rel = rel
    stem_rel = rel[:-5]
    parts = []
    for suffix, width in (("-640", 640), ("-960", 960)):
        variant_rel = f"{stem_rel}{suffix}.webp"
        if _variant_exists(variant_rel):
            parts.append(f"/static/{variant_rel} {width}w")
    parts.append(f"{image_url} 1200w")

    sizes = (
        "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 400px"
        if card
        else "100vw"
    )
    best_src = parts[0].split()[0] if len(parts) > 1 else image_url
    return {
        "src": best_src,
        "srcset": ", ".join(parts),
        "sizes": sizes,
    }


@app.template_global()
def affiliate_location(slug: str) -> dict:
    dests = _destinations()
    d = dests.get(slug, {})
    meta = get_location_meta(slug, name=d.get("name"))
    if slug not in LOCATION_META and d.get("location_meta"):
        loc = d["location_meta"]
        for key in ("label", "booking_city", "agoda_city_id", "gyg_location", "viator_dest"):
            val = loc.get(key)
            if val and val != 0:
                meta[key] = val
    return meta


@app.template_global()
def hotel_affiliate_url(hotel: dict, location_slug: str) -> str:
    return build_hotel_link(hotel["provider"], hotel, affiliate_location(location_slug))


@app.template_global()
def activity_affiliate_url(activity: dict, location_slug: str) -> str:
    return build_activity_link(activity["provider"], activity, affiliate_location(location_slug))


@app.template_global()
def gyg_partner_id() -> str:
    from admin.store import get_affiliate_ids, is_configured

    pid = get_affiliate_ids().get("gyg_partner_id", "")
    return pid if is_configured(pid) else ""


@app.template_global()
def viator_widget_config() -> dict:
    from admin.store import get_affiliate_ids, is_configured

    ids = get_affiliate_ids()
    pid = ids.get("viator_pid", "")
    ref = ids.get("viator_widget_ref", "")
    if is_configured(pid) and is_configured(ref):
        return {"pid": pid, "ref": ref}
    return {}


@app.template_global()
def tracked_affiliate_url(provider: str, target_url: str) -> str:
    if target_url.startswith("#"):
        return target_url
    return url_for("affiliate_redirect", provider=provider) + "?to=" + quote(target_url, safe="")


@app.template_global()
def esim_airalo_url() -> str:
    return tracked_affiliate_url("esim_airalo", esim_airalo())


@app.template_global()
def esim_holafly_url() -> str:
    return tracked_affiliate_url("esim_holafly", esim_holafly())


@app.template_global()
def travel_insurance_url() -> str:
    return tracked_affiliate_url("travel_insurance", travel_insurance())


@app.template_global()
def transport_12go_url() -> str:
    return tracked_affiliate_url("transport_12go", transport_12go())


@app.template_global()
def visa_ivisa_url() -> str:
    return tracked_affiliate_url("visa_ivisa", visa_ivisa())


@app.template_global()
def pdf_checkout_url() -> str:
    from admin.pdf_payment_service import is_payment_configured
    if is_payment_configured():
        return config.pdf_flow_base_url() + lang_url("pdf_checkout")
    url = pdf_checkout()
    if url.startswith("#"):
        return url
    return tracked_affiliate_url("pdf", url)


@app.route("/go/<provider>")
def affiliate_redirect(provider):
    from admin.analytics_filters import analytics_ip_hash, should_track_affiliate_click

    target = request.args.get("to", "")
    if not target or not target.startswith("http"):
        abort(404)
    client_ip = (request.remote_addr or "").strip()
    user_agent = (request.user_agent.string or "")[:200]
    if should_track_affiliate_click(
        user_agent=user_agent,
        client_ip=client_ip,
        referrer=request.referrer or "",
        host=request.host or "",
    ):
        analytics_db.log_affiliate_click(
            provider,
            target,
            request.referrer or "",
            user_agent=user_agent,
            ip_hash=analytics_ip_hash(client_ip),
        )
    return redirect(target)


# ── Carte interactive (points affiliés) ───────────────────────────────

@app.route("/api/map/<slug>.json")
def api_map_points(slug):
    from flask import jsonify
    from admin import map_service

    lang = get_lang()
    dest = _destinations(lang).get(slug)
    if not dest:
        return jsonify({"ok": False, "error": "Not found"}), 404
    points = map_service.get_public_map_points(slug, lang, tracked_affiliate_url)
    legend = map_service.legend_for_kinds([p["kind"] for p in points], lang)
    return jsonify({"ok": True, "destination": slug, "name": dest.get("name", slug), "points": points, "legend": legend})


# ── Homepage ──────────────────────────────────────────────────────────

@app.route("/")
@app.route("/en/")
@app.route("/en")
def index():
    lang = get_lang()
    articles = _articles(lang)
    featured_articles = [a for a in articles if a.get("featured")]
    return render_template(
        "index.html",
        featured_articles=featured_articles,
        meta_title=t("meta.home.title", lang),
        meta_description=t("meta.home.desc", lang),
        meta_keywords=t("meta.home.kw", lang),
    )


# ── Préparer mon voyage ───────────────────────────────────────────────

@app.route("/preparer-mon-voyage")
@app.route("/en/plan-my-trip")
def prepare_trip():
    from data.trip_planner import build_planner_catalog
    from locales.ui import t as ui_t

    lang = get_lang()
    catalog = build_planner_catalog(
        lang,
        articles=_articles(lang),
        itineraries=_itineraries(lang),
        destinations=_destinations(lang),
        categories=_categories(lang),
        lang_url_fn=lang_url,
        t_fn=ui_t,
        track_url_fn=tracked_affiliate_url,
    )
    return render_template(
        "prepare_trip.html",
        planner_catalog=catalog,
        meta_title=ui_t("meta.prepare.title", lang),
        meta_description=ui_t("meta.prepare.desc", lang),
    )


# ── Outils voyageurs ──────────────────────────────────────────────────

@app.route("/quand-partir-au-vietnam")
@app.route("/en/best-time-to-visit-vietnam")
def best_season():
    from data.travel_tools import build_seasons

    lang = get_lang()
    return render_template(
        "tools/best_season.html",
        seasons=build_seasons(lang),
        meta_title=t("meta.season.title", lang),
        meta_description=t("meta.season.desc", lang),
        meta_keywords="meilleure saison Vietnam, quand partir Vietnam, météo Vietnam"
        if lang == "fr"
        else "best time Vietnam, when to visit Vietnam, Vietnam weather",
    )


@app.route("/api/fx-rates")
@app.route("/en/api/fx-rates")
def api_fx_rates():
    from flask import jsonify
    from data.fx_rates import get_fx_rates

    rates = get_fx_rates()
    return jsonify({"ok": True, **rates})


@app.route("/calculateur-budget-vietnam")
@app.route("/en/vietnam-budget-calculator")
def budget_tool():
    from data.travel_tools import build_budget

    lang = get_lang()
    return render_template(
        "tools/budget.html",
        budget=build_budget(lang),
        meta_title=t("meta.budget.title", lang),
        meta_description=t("meta.budget.desc", lang),
        meta_keywords="budget voyage Vietnam, coût voyage Vietnam, prix Vietnam"
        if lang == "fr"
        else "Vietnam travel budget, Vietnam trip cost, Vietnam prices",
    )


@app.route("/visa-vietnam")
@app.route("/en/vietnam-visa")
def visa_tool():
    from data.travel_tools import build_visa

    lang = get_lang()
    return render_template(
        "tools/visa.html",
        visa=build_visa(lang),
        meta_title=t("meta.visa.title", lang),
        meta_description=t("meta.visa.desc", lang),
        meta_keywords="visa Vietnam, e-visa Vietnam, exemption visa Vietnam"
        if lang == "fr"
        else "Vietnam visa, Vietnam e-visa, Vietnam visa exemption",
    )


@app.route("/esim-assurance-vietnam")
@app.route("/en/esim-insurance-vietnam")
def essentials_tool():
    from data.travel_tools import build_comparators

    lang = get_lang()
    return render_template(
        "tools/essentials.html",
        compare=build_comparators(lang),
        meta_title=t("meta.essentials.title", lang),
        meta_description=t("meta.essentials.desc", lang),
        meta_keywords="eSIM Vietnam, assurance voyage Vietnam, Airalo Holafly"
        if lang == "fr"
        else "Vietnam eSIM, Vietnam travel insurance, Airalo Holafly",
    )


# ── Applications utiles (guide anti-arnaque) ──────────────────────────

@app.route("/applications-utiles-vietnam")
@app.route("/en/useful-apps-vietnam")
def useful_apps():
    from data.vietnam_apps import app_categories, app_faq

    lang = get_lang()
    return render_template(
        "apps.html",
        app_cats=app_categories(lang),
        apps_faq=app_faq(lang),
        meta_title=t("meta.apps.title", lang),
        meta_description=t("meta.apps.desc", lang),
        meta_keywords="applications Vietnam, Grab Vietnam, apps voyage Vietnam, éviter arnaques Vietnam"
        if lang == "fr"
        else "Vietnam apps, Grab Vietnam, travel apps Vietnam, avoid scams Vietnam",
        og_image="/static/images/pool/1521993117367-b7f70ccd029d.webp",
    )


# ── Guides pratiques (sécurité, coutumes, phrases) ───────────────────

@app.route("/securite-voyage-vietnam")
@app.route("/en/vietnam-travel-safety")
def safety_guide():
    from data.travel_guides import build_safety_guide

    lang = get_lang()
    return render_template(
        "tools/safety.html",
        guide=build_safety_guide(lang),
        meta_title=t("meta.safety.title", lang),
        meta_description=t("meta.safety.desc", lang),
        meta_keywords=t("meta.safety.kw", lang),
        og_image="/static/images/pool/1528127269322-539801943592.webp",
    )


@app.route("/coutumes-vietnam")
@app.route("/en/vietnam-customs-etiquette")
def customs_guide():
    from data.travel_guides import build_customs_guide

    lang = get_lang()
    return render_template(
        "tools/customs.html",
        guide=build_customs_guide(lang),
        meta_title=t("meta.customs.title", lang),
        meta_description=t("meta.customs.desc", lang),
        meta_keywords=t("meta.customs.kw", lang),
        og_image="/static/images/pool/1557750255-c76072a7aad1.webp",
    )


@app.route("/phrases-utiles-vietnamien")
@app.route("/en/useful-vietnamese-phrases")
def phrases_guide():
    from data.travel_guides import build_phrases_guide

    lang = get_lang()
    return render_template(
        "tools/phrases.html",
        guide=build_phrases_guide(lang),
        meta_title=t("meta.phrases.title", lang),
        meta_description=t("meta.phrases.desc", lang),
        meta_keywords=t("meta.phrases.kw", lang),
        og_image="/static/images/pool/1531737212413-667205e1cda7.webp",
    )


# ── Blog ──────────────────────────────────────────────────────────────

@app.route("/blog")
@app.route("/en/blog")
def blog_index():
    lang = get_lang()
    posts = sorted(_articles(lang), key=lambda a: a["date"], reverse=True)
    return render_template(
        "blog_index.html",
        articles=posts,
        meta_title=t("meta.blog.title", lang),
        meta_description=t("meta.blog.desc", lang),
        meta_keywords=t("meta.blog.kw", lang),
    )


@app.route("/blog/<slug>")
@app.route("/en/blog/<slug>")
def article(slug):
    lang = get_lang()
    post = get_article_by_slug(slug, lang)
    if not post:
        abort(404)
    # Repli image : si le fichier (FS éphémère) a disparu après un redéploiement, on
    # bascule sur la photo du pool (commitée) — corrige les articles générés avant le fix.
    post["image"] = persistent_image_url(post.get("image"), post.get("image_photo_id"), post.get("image_source_url"))
    articles = _articles(lang)
    related = [a for a in articles if a["category"] == post["category"] and a["slug"] != slug][:3]
    return render_template(
        "article.html",
        article=post,
        related=related,
        meta_title=article_meta_title(post),
        meta_description=article_meta_description(post, lang),
        meta_keywords=", ".join(post.get("tags", [])[:10]),
        og_image=post.get("image"),
    )


@app.route("/categorie/<category>")
@app.route("/en/category/<category>")
def category(category):
    lang = get_lang()
    cats = _categories(lang)
    if category not in cats:
        abort(404)
    articles = [a for a in _articles(lang) if a["category"] == category]
    cat = cats[category]
    return render_template(
        "category.html",
        category_key=category,
        category=cat,
        articles=articles,
        meta_title=f"{cat['label']} Vietnam {t('meta.category.suffix', lang)}",
        meta_description=truncate_text(
            f"{cat['description']} {t('meta.category.desc_extra', lang)}",
            160,
        ),
        meta_keywords=f"{cat['label']}, Vietnam travel, Vietnam guide",
    )


# ── Itineraries ───────────────────────────────────────────────────────

@app.route("/itineraries/<slug>")
@app.route("/en/itineraries/<slug>")
def itinerary(slug):
    lang = get_lang()
    all_itins = _itineraries(lang)
    itin = all_itins.get(slug)
    if not itin:
        abort(404)
    # Maillage interne : les autres durées (3/7/10/15 jours) en bas de page.
    other_itins = [
        {"slug": s, "title": it["title"], "duration": it["duration"],
         "summary": it.get("summary", ""), "budget_hint": it.get("budget_hint", "")}
        for s, it in all_itins.items() if s != slug
    ]
    return render_template(
        "itinerary.html",
        itin=itin,
        slug=slug,
        other_itins=other_itins,
        meta_title=itin["meta_title"],
        meta_description=itin["meta_description"],
        meta_keywords=t("meta.itin.kw", lang, days=str(itin["duration"])),
        og_image=itin.get("hero_image"),
    )


@app.route("/itineraries/<slug>/guide", methods=["POST"])
@app.route("/en/itineraries/<slug>/guide", methods=["POST"])
def itinerary_guide_subscribe(slug):
    """Inscription newsletter → lien de téléchargement PDF itinéraire."""
    from urllib.parse import quote

    from admin.itinerary_download_tokens import make_itinerary_download_token
    from admin.newsletter_service import add_newsletter_subscriber

    lang = get_lang()
    if slug not in ITINERARIES:
        abort(404)
    back = lang_url("itinerary", lang, slug=slug) + "#guide-pdf"

    if not request.form.get("consent_rgpd"):
        flash(t("flash.consent", lang), "error")
        return redirect(back)

    email = (request.form.get("email") or "").strip().lower()
    if not email or "@" not in email:
        flash(t("flash.invalid_email", lang), "error")
        return redirect(back)

    add_newsletter_subscriber(email)
    token = make_itinerary_download_token(email, slug)
    download_path = lang_url("itinerary_guide_download", lang, slug=slug, token=token)
    flash(t("itin.guide.success", lang), "success")
    return redirect(f"{download_path}?email={quote(email)}")


@app.route("/itineraries/<slug>/guide/<token>")
@app.route("/en/itineraries/<slug>/guide/<token>")
def itinerary_guide_download(slug, token):
    from flask import Response

    from admin.itinerary_download_tokens import verify_itinerary_download_token
    from admin.itinerary_pdf_service import generate_itinerary_pdf_bytes, itinerary_pdf_filename

    lang = get_lang()
    if slug not in ITINERARIES:
        abort(404)

    email = (request.args.get("email") or "").strip().lower()
    if not verify_itinerary_download_token(email, slug, token):
        abort(403)

    try:
        pdf_bytes = generate_itinerary_pdf_bytes(slug, lang)
    except ValueError:
        abort(404)

    filename = itinerary_pdf_filename(slug, lang)
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Static pages ──────────────────────────────────────────────────────

@app.route("/politique-confidentialite")
@app.route("/en/privacy")
def privacy():
    lang = get_lang()
    return render_template(
        "privacy.html",
        meta_title=t("meta.privacy.title", lang),
        meta_description=t("meta.privacy.desc", lang),
        meta_keywords="RGPD, privacy, cookies, newsletter Vietnam" if lang == "en" else "RGPD, confidentialité, cookies, newsletter Vietnam",
    )


@app.route("/mentions-legales")
@app.route("/en/legal")
def legal_notices():
    lang = get_lang()
    return render_template(
        "legal.html",
        meta_title=t("meta.legal.title", lang),
        meta_description=t("meta.legal.desc", lang),
        meta_keywords="legal notice, Inside Vietnam Travel" if lang == "en" else "mentions légales, Inside Vietnam Travel",
    )


@app.route("/a-propos")
@app.route("/en/about")
def about():
    lang = get_lang()
    return render_template(
        "about.html",
        meta_title=t("meta.about.title", lang),
        meta_description=t("meta.about.desc", lang),
        meta_keywords="independent Vietnam guide, Inside Vietnam Travel" if lang == "en" else "guide Vietnam indépendant, Inside Vietnam Travel, voyage Vietnam",
    )


@app.route("/contact", methods=["GET", "POST"])
@app.route("/en/contact", methods=["GET", "POST"])
def contact():
    from admin.contact_service import submit_contact_form

    lang = get_lang()
    if request.method == "POST":
        if request.form.get("website"):
            return redirect(lang_url("contact", lang))
        try:
            if not request.form.get("consent_rgpd"):
                raise ValueError(t("flash.consent", lang))
            submit_contact_form(
                name=request.form.get("name", ""),
                email=request.form.get("email", ""),
                subject=request.form.get("subject", ""),
                message=request.form.get("message", ""),
                lang=lang,
            )
            flash(t("contact.success", lang), "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception:
            flash(t("contact.error", lang), "error")
        return redirect(lang_url("contact", lang))

    return render_template(
        "contact.html",
        meta_title=t("meta.contact.title", lang),
        meta_description=t("meta.contact.desc", lang),
        meta_keywords="contact Vietnam travel, Inside Vietnam Travel" if lang == "en" else "contact voyage Vietnam, Inside Vietnam Travel",
    )


@app.route("/newsletter/desinscription", methods=["GET", "POST"])
@app.route("/en/newsletter/unsubscribe", methods=["GET", "POST"])
def newsletter_unsubscribe():
    from admin.newsletter_service import remove_newsletter_subscriber
    from admin.newsletter_tokens import verify_unsubscribe_token

    lang = get_lang()
    email = (request.form.get("email") or request.args.get("email") or "").strip().lower()
    token = (request.form.get("token") or request.args.get("token") or "").strip()

    if request.method == "POST":
        if not verify_unsubscribe_token(email, token):
            return render_template(
                "newsletter_unsubscribe.html",
                error=t("unsub.invalid", lang),
                meta_title=t("unsub.confirm_title", lang),
                meta_description=t("meta.privacy.desc", lang),
            ), 400
        remove_newsletter_subscriber(email)
        return render_template(
            "newsletter_unsubscribe.html",
            success=True,
            email=email,
            meta_title=t("unsub.success", lang),
            meta_description=t("unsub.success", lang),
        )

    if email and token:
        if not verify_unsubscribe_token(email, token):
            return render_template(
                "newsletter_unsubscribe.html",
                error=t("unsub.invalid_short", lang),
                meta_title=t("unsub.confirm_title", lang),
                meta_description=t("meta.privacy.desc", lang),
            ), 400
        return render_template(
            "newsletter_unsubscribe.html",
            email=email,
            token=token,
            meta_title=t("unsub.confirm_title", lang),
            meta_description=t("meta.privacy.desc", lang),
        )

    return render_template(
        "newsletter_unsubscribe.html",
        error=t("unsub.incomplete", lang),
        meta_title=t("unsub.confirm_title", lang),
        meta_description=t("meta.privacy.desc", lang),
    ), 400


@app.route("/newsletter", methods=["POST"])
@app.route("/en/newsletter", methods=["POST"])
def newsletter_subscribe():
    from admin.newsletter_service import add_newsletter_subscriber

    lang = get_lang()
    if not request.form.get("consent_rgpd"):
        flash(t("flash.consent", lang), "error")
        return redirect(request.referrer or lang_url("index", lang))

    email = (request.form.get("email") or "").strip().lower()
    if email and "@" in email:
        if add_newsletter_subscriber(email):
            flash(t("flash.subscribed", lang), "success")
        else:
            flash(t("flash.already", lang), "success")
    else:
        flash(t("flash.invalid_email", lang), "error")
    return redirect(request.referrer or lang_url("index", lang))


# ── Guide PDF (achat + téléchargement) ───────────────────────────────────

@app.route("/guide-pdf/checkout")
@app.route("/en/guide-pdf/checkout")
def pdf_checkout_start():
    from admin.pdf_payment_service import create_checkout_session, is_payment_configured

    lang = get_lang()
    if not is_payment_configured():
        flash(t("pdf.error.payment", lang), "error")
        return redirect(lang_url("index", lang) + "#pdf-guide")

    base = config.pdf_flow_base_url()
    success_url = base + lang_url("pdf_success", lang) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = base + lang_url("index", lang) + "#pdf-guide"
    result = create_checkout_session(lang=lang, success_url=success_url, cancel_url=cancel_url)
    if not result.get("ok"):
        flash(t("pdf.error.payment", lang), "error")
        return redirect(lang_url("index", lang) + "#pdf-guide")

    from admin.analytics_filters import analytics_ip_hash, should_track_affiliate_click

    client_ip = (request.remote_addr or "").strip()
    user_agent = (request.user_agent.string or "")[:200]
    if should_track_affiliate_click(user_agent=user_agent, client_ip=client_ip):
        analytics_db.log_affiliate_click(
            "pdf",
            result.get("url", ""),
            request.referrer or "",
            user_agent=user_agent,
            ip_hash=analytics_ip_hash(client_ip),
        )
    return redirect(result["url"])


@app.route("/guide-pdf/merci")
@app.route("/en/guide-pdf/success")
def pdf_success():
    from admin.pdf_guide_service import pdf_filename
    from admin.pdf_payment_service import (
        build_download_url,
        fulfill_checkout_session,
        notify_purchase_fulfilled,
    )

    lang = get_lang()
    session_id = (request.args.get("session_id") or "").strip()
    download_url = ""
    pdf_lang = lang
    if session_id:
        result = fulfill_checkout_session(session_id)
        if result.get("ok"):
            token = result["token"]
            pdf_lang = result.get("lang", lang)
            download_url = build_download_url(token, pdf_lang)
            if not result.get("already"):
                notify_purchase_fulfilled(
                    token=token,
                    email=result.get("email", ""),
                    lang=result.get("lang", lang),
                )

    return render_template(
        "pdf_success.html",
        download_url=download_url,
        pdf_filename=pdf_filename(pdf_lang),
        meta_title=t("pdf.success.meta_title", lang),
        meta_description=t("pdf.success.meta_desc", lang),
        meta_robots="noindex, nofollow",
    )


@app.route("/guide-pdf/telecharger/<token>")
@app.route("/en/guide-pdf/download/<token>")
def pdf_download(token):
    from admin.pdf_guide_service import generate_pdf_bytes, pdf_filename
    from admin.pdf_payment_service import get_valid_token, record_download

    lang = get_lang()
    record = get_valid_token(token)
    if not record:
        abort(404)
    pdf_lang = record.get("lang", lang)
    data = generate_pdf_bytes(pdf_lang)
    record_download(token)
    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{pdf_filename(pdf_lang)}"',
            "Cache-Control": "private, no-store",
        },
    )


# ── Guides piliers (silos thématiques SEO) ──────────────────────────────

@app.route("/guide/<slug>")
@app.route("/en/guide/<slug>")
def pillar(slug):
    lang = get_lang()
    found = pillars.hub_by_slug(slug)
    if not found:
        abort(404)
    key, raw = found
    p = pillars.localize_hub(key, raw, lang, lang_url)
    return render_template(
        "pillar.html",
        pillar=p,
        meta_title=p["meta_title"],
        meta_description=p["meta_description"],
        meta_keywords=f"{p['title']}, Vietnam, voyage Vietnam, guide Vietnam",
        og_image=(f"/static/images/pool/{p.get('photo_id')}.webp" if p.get("photo_id") else None),
    )


# ── Destinations (route dynamique — en dernier) ─────────────────────────

@app.route("/<slug>")
@app.route("/en/<slug>")
def destination_page(slug):
    if slug in RESERVED_SLUGS:
        abort(404)
    lang = get_lang()
    dest = _destinations(lang).get(slug)
    if not dest:
        abort(404)
    return render_template(
        "destination.html",
        dest=dest,
        meta_title=dest.get("meta_title") or build_meta_title(f"Guide {dest['name']} Vietnam"),
        meta_description=truncate_text(dest.get("meta_description", ""), 160),
        meta_keywords=t("meta.dest.kw", lang, name=dest["name"]),
        og_image=dest.get("image"),
    )


# ── Recherche (index client) ──────────────────────────────────────────

@app.route("/search-index.json")
def search_index():
    from flask import jsonify

    lang = "en" if (request.args.get("lang") == "en") else "fr"
    items = []

    for slug, d in _destinations(lang).items():
        items.append({
            "t": d.get("name", slug),
            "s": d.get("tagline", ""),
            "u": lang_url("destination_page", lang, slug=slug),
            "g": "destination",
        })
        loc = affiliate_location(slug)
        dest_name = d.get("name", slug)
        # Hôtels — uniquement des liens affiliés trackés (Booking / Agoda).
        for hotel in (d.get("hotels") or []):
            provider = hotel.get("provider")
            if not provider:
                continue
            price = hotel.get("price_hint", "")
            items.append({
                "t": hotel.get("name", ""),
                "s": f"{dest_name} · {price}".strip(" ·"),
                "u": tracked_affiliate_url(provider, build_hotel_link(provider, hotel, loc)),
                "g": "hotel",
                "x": 1,
            })
        # Activités & tours — liens affiliés trackés (GetYourGuide / Viator).
        for act in (d.get("activities") or []):
            provider = act.get("provider")
            if not provider:
                continue
            price = act.get("price_hint", "")
            items.append({
                "t": act.get("name", ""),
                "s": f"{dest_name} · {price}".strip(" ·"),
                "u": tracked_affiliate_url(provider, build_activity_link(provider, act, loc)),
                "g": "activity",
                "x": 1,
            })
    for slug, it in _itineraries(lang).items():
        items.append({
            "t": it.get("title", slug),
            "s": it.get("summary", ""),
            "u": lang_url("itinerary", lang, slug=slug),
            "g": "itinerary",
        })
    for a in _articles(lang):
        items.append({
            "t": a.get("title", ""),
            "s": a.get("excerpt", ""),
            "u": lang_url("article", lang, slug=a["slug"]),
            "g": "article",
        })
    for endpoint, key in (
        ("best_season", "tools.season"),
        ("budget_tool", "tools.budget"),
        ("visa_tool", "tools.visa"),
        ("essentials_tool", "tools.essentials"),
        ("useful_apps", "tools.apps"),
        ("safety_guide", "safety.nav"),
        ("customs_guide", "customs.nav"),
        ("phrases_guide", "phrases.nav"),
        ("prepare_trip", "nav.prepare"),
    ):
        items.append({
            "t": t(key, lang),
            "s": "",
            "u": lang_url(endpoint, lang),
            "g": "tool",
        })

    return jsonify(items)


@app.route("/api/visitor-recommendations")
@app.route("/en/api/visitor-recommendations")
def api_visitor_recommendations():
    from flask import jsonify
    from data.visitor_profile import (
        PROFILE_COOKIE,
        mai_suggestions,
        parse_cookie,
        resolve_from_profile,
    )

    lang = get_lang()
    profile = parse_cookie(request.cookies.get(PROFILE_COOKIE))
    if not profile:
        return jsonify({
            "ok": True,
            "personalized": False,
            "suggestions": mai_suggestions(None, lang, t),
        })

    rec = resolve_from_profile(
        profile,
        lang,
        destinations=_destinations(lang),
        itineraries=_itineraries(lang),
        articles=_articles(lang),
        categories=_categories(lang),
        lang_url_fn=lang_url,
        t_fn=t,
    )
    rec["ok"] = True
    rec["suggestions"] = mai_suggestions(profile, lang, t)
    return jsonify(rec)


@app.route("/api/visitor-profile/sync", methods=["POST"])
@app.route("/en/api/visitor-profile/sync", methods=["POST"])
def api_visitor_profile_sync():
    from flask import jsonify
    from data.visitor_profile import hash_visitor_id, parse_cookie, PROFILE_COOKIE

    profile = parse_cookie(request.cookies.get(PROFILE_COOKIE))
    payload = request.get_json(silent=True) or {}
    if not profile and not payload.get("id"):
        return jsonify({"ok": False, "error": "no profile"}), 400

    vid = (profile or {}).get("id") or payload.get("id") or ""
    visitor_hash = hash_visitor_id(str(vid))
    if not visitor_hash:
        return jsonify({"ok": False}), 400

    cities = payload.get("c") or (profile or {}).get("c") or []
    interests = payload.get("i") or (profile or {}).get("i") or []
    try:
        analytics_db.log_visitor_profile_snapshot(
            visitor_hash=visitor_hash,
            trip_group=str(payload.get("g") or (profile or {}).get("g") or "")[:20],
            trip_style=str(payload.get("s") or (profile or {}).get("s") or "")[:20],
            trip_duration=str(payload.get("d") or (profile or {}).get("d") or "")[:20],
            cities=",".join(cities[:8])[:200],
            interests=",".join(interests[:12])[:300],
            path=str(payload.get("path") or request.path or "")[:300],
        )
    except Exception:
        pass
    return jsonify({"ok": True})


# ── Chat IA (Mai) ─────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    from flask import jsonify
    from admin import chat_service

    if not chat_service.is_enabled():
        return jsonify({"ok": False, "error": "Chat indisponible."}), 503

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    lang = "en" if payload.get("lang") == "en" else get_lang()
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    # Photos déjà affichées dans la conversation (le front les renvoie) :
    # Mai ne montre jamais deux fois la même image.
    raw_seen = payload.get("seen_photos")
    seen_photos = [
        u.strip()[:500] for u in raw_seen if isinstance(u, str) and u.strip()
    ][:60] if isinstance(raw_seen, list) else []

    from data.visitor_profile import PROFILE_COOKIE, parse_cookie
    visitor_profile = parse_cookie(request.cookies.get(PROFILE_COOKIE))
    if not visitor_profile and isinstance(payload.get("profile"), dict):
        from data.visitor_profile import normalize_profile
        visitor_profile = normalize_profile(payload["profile"])

    try:
        result = chat_service.chat_reply(
            message,
            history,
            lang,
            client_ip=(request.remote_addr or "").strip(),
            track_url_fn=tracked_affiliate_url,
            visitor_profile=visitor_profile,
            seen_photo_urls=seen_photos,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        from admin import ai_client
        return jsonify({"ok": False, "error": ai_client.friendly_error(exc)}), 502

    return jsonify(result)


@app.route("/en/api/chat", methods=["POST"])
def api_chat_en():
    return api_chat()


# ── SEO ───────────────────────────────────────────────────────────────

@app.route("/AgodaPartnerVerification.htm")
def agoda_partner_verification():
    """Vérification domaine Agoda Partners (méthode fichier HTML)."""
    body = (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        "<title>Agoda Partner Site Verification</title></head><body>"
        "agoda-partner-site-verification: AgodaPartnerVerification.html"
        "</body></html>"
    )
    return Response(body, mimetype="text/html; charset=utf-8")


@app.route("/robots.txt")
def robots():
    from geo_utils import render_robots_txt
    return Response(render_robots_txt(), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    xml = render_sitemap_xml()
    return Response(xml, mimetype="application/xml")


@app.route("/llms.txt")
def llms_txt():
    from geo_utils import render_llms_txt
    return Response(render_llms_txt(full=False), mimetype="text/plain; charset=utf-8")


@app.route("/llms-full.txt")
def llms_full_txt():
    from geo_utils import render_llms_txt
    return Response(render_llms_txt(full=True), mimetype="text/plain; charset=utf-8")


@app.errorhandler(404)
def not_found(e):
    lang = get_lang()
    return render_template(
        "404.html",
        meta_title=t("meta.404.title", lang),
        meta_description=t("meta.404.desc", lang),
    ), 404


def _startup_tasks():
    from admin.image_service import ensure_responsive_variants, sync_destination_images

    ensure_responsive_variants()
    try:
        sync_destination_images(allow_network=False)
    except Exception:
        pass
    try:
        from admin import map_service
        if not map_service.get_map_store().get("points"):
            map_service.defer_sync_all()
    except Exception:
        pass


threading.Thread(target=_startup_tasks, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
