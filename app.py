"""Inside Vietnam Travel — affiliate travel guide (Flask)."""

import hashlib
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
    is_analytics_excluded_ip,
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
    website_schema,
)
from admin import admin_bp
from admin import db as analytics_db
from admin.store import get_articles, get_article_by_slug, get_categories, get_settings, get_destinations_dict
from data.affiliate_urls import (
    LOCATION_META,
    build_activity_link,
    build_hotel_link,
    esim_airalo,
    esim_holafly,
    get_location_meta,
    pdf_checkout,
    travel_insurance,
)
from data.itineraries import ITINERARIES
from data.affiliates import PDF_GUIDE, NEWSLETTER

RESERVED_SLUGS = frozenset({
    "blog", "admin", "go", "itineraries", "a-propos", "newsletter",
    "politique-confidentialite", "mentions-legales",
    "robots.txt", "sitemap.xml", "categorie", "category", "static", "favicon.ico",
    "en", "about", "privacy", "legal", "unsubscribe", "contact", "guide-pdf",
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



def _articles(lang=None):
    return get_articles(lang or get_lang())


def _categories(lang=None):
    return get_categories(lang or get_lang())


def _destinations(lang=None):
    return get_destinations_dict(lang or get_lang())


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


def _log_page_view_async(path: str, referrer: str, user_agent: str, ip_hash: str):
    try:
        analytics_db.log_page_view(
            path=path,
            referrer=referrer,
            user_agent=user_agent,
            ip_hash=ip_hash,
        )
    except Exception:
        pass


@app.before_request
def prepare_request():
    set_lang(detect_lang_from_path())


@app.before_request
def track_page_view():
    if request.method != "GET":
        return
    path = request.path
    if path.startswith(("/admin", "/static", "/go/", "/favicon")):
        return
    if is_analytics_excluded_ip():
        return
    ip_hash = hashlib.sha256(
        (request.remote_addr or "unknown").encode()
    ).hexdigest()[:16]
    threading.Thread(
        target=_log_page_view_async,
        args=(path, request.referrer or "", (request.user_agent.string or "")[:200], ip_hash),
        daemon=True,
    ).start()


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
    return {
        "site": app.config,
        "lang": lang,
        "categories": _categories(lang),
        "current_year": datetime.now().year,
        "destinations": _destinations(lang),
        "itineraries": _itineraries(lang),
        "pdf": {"PDF_GUIDE": _localized_block(PDF_GUIDE, lang)},
        "newsletter": {"NEWSLETTER": _localized_block(NEWSLETTER, lang)},
        "ga4_id": settings.get("ga4_measurement_id", ""),
        "canonical_url": canonical_for_request(lang),
        "hreflang_urls": hreflang_urls(),
        "switch_lang_url": switch_lang_url(),
        "page_url_in_lang": page_url_in_lang,
        "meta_keywords": None,
        "legal_contact_email": config.LEGAL_CONTACT_EMAIL,
        "legal_updated": config.LEGAL_UPDATED_I18N.get(lang, config.LEGAL_UPDATED),
        "site_tagline": config.SITE_TAGLINE_I18N.get(lang, config.SITE_TAGLINE),
        "site_description": config.SITE_DESCRIPTION_I18N.get(lang, config.SITE_DESCRIPTION),
        "site_keywords": config.SITE_KEYWORDS_I18N.get(lang, config.SITE_KEYWORDS),
        "t": t,
        "lang_url": lang_url,
        "html_lang": "en" if lang == "en" else "fr",
        "og_locale": "en_GB" if lang == "en" else "fr_FR",
    }


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
    return article.get("image") or url_for("static", filename="images/og-default.svg")


def _variant_exists(static_rel: str) -> bool:
    return (Path(app.static_folder) / static_rel).is_file()


@app.template_global()
def responsive_image(image_url: str, *, card: bool = False) -> dict:
    """src + srcset pour images WebP locales avec variantes -640/-960."""
    fallback = image_url or url_for("static", filename="images/og-default.svg")
    if not image_url or not image_url.endswith(".webp") or "/static/images/" not in image_url:
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
    target = request.args.get("to", "")
    if not target or not target.startswith("http"):
        abort(404)
    if not is_analytics_excluded_ip():
        analytics_db.log_affiliate_click(provider, target, request.referrer or "")
    return redirect(target)


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
    articles = _articles(lang)
    related = [a for a in articles if a["category"] == post["category"] and a["slug"] != slug][:3]
    return render_template(
        "article.html",
        article=post,
        related=related,
        meta_title=article_meta_title(post),
        meta_description=article_meta_description(post, lang),
        meta_keywords=", ".join(post.get("tags", [])[:10]),
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
    itin = _itineraries(lang).get(slug)
    if not itin:
        abort(404)
    return render_template(
        "itinerary.html",
        itin=itin,
        slug=slug,
        meta_title=itin["meta_title"],
        meta_description=itin["meta_description"],
        meta_keywords=t("meta.itin.kw", lang, days=str(itin["duration"])),
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

    if not is_analytics_excluded_ip():
        analytics_db.log_affiliate_click("pdf", result.get("url", ""), request.referrer or "")
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
    )


# ── SEO ───────────────────────────────────────────────────────────────

@app.route("/robots.txt")
def robots():
    content = f"User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {config.SITE_URL}/sitemap.xml\n"
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    xml = render_sitemap_xml()
    return Response(xml, mimetype="application/xml")


@app.errorhandler(404)
def not_found(e):
    lang = get_lang()
    return render_template(
        "404.html",
        meta_title=t("meta.404.title", lang),
        meta_description=t("meta.404.desc", lang),
    ), 404


def _startup_tasks():
    from admin.image_service import ensure_responsive_variants
    ensure_responsive_variants()


threading.Thread(target=_startup_tasks, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
