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
    "robots.txt", "sitemap.xml", "categorie", "static", "favicon.ico",
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

NEWSLETTER_FILE = Path(__file__).parent / "data" / "newsletter_subscribers.txt"

analytics_db.init_db()


def _articles():
    return get_articles()


def _categories():
    return get_categories()


def _destinations():
    return get_destinations_dict()


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
def track_page_view():
    if request.method != "GET":
        return
    path = request.path
    if path.startswith(("/admin", "/static", "/go/", "/favicon")):
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
    canonical = config.SITE_URL.rstrip("/") + (request.path if request.path != "/" else "")
    return {
        "site": app.config,
        "categories": _categories(),
        "current_year": datetime.now().year,
        "destinations": _destinations(),
        "itineraries": ITINERARIES,
        "pdf": {"PDF_GUIDE": PDF_GUIDE},
        "newsletter": {"NEWSLETTER": NEWSLETTER},
        "ga4_id": settings.get("ga4_measurement_id", ""),
        "canonical_url": canonical,
        "meta_keywords": None,
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
    return organization_schema()


@app.template_global()
def seo_website():
    return website_schema()


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
    url = pdf_checkout()
    if url.startswith("#"):
        return url
    return tracked_affiliate_url("pdf", url)


@app.route("/go/<provider>")
def affiliate_redirect(provider):
    target = request.args.get("to", "")
    if not target or not target.startswith("http"):
        abort(404)
    analytics_db.log_affiliate_click(provider, target, request.referrer or "")
    return redirect(target)


# ── Homepage ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    articles = _articles()
    featured_articles = [a for a in articles if a.get("featured")]
    return render_template(
        "index.html",
        featured_articles=featured_articles,
        meta_title="Voyage Vietnam 2026 : guides, itinéraires et conseils pratiques",
        meta_description=(
            "Préparez votre voyage au Vietnam : itinéraires 3 à 10 jours, guides Hanoï, "
            "Hội An, Saigon, visa, budget et conseils pour voyageurs français."
        ),
        meta_keywords="voyage Vietnam, guide Vietnam, itinéraire Vietnam, préparer voyage Vietnam, voyageurs français",
    )


# ── Blog ──────────────────────────────────────────────────────────────

@app.route("/blog")
def blog_index():
    posts = sorted(_articles(), key=lambda a: a["date"], reverse=True)
    return render_template(
        "blog_index.html",
        articles=posts,
        meta_title="Blog voyage Vietnam : visa, budget, transport, gastronomie",
        meta_description=(
            "Articles pratiques pour préparer un voyage au Vietnam : e-visa, budget au jour, "
            "eSIM, sécurité, transport et street food. Conseils pour voyageurs français."
        ),
        meta_keywords="blog voyage Vietnam, visa Vietnam, budget Vietnam, conseils voyage Vietnam",
    )


@app.route("/blog/<slug>")
def article(slug):
    post = get_article_by_slug(slug)
    if not post:
        abort(404)
    articles = _articles()
    related = [a for a in articles if a["category"] == post["category"] and a["slug"] != slug][:3]
    return render_template(
        "article.html",
        article=post,
        related=related,
        meta_title=article_meta_title(post),
        meta_description=article_meta_description(post),
        meta_keywords=", ".join(post.get("tags", [])[:10]),
    )


@app.route("/categorie/<category>")
def category(category):
    cats = _categories()
    if category not in cats:
        abort(404)
    articles = [a for a in _articles() if a["category"] == category]
    cat = cats[category]
    return render_template(
        "category.html",
        category_key=category,
        category=cat,
        articles=articles,
        meta_title=f"{cat['label']} Vietnam — guides pratiques voyage",
        meta_description=truncate_text(
            f"{cat['description']} Conseils pour voyageurs français préparant un séjour au Vietnam.",
            160,
        ),
        meta_keywords=f"{cat['label']}, voyage Vietnam, guide Vietnam",
    )


# ── Itineraries ───────────────────────────────────────────────────────

@app.route("/itineraries/<slug>")
def itinerary(slug):
    itin = ITINERARIES.get(slug)
    if not itin:
        abort(404)
    return render_template(
        "itinerary.html",
        itin=itin,
        slug=slug,
        meta_title=itin["meta_title"],
        meta_description=itin["meta_description"],
        meta_keywords=f"itinéraire Vietnam {itin['duration']} jours, voyage Vietnam, circuit Vietnam",
    )


# ── Static pages ──────────────────────────────────────────────────────

@app.route("/a-propos")
def about():
    return render_template(
        "about.html",
        meta_title="À propos — guide voyage Vietnam indépendant",
        meta_description=(
            "Inside Vietnam Travel : guide indépendant pour préparer votre voyage au Vietnam. "
            "Itinéraires, conseils pratiques et transparence sur les liens affiliés."
        ),
        meta_keywords="guide Vietnam indépendant, Inside Vietnam Travel, voyage Vietnam",
    )


@app.route("/newsletter", methods=["POST"])
def newsletter_subscribe():
    from admin.newsletter_service import add_newsletter_subscriber
    email = (request.form.get("email") or "").strip().lower()
    if email and "@" in email:
        if add_newsletter_subscriber(email):
            flash("Merci ! Vous êtes inscrit à la newsletter.", "success")
        else:
            flash("Cette adresse est déjà inscrite.", "success")
    else:
        flash("Veuillez entrer une adresse email valide.", "error")
    return redirect(request.referrer or url_for("index"))


# ── Destinations (route dynamique — en dernier) ─────────────────────────

@app.route("/<slug>")
def destination_page(slug):
    if slug in RESERVED_SLUGS:
        abort(404)
    dest = _destinations().get(slug)
    if not dest:
        abort(404)
    return render_template(
        "destination.html",
        dest=dest,
        meta_title=dest.get("meta_title") or build_meta_title(f"Guide {dest['name']} Vietnam"),
        meta_description=truncate_text(dest.get("meta_description", ""), 160),
        meta_keywords=f"guide {dest['name']}, voyage {dest['name']}, que faire {dest['name']}, Vietnam",
    )


# ── SEO ───────────────────────────────────────────────────────────────

@app.route("/robots.txt")
def robots():
    content = f"User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: {config.SITE_URL}/sitemap.xml\n"
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    articles = _articles()
    cats = _categories()
    pages = [
        {"loc": url_for("index", _external=True), "priority": "1.0"},
        {"loc": url_for("blog_index", _external=True), "priority": "0.9"},
        {"loc": url_for("about", _external=True), "priority": "0.5"},
    ]
    for slug in _destinations():
        pages.append({"loc": f"{config.SITE_URL}/{slug}", "priority": "0.9"})
    for slug in ITINERARIES:
        pages.append({
            "loc": url_for("itinerary", slug=slug, _external=True),
            "priority": "0.9",
        })
    for cat in cats:
        pages.append({
            "loc": url_for("category", category=cat, _external=True),
            "priority": "0.7",
        })
    for post in articles:
        pages.append({
            "loc": url_for("article", slug=post["slug"], _external=True),
            "priority": "0.8",
            "lastmod": post["date"],
        })

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        xml += "  <url>\n"
        xml += f"    <loc>{page['loc']}</loc>\n"
        if "lastmod" in page:
            xml += f"    <lastmod>{page['lastmod']}</lastmod>\n"
        xml += f"    <priority>{page['priority']}</priority>\n"
        xml += "  </url>\n"
    xml += "</urlset>"
    return Response(xml, mimetype="application/xml")


@app.errorhandler(404)
def not_found(e):
    return render_template(
        "404.html",
        meta_title="Page introuvable",
        meta_description="Cette page n'existe pas. Retournez à l'accueil pour préparer votre voyage au Vietnam.",
    ), 404


def _startup_tasks():
    from admin.image_service import ensure_responsive_variants
    ensure_responsive_variants()


threading.Thread(target=_startup_tasks, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
