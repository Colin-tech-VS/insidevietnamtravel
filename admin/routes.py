"""Routes /admin — dashboard, IA, affiliation, revenus, analytics."""

import json
import os

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify,
)

from admin.auth import check_password, do_login, do_logout, login_required
from admin import db
from admin import ai_client
from admin import groq_ai
from admin import groq_destinations
from admin import groq_newsletter
from admin import draft_store
from admin.image_service import (
    attach_image_to_article,
    attach_image_to_destination,
    sync_destination_images,
    read_uploaded_image_bytes,
    set_uploaded_image_for_article,
    set_uploaded_image_for_destination,
)
from admin.topic_suggestions import get_topic_suggestions
from admin.admin_recommendations import (
    get_dashboard_recommendations,
    get_affiliate_recommendations,
    get_analytics_recommendations,
    get_revenue_recommendations,
)
from data.vietnam_cities import VIETNAM_CITIES, GUIDE_TYPES, ALL_CITY_VALUES
from data.trip_planner import REGION_LABELS_FR, REGION_ORDER, resolve_region
from admin.affiliate_service import build_affiliate_summary, build_site_analytics, compute_estimated_commission
from admin.affiliate_verify import normalize_affiliate_input, parse_viator_embed, verify_affiliate_id
from admin.content_editor import (
    improve_published_article,
    improve_published_destination,
    update_published_image,
    update_published_image_upload,
)
from admin.store import (
    get_settings, save_settings,
    get_affiliate_ids, save_affiliate_ids,
    get_articles, add_article, get_article_by_slug, replace_published_article,
    get_destinations_dict, add_or_update_destination, delete_destination,
    get_destination_by_slug, set_destination_region, find_destination_slug,
    count_newsletter_subscribers,
    add_custom_partner, delete_custom_partner, get_custom_partners,
    save_custom_partners, slugify,
    get_reviews, save_reviews,
    get_categories, add_category, delete_category, category_usage_counts,
)
from data.articles import CATEGORIES as BUILTIN_CATEGORIES
from admin.newsletter_service import (
    get_newsletter_subscribers,
    build_manual_newsletter,
    send_newsletter_email,
    remove_newsletter_subscriber,
    is_smtp_configured,
    render_newsletter_preview,
)
from admin.manual_content import build_manual_article, build_manual_destination
from data.affiliate_partners import PARTNER_BY_KEY

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../templates/admin")


# ── Brouillons serveur ────────────────────────────────────────────────
# Les brouillons (guides, destinations, newsletters) sont stockés côté serveur via
# admin.draft_store : seul un petit token transite dans le cookie de session. Cela
# contourne la limite 4 Ko du cookie ET permet une génération IA en tâche de fond
# (cf. docstring de draft_store) — fini les « Failed to fetch » / timeouts Scalingo.

def _draft_token_key(kind: str) -> str:
    return f"{kind}_draft_token"


def _get_draft(kind: str) -> dict | None:
    return draft_store.get_draft(session.get(_draft_token_key(kind)))


def _store_draft(kind: str, draft: dict) -> None:
    token = draft_store.new_token()
    draft_store.set_draft(token, draft)
    session[_draft_token_key(kind)] = token


def _clear_draft(kind: str) -> None:
    draft_store.clear(session.pop(_draft_token_key(kind), None))


def _start_draft_job(kind: str, fn, initial_phase: str = "Connexion au moteur IA…") -> None:
    token = draft_store.new_token()
    session[_draft_token_key(kind)] = token
    draft_store.start_job(token, fn, ai_client.friendly_error, initial_phase=initial_phase)


def _draft_status(kind: str) -> dict:
    return draft_store.status(session.get(_draft_token_key(kind)))


_CONTENT_JOB_KEY = "content_job_token"


def _start_content_job(fn, *, initial_phase: str = "Traitement en cours…") -> None:
    token = draft_store.new_token()
    session[_CONTENT_JOB_KEY] = token
    draft_store.start_job(token, fn, ai_client.friendly_error, initial_phase=initial_phase)


def _content_job_status() -> dict:
    return draft_store.status(session.get(_CONTENT_JOB_KEY))


def _parse_image_update_request() -> tuple[str, str, str, bytes | None]:
    """Extrait URL, requête Pixabay, alt et éventuellement les octets d'un fichier importé."""
    if request.content_type and "multipart" in request.content_type:
        alt = (request.form.get("alt") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()
        query = (request.form.get("query") or "").strip()
        upload = None
        f = request.files.get("image_file")
        if f and f.filename:
            upload = read_uploaded_image_bytes(f)
        return image_url, query, alt, upload
    data = request.get_json(silent=True) or {}
    return (
        (data.get("image_url") or "").strip(),
        (data.get("query") or "").strip(),
        (data.get("alt") or "").strip(),
        None,
    )


def _apply_form_cover_image(item: dict, *, is_destination: bool = False) -> None:
    """Applique une image importée ou Pixabay au formulaire manuel (priorité : fichier)."""
    f = request.files.get("image_file")
    alt = (request.form.get("image_alt") or request.form.get("alt") or "").strip() or None
    if f and f.filename:
        raw = read_uploaded_image_bytes(f)
        if is_destination:
            item.update(set_uploaded_image_for_destination(item, raw, alt))
        else:
            item.update(set_uploaded_image_for_article(item, raw, alt))
    elif request.form.get("generate_image") == "on":
        if is_destination:
            item.update(attach_image_to_destination(item, None))
        else:
            item.update(attach_image_to_article(item, None))


def _generate_draft(report, topic: str, guide_type: str, city: str) -> dict:
    import time
    article = groq_ai.generate_guide(topic=topic, guide_type=guide_type, city=city, progress=report)
    article["city"] = city
    report("Génération de l'image Vietnam (WebP)…")
    article.update(attach_image_to_article(
        article,
        article.get("image_prompt"),
        image_nonce=int(time.time() * 1000) % 1_000_000,
    ))
    report("Finalisation de l'article…")
    return article


def _improve_draft(report, article: dict, instructions: str) -> dict:
    article = groq_ai.improve_guide(article, instructions, progress=report)
    if article.get("image_prompt"):
        report("Mise à jour de l'image…")
        article.update(attach_image_to_article(article, article.get("image_prompt")))
    report("Finalisation de l'article…")
    return article


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        if check_password(request.form.get("password", "")):
            do_login()
            return redirect(url_for("admin.dashboard"))
        flash("Mot de passe incorrect.", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    do_logout()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    totals = db.get_dashboard_totals()
    revenue = db.get_revenue_stats()
    realtime = db.get_realtime_stats()
    settings = get_settings()
    affiliates = get_affiliate_ids()
    configured = sum(1 for v in affiliates.values() if v and "PLACEHOLDER" not in str(v))

    est_commission = compute_estimated_commission(30)

    return render_template(
        "admin/dashboard.html",
        totals=totals,
        revenue=revenue,
        realtime=realtime,
        articles_count=len(get_articles()),
        subscribers=count_newsletter_subscribers(),
        affiliates_configured=configured,
        affiliates_total=len(affiliates),
        est_commission=est_commission,
        groq_ok=ai_client.is_configured(),
        ai_provider=ai_client.provider(),
        ai_provider_label=ai_client.provider_label(),
        ai_status=ai_client.provider_status(),
        ai_provider_labels=ai_client.PROVIDER_LABELS,
        recommendations=get_dashboard_recommendations(
            groq_ok=ai_client.is_configured(),
            affiliates_configured=configured,
            affiliates_total=len(affiliates),
            articles_count=len(get_articles()),
            totals=totals,
            est_commission=est_commission,
        ),
    )


@admin_bp.route("/settings/ai", methods=["POST"])
@login_required
def settings_ai():
    provider = (request.form.get("ai_provider") or "groq").strip().lower()
    if provider not in ai_client.PROVIDERS:
        provider = "groq"
    save_settings({"ai_provider": provider})
    flash(f"Moteur IA : {ai_client.provider_label(provider)} sélectionné.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/guides", methods=["GET", "POST"])
@login_required
def guides():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "generate":
                city = request.form.get("city", "").strip()
                if not city or city not in ALL_CITY_VALUES:
                    flash("Veuillez sélectionner une ville dans la liste.", "error")
                    return redirect(url_for("admin.guides"))
                article = _generate_draft(
                    topic=request.form.get("topic", ""),
                    guide_type=request.form.get("guide_type", "article blog"),
                    city=city,
                )
                _store_draft("article", article)
                flash("Guide généré — vérifiez l'aperçu avant publication.", "success")
            elif action == "publish" and _get_draft("article"):
                article = _get_draft("article")
                if request.form.get("featured") == "on":
                    article["featured"] = True
                if not article.get("image"):
                    article.update(attach_image_to_article(article, article.get("image_prompt")))
                add_article(article)
                _clear_draft("article")
                flash(f"Article publié : /blog/{article['slug']}", "success")
                return redirect(url_for("admin.guides"))
            elif action == "improve" and _get_draft("article"):
                current = _get_draft("article")
                if current.get("manual"):
                    flash("Utilisez l'onglet Manuel pour modifier ce brouillon.", "error")
                else:
                    article = _improve_draft(
                        current,
                        request.form.get("instructions", "Améliore le SEO et ajoute plus de détails pratiques."),
                    )
                    _store_draft("article", article)
                    flash("Article amélioré par l'IA.", "success")
            elif action == "edit":
                slug = request.form.get("slug", "").strip()
                article = get_article_by_slug(slug, "fr")
                if not article:
                    flash("Article introuvable.", "error")
                else:
                    draft = {**article, "manual": True, "editing_slug": slug}
                    _store_draft("article", draft)
                    flash(
                        f"« {article.get('title', slug)} » chargé dans le formulaire — modifiez puis enregistrez.",
                        "success",
                    )
            elif action in ("manual_draft", "manual_publish"):
                article = build_manual_article(request.form)
                editing_slug = (request.form.get("editing_slug") or "").strip()
                existing = get_article_by_slug(editing_slug) if editing_slug else None
                if existing:
                    for key in (
                        "image", "image_photo_id", "image_alt", "image_source_url",
                        "featured", "guide_type", "image_placeholder",
                    ):
                        if existing.get(key) and not article.get(key):
                            article[key] = existing[key]
                    article["editing_slug"] = editing_slug
                _apply_form_cover_image(article, is_destination=False)
                if action == "manual_publish":
                    if request.form.get("featured") == "on":
                        article["featured"] = True
                    if editing_slug:
                        article.pop("editing_slug", None)
                        replace_published_article(editing_slug, article)
                        _clear_draft("article")
                        flash(f"Article mis à jour : /blog/{article['slug']}", "success")
                        return redirect(url_for("admin.guides"))
                    add_article(article)
                    _clear_draft("article")
                    flash(f"Article publié : /blog/{article['slug']}", "success")
                    return redirect(url_for("admin.guides"))
                _store_draft("article", article)
                flash("Brouillon manuel enregistré — vérifiez l'aperçu.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(ai_client.friendly_error(e), "error")

    suggestions = get_topic_suggestions(use_ai=False)

    draft = _get_draft("article")
    cats_fr = get_categories("fr")
    counts = category_usage_counts()
    return render_template(
        "admin/guides.html",
        draft=draft,
        articles=get_articles()[:20],
        groq_ok=ai_client.is_configured(),
        ai_provider_label=ai_client.provider_label(),
        suggestions=suggestions,
        vietnam_cities=VIETNAM_CITIES,
        guide_types=GUIDE_TYPES,
        article_categories=[{"value": k, "label": c.get("label", k)} for k, c in cats_fr.items()],
        blog_categories=[
            {
                "key": k,
                "label": c.get("label", k),
                "description": c.get("description", ""),
                "builtin": k in BUILTIN_CATEGORIES,
                "count": counts.get(k, 0),
            }
            for k, c in cats_fr.items()
        ],
        draft_is_manual=bool((draft or {}).get("manual")),
    )


@admin_bp.route("/categories/add", methods=["POST"])
@login_required
def categories_add():
    try:
        key, cat = add_category(
            request.form.get("label_fr", ""),
            key=request.form.get("key", ""),
            label_en=request.form.get("label_en", ""),
            description_fr=request.form.get("description_fr", ""),
            description_en=request.form.get("description_en", ""),
        )
        flash(
            f"Catégorie créée : « {cat['label']} » (/categorie/{key}) — "
            "visible dans le blog et le sitemap.",
            "success",
        )
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.guides"))


@admin_bp.route("/categories/<key>/delete", methods=["POST"])
@login_required
def categories_delete(key):
    try:
        delete_category(key)
        flash(f"Catégorie supprimée : {key}", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("admin.guides"))


@admin_bp.route("/api/guides/suggestions", methods=["POST"])
@login_required
def api_guide_suggestions():
    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY)"}), 400
    try:
        suggestions = get_topic_suggestions(use_ai=True)
        return jsonify({"ok": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"ok": False, "error": ai_client.friendly_error(e)}), 500


@admin_bp.route("/api/guides/generate", methods=["POST"])
@login_required
def api_generate_guide():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    topic = (data.get("topic") or "").strip()
    guide_type = data.get("guide_type") or "article blog"

    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY)"}), 400
    if not city or city not in ALL_CITY_VALUES:
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400
    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    # Génération en tâche de fond : la requête répond aussitôt, le client interroge
    # /api/guides/draft-status. Évite le timeout du routeur et rend les pauses
    # anti rate-limit de Groq sans effet sur la requête HTTP.
    _start_draft_job("article", lambda report: _generate_draft(report, topic, guide_type, city))
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/guides/improve", methods=["POST"])
@login_required
def api_improve_guide():
    draft = _get_draft("article")
    if not draft:
        return jsonify({"ok": False, "error": "Aucun brouillon"}), 400
    if draft.get("manual"):
        return jsonify({"ok": False, "error": "Brouillon manuel — utilisez l'onglet Manuel pour modifier."}), 400
    data = request.get_json(silent=True) or {}
    instructions = data.get("instructions") or "Améliore le SEO pour voyageurs français préparant un trip Vietnam."
    _start_draft_job("article", lambda report: _improve_draft(report, draft, instructions))
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/guides/draft-status")
@login_required
def api_guide_draft_status():
    return jsonify(_draft_status("article"))


@admin_bp.route("/api/content/job-status")
@login_required
def api_content_job_status():
    return jsonify(_content_job_status())


@admin_bp.route("/api/content/article/<slug>/improve", methods=["POST"])
@login_required
def api_improve_published_article(slug):
    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée"}), 400
    if not get_article_by_slug(slug):
        return jsonify({"ok": False, "error": "Article introuvable"}), 404
    data = request.get_json(silent=True) or {}
    instructions = (data.get("instructions") or "").strip()
    if not instructions:
        return jsonify({"ok": False, "error": "Instructions obligatoires"}), 400

    def job(report):
        return improve_published_article(slug, instructions, report)

    _start_content_job(job, initial_phase="Amélioration IA de l'article…")
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/content/destination/<slug>/improve", methods=["POST"])
@login_required
def api_improve_published_destination(slug):
    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée"}), 400
    if not get_destination_by_slug(slug):
        return jsonify({"ok": False, "error": "Destination introuvable"}), 404
    data = request.get_json(silent=True) or {}
    instructions = (data.get("instructions") or "").strip()
    if not instructions:
        return jsonify({"ok": False, "error": "Instructions obligatoires"}), 400

    def job(report):
        return improve_published_destination(slug, instructions, report)

    _start_content_job(job, initial_phase="Amélioration IA de la destination…")
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/content/article/<slug>/image", methods=["POST"])
@login_required
def api_update_article_image(slug):
    if not get_article_by_slug(slug):
        return jsonify({"ok": False, "error": "Article introuvable"}), 404
    image_url, query, alt, upload_bytes = _parse_image_update_request()
    if not upload_bytes and not image_url and not query:
        return jsonify({"ok": False, "error": "Importez un fichier, ou indiquez une URL / mots-clés Pixabay"}), 400

    def job(report):
        if upload_bytes:
            return update_published_image_upload("article", slug, upload_bytes, alt=alt, report=report)
        return update_published_image(
            "article", slug, image_url=image_url, query=query, alt=alt, report=report,
        )

    _start_content_job(job, initial_phase="Mise à jour de l'image…")
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/content/destination/<slug>/image", methods=["POST"])
@login_required
def api_update_destination_image(slug):
    if not get_destination_by_slug(slug):
        return jsonify({"ok": False, "error": "Destination introuvable"}), 404
    image_url, query, alt, upload_bytes = _parse_image_update_request()
    if not upload_bytes and not image_url and not query:
        return jsonify({"ok": False, "error": "Importez un fichier, ou indiquez une URL / mots-clés Pixabay"}), 400

    def job(report):
        if upload_bytes:
            return update_published_image_upload("destination", slug, upload_bytes, alt=alt, report=report)
        return update_published_image(
            "destination", slug, image_url=image_url, query=query, alt=alt, report=report,
        )

    _start_content_job(job, initial_phase="Mise à jour de l'image…")
    return jsonify({"ok": True, "started": True})


def _generate_destination_draft(report, city: str, notes: str = "") -> dict:
    import time
    dest = groq_destinations.generate_destination(city, notes, progress=report)
    report("Génération de l'image de la destination (WebP)…")
    dest.update(attach_image_to_destination(
        dest,
        dest.get("image_prompt"),
        image_nonce=int(time.time() * 1000) % 1_000_000,
    ))
    report("Finalisation de la page…")
    return dest


@admin_bp.route("/destinations", methods=["GET", "POST"])
@login_required
def destinations_admin():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "publish" and _get_draft("destination"):
                dest = _get_draft("destination")
                editing_slug = dest.pop("editing_slug", "")
                add_or_update_destination(dest)
                if editing_slug and editing_slug != dest["slug"]:
                    delete_destination(editing_slug)
                _clear_draft("destination")
                flash(f"Destination publiée : /{dest['slug']}", "success")
                return redirect(url_for("admin.destinations_admin"))
            elif action == "delete":
                slug = request.form.get("slug", "")
                if slug:
                    delete_destination(slug)
                    flash("Destination supprimée.", "success")
            elif action == "set_region":
                slug = request.form.get("slug", "")
                region = request.form.get("region", "")
                dest = set_destination_region(slug, region)
                flash(
                    f"« {dest.get('name', slug)} » placée dans la section "
                    f"{REGION_LABELS_FR.get(region, region)}.",
                    "success",
                )
            elif action == "edit":
                slug = request.form.get("slug", "")
                dest = get_destination_by_slug(slug, "fr")
                if not dest:
                    flash("Destination introuvable.", "error")
                else:
                    draft = {**dest, "manual": True, "editing_slug": slug}
                    draft.setdefault("region", resolve_region(slug, dest))
                    _store_draft("destination", draft)
                    flash(f"« {dest.get('name', slug)} » chargée dans le formulaire — modifiez puis publiez.", "success")
            elif action in ("manual_draft", "manual_publish"):
                dest = build_manual_destination(request.form)
                editing_slug = (request.form.get("editing_slug") or "").strip()
                existing = get_destination_by_slug(editing_slug) if editing_slug else None
                if existing:
                    # Édition : on conserve image, hôtels, activités… non resaisis.
                    for key in ("image", "image_photo_id", "image_alt", "hotels", "activities", "region"):
                        if existing.get(key) and not dest.get(key):
                            dest[key] = existing[key]
                    dest["editing_slug"] = editing_slug
                _apply_form_cover_image(dest, is_destination=True)
                if action == "manual_publish":
                    dest.pop("editing_slug", None)
                    add_or_update_destination(dest)
                    if existing and editing_slug != dest["slug"]:
                        delete_destination(editing_slug)
                    _clear_draft("destination")
                    flash(f"Destination publiée : /{dest['slug']}", "success")
                    return redirect(url_for("admin.destinations_admin"))
                _store_draft("destination", dest)
                flash("Brouillon manuel enregistré — vérifiez l'aperçu.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Erreur : {e}", "error")
        return redirect(url_for("admin.destinations_admin"))

    sync_destination_images(allow_network=True)
    dest_list = []
    for slug, d in get_destinations_dict().items():
        d["region_key"] = resolve_region(slug, d)
        d["region_label"] = REGION_LABELS_FR.get(d["region_key"], d["region_key"])
        dest_list.append(d)
    region_rank = {key: i for i, key in enumerate(REGION_ORDER)}
    dest_list.sort(key=lambda d: (region_rank.get(d["region_key"], 9), (d.get("name") or "").lower()))
    city_options = [c for c in ALL_CITY_VALUES if c != "Tout le Vietnam"]
    # Ville → slug de la page destination déjà publiée (pour marquer le sélecteur).
    published_by_city = {}
    for c in city_options:
        slug = find_destination_slug(c)
        if slug:
            published_by_city[c] = slug

    draft = _get_draft("destination")
    return render_template(
        "admin/destinations.html",
        draft=draft,
        destinations=dest_list,
        city_options=city_options,
        published_by_city=published_by_city,
        region_options=[(key, REGION_LABELS_FR[key]) for key in REGION_ORDER],
        groq_ok=ai_client.is_configured(),
        ai_provider_label=ai_client.provider_label(),
        draft_is_manual=bool((draft or {}).get("manual")),
    )


@admin_bp.route("/api/destinations/generate", methods=["POST"])
@login_required
def api_generate_destination():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY)"}), 400
    if not city or city not in ALL_CITY_VALUES or city == "Tout le Vietnam":
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400

    _start_draft_job("destination", lambda report: _generate_destination_draft(report, city, notes))
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/destinations/draft-status")
@login_required
def api_destination_draft_status():
    return jsonify(_draft_status("destination"))


@admin_bp.route("/newsletter", methods=["GET", "POST"])
@login_required
def newsletter_admin():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action in ("manual_draft",):
                draft = build_manual_newsletter(request.form)
                _store_draft("newsletter", draft)
                flash("Brouillon email enregistré — vérifiez l'aperçu.", "success")
            elif action == "send_test":
                draft = _get_draft("newsletter")
                if not draft:
                    flash("Composez d'abord un email (IA ou manuel).", "error")
                    return redirect(url_for("admin.newsletter_admin"))
                test_email = (request.form.get("test_email") or "").strip().lower()
                if not test_email or "@" not in test_email:
                    flash("Indiquez une adresse email de test valide.", "error")
                    return redirect(url_for("admin.newsletter_admin"))
                result = send_newsletter_email(
                    [test_email],
                    draft["subject"],
                    draft["body_html"],
                    preheader=draft.get("preheader", ""),
                )
                if result["sent"]:
                    flash(f"Email de test envoyé à {test_email}.", "success")
                else:
                    flash(f"Échec d'envoi vers {test_email}.", "error")
            elif action == "send_one":
                draft = _get_draft("newsletter")
                if not draft:
                    flash("Composez d'abord un email (IA ou manuel).", "error")
                    return redirect(url_for("admin.newsletter_admin"))
                email = (request.form.get("email") or "").strip().lower()
                result = send_newsletter_email(
                    [email],
                    draft["subject"],
                    draft["body_html"],
                    preheader=draft.get("preheader", ""),
                )
                if result["sent"]:
                    flash(f"Email envoyé à {email}.", "success")
                    partner_id = (request.form.get("partner_id") or "").strip()
                    if partner_id:
                        from admin.partners_service import mark_contacted
                        mark_contacted(partner_id)
                else:
                    flash(f"Échec d'envoi vers {email}.", "error")
            elif action == "send_all":
                draft = _get_draft("newsletter")
                if not draft:
                    flash("Composez d'abord un email (IA ou manuel).", "error")
                    return redirect(url_for("admin.newsletter_admin"))
                subs = get_newsletter_subscribers()
                if not subs:
                    flash("Aucun abonné.", "error")
                    return redirect(url_for("admin.newsletter_admin"))
                result = send_newsletter_email(
                    [s["email"] for s in subs],
                    draft["subject"],
                    draft["body_html"],
                    preheader=draft.get("preheader", ""),
                )
                msg = f"{result['sent']} email(s) envoyé(s) sur {result['total']}."
                if result["failed"]:
                    msg += f" Échecs : {', '.join(result['failed'])}."
                flash(msg, "success" if result["sent"] else "error")
            elif action == "delete_subscriber":
                email = (request.form.get("email") or "").strip().lower()
                if remove_newsletter_subscriber(email):
                    flash(f"Abonné {email} supprimé.", "success")
                else:
                    flash("Abonné introuvable.", "error")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Erreur : {e}", "error")
        return redirect(url_for("admin.newsletter_admin"))

    subscribers = get_newsletter_subscribers()
    draft = _get_draft("newsletter")
    preview_html = render_newsletter_preview(draft) if draft else ""
    from admin import partners_service as ps
    partners_to_contact = [p for p in ps.get_partnerships() if p.get("email")]
    return render_template(
        "admin/newsletter.html",
        subscribers=subscribers,
        draft=draft,
        preview_html=preview_html,
        groq_ok=ai_client.is_configured(),
        ai_provider_label=ai_client.provider_label(),
        smtp_ok=is_smtp_configured(),
        email_types=groq_newsletter.EMAIL_TYPES,
        draft_is_manual=bool(draft and draft.get("manual")),
        test_email_default=os.environ.get("LEGAL_CONTACT_EMAIL", ""),
        partners_to_contact=partners_to_contact,
        partner_status_labels=ps.PARTNER_STATUS_LABELS,
    )


@admin_bp.route("/newsletter/preview")
@login_required
def newsletter_preview():
    from flask import Response
    draft = _get_draft("newsletter")
    if not draft:
        return "Aucun brouillon.", 404
    return Response(render_newsletter_preview(draft), mimetype="text/html; charset=utf-8")


@admin_bp.route("/contact", methods=["GET", "POST"])
@login_required
def contact_admin():
    from admin.contact_service import (
        delete_message,
        get_contact_messages,
        mark_message_read,
    )
    from admin.mail_service import is_contact_smtp_configured

    if request.method == "POST":
        action = request.form.get("action")
        msg_id = request.form.get("msg_id", "")
        if action == "mark_read" and mark_message_read(msg_id):
            flash("Message marqué comme lu.", "success")
        elif action == "delete" and delete_message(msg_id):
            flash("Message supprimé.", "success")
        return redirect(url_for("admin.contact_admin"))

    return render_template(
        "admin/contact.html",
        messages=get_contact_messages(),
        smtp_ok=is_contact_smtp_configured(),
    )


@admin_bp.route("/reviews", methods=["GET", "POST"])
@login_required
def reviews_admin():
    from datetime import date

    if request.method == "POST":
        action = request.form.get("action")
        reviews = get_reviews()

        if action == "delete":
            rid = request.form.get("id", "")
            reviews = [r for r in reviews if r.get("id") != rid]
            save_reviews(reviews)
            flash("Avis supprimé.", "success")

        elif action == "save":
            author = (request.form.get("author") or "").strip()
            text_fr = (request.form.get("text_fr") or "").strip()
            if not author or not text_fr:
                flash("Nom et témoignage (FR) obligatoires.", "error")
                return redirect(url_for("admin.reviews_admin"))
            rid = request.form.get("id") or f"r-{slugify(author)}-{int(date.today().strftime('%y%m%d'))}"
            try:
                rating = max(1, min(5, int(request.form.get("rating", 5))))
            except (TypeError, ValueError):
                rating = 5
            review = {
                "id": rid,
                "author": author,
                "location": (request.form.get("location") or "").strip(),
                "rating": rating,
                "date": (request.form.get("date") or date.today().isoformat()),
                "text": {
                    "fr": text_fr,
                    "en": (request.form.get("text_en") or "").strip() or text_fr,
                },
            }
            reviews = [r for r in reviews if r.get("id") != rid]
            reviews.insert(0, review)
            save_reviews(reviews)
            flash("Avis enregistré.", "success")

        return redirect(url_for("admin.reviews_admin"))

    reviews = get_reviews()
    edit_id = request.args.get("edit", "")
    editing = next((r for r in reviews if r.get("id") == edit_id), None)
    return render_template(
        "admin/reviews.html",
        reviews=reviews,
        editing=editing,
        avg=round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 1) if reviews else 0,
    )


@admin_bp.context_processor
def admin_globals():
    try:
        from admin.contact_service import count_unread_messages
        unread = count_unread_messages()
    except Exception:
        unread = 0
    return {"contact_unread": unread}


@admin_bp.route("/api/newsletter/generate", methods=["POST"])
@login_required
def api_generate_newsletter():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    email_type = data.get("email_type") or "actualite"
    notes = (data.get("notes") or "").strip()

    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY)"}), 400
    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    _start_draft_job(
        "newsletter",
        lambda report: groq_newsletter.generate_newsletter_email(topic, email_type, notes, progress=report),
    )
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/newsletter/draft-status")
@login_required
def api_newsletter_draft_status():
    return jsonify(_draft_status("newsletter"))


@admin_bp.route("/affiliates", methods=["GET", "POST"])
@login_required
def affiliates():
    days = int(request.args.get("days", 30))
    if days not in (7, 30, 90):
        days = 30

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_partner":
            id_key = request.form.get("id_key", "")
            raw = request.form.get("affiliate_id", "").strip()
            value = normalize_affiliate_input(id_key, raw)
            if id_key in PARTNER_BY_KEY or id_key in get_affiliate_ids():
                data = get_affiliate_ids()
                data[id_key] = value
                data.update(parse_viator_embed(raw))
                save_affiliate_ids(data)
                name = PARTNER_BY_KEY.get(id_key, {}).get("name", id_key)
                check = verify_affiliate_id(id_key, value)
                if check["status"] == "ok":
                    flash(f"ID {name} enregistré — tracking vérifié ({check['param']}={value}).", "success")
                elif check["status"] == "warn":
                    flash(f"ID {name} enregistré — {check['message']}", "warning")
                else:
                    flash(f"ID {name} enregistré — {check['message']}", "error")

        elif action == "add_custom":
            name = request.form.get("name", "").strip()
            if name:
                add_custom_partner({
                    "id": slugify(name),
                    "name": name,
                    "category": request.form.get("category", "Autre"),
                    "description": request.form.get("description", ""),
                    "what_you_earn": request.form.get("what_you_earn", "Variable"),
                    "affiliate_url": request.form.get("affiliate_url", "").strip(),
                    "avg_per_click": float(request.form.get("avg_per_click") or 3),
                    "signup_url": request.form.get("signup_url", "").strip(),
                    "icon": "🔗",
                })
                flash(f"Partenaire « {name} » ajouté.", "success")
                try:
                    from admin.map_service import defer_sync_all
                    defer_sync_all()
                except Exception:
                    pass

        elif action == "update_custom":
            pid = request.form.get("partner_id", "")
            partners = get_custom_partners()
            for p in partners:
                if p["id"] == pid:
                    p["affiliate_url"] = request.form.get("affiliate_url", "").strip()
                    p["avg_per_click"] = float(request.form.get("avg_per_click") or 3)
            save_custom_partners(partners)
            flash("Partenaire mis à jour.", "success")
            try:
                from admin.map_service import defer_sync_all
                defer_sync_all()
            except Exception:
                pass

        elif action == "delete_custom":
            delete_custom_partner(request.form.get("partner_id", ""))
            flash("Partenaire supprimé.", "success")

        return redirect(url_for("admin.affiliates", days=days))

    summary = build_affiliate_summary(days)
    configured = sum(1 for p in summary["partners"] if p["configured"])

    return render_template(
        "admin/affiliates.html",
        summary=summary,
        days=days,
        configured_count=configured,
        partners_total=len(summary["partners"]),
        recommendations=get_affiliate_recommendations(summary),
    )


@admin_bp.route("/revenue", methods=["GET", "POST"])
@login_required
def revenue():
    if request.method == "POST":
        try:
            db.add_revenue(
                source=request.form.get("source", "manual"),
                amount=float(request.form.get("amount", 0)),
                note=request.form.get("note", ""),
            )
            flash("Revenu ajouté.", "success")
        except ValueError:
            flash("Montant invalide.", "error")
        return redirect(url_for("admin.revenue"))

    revenue_data = db.get_revenue_stats()
    aff_stats = db.get_affiliate_stats(30)
    est = compute_estimated_commission(30)
    affiliates = get_affiliate_ids()
    affiliates_configured = sum(1 for v in affiliates.values() if v and "PLACEHOLDER" not in str(v))

    return render_template(
        "admin/revenue.html",
        revenue=revenue_data,
        est_commission=est,
        affiliates_configured=affiliates_configured,
        aff_stats=aff_stats,
        recommendations=get_revenue_recommendations(revenue_data, est, aff_stats),
    )


@admin_bp.route("/analytics")
@login_required
def analytics():
    days = int(request.args.get("days", 30))
    if days not in (7, 30, 90):
        days = 30
    stats = build_site_analytics(days)
    profile_stats = db.get_visitor_profile_stats(days)
    return render_template(
        "admin/analytics.html",
        stats=stats,
        days=days,
        social=db.get_social_traffic(days),
        profile_stats=profile_stats,
        recommendations=get_analytics_recommendations(stats, days),
    )


# ── Réseaux sociaux (Facebook + réseaux voyageurs) ────────────────────
@admin_bp.route("/social")
@login_required
def social():
    from admin import facebook_service as fb
    from admin import social_networks as sn
    from admin.social_ai import page_inventory

    inventory = page_inventory("fr")
    groups: dict[str, list] = {}
    for item in inventory:
        groups.setdefault(item["group"], []).append(item)

    return render_template(
        "admin/social.html",
        fb_configured=fb.is_configured(),
        fb_page_id=fb.get_page_id(),
        fb_token_masked=fb.masked_token(),
        networks=sn.network_status(),
        reddit_default_sub=sn.get_field("reddit_default_sub") or "VietnamTravel",
        page_groups=groups,
        pool_images=_social_pool_images(),
        social=db.get_social_traffic(30),
        ai_ready=ai_client.is_configured(),
    )


def _social_pool_images() -> list[dict]:
    """Vignettes du pool (images persistantes, URL publique) pour le contenu nouveau."""
    from admin.image_service import VIETNAM_PHOTO_POOL
    import config
    base = config.SITE_URL.rstrip("/")
    return [
        {"id": pid, "label": desc,
         "thumb": f"/static/images/pool/{pid}-640.webp",
         "url": f"{base}/static/images/pool/{pid}.webp"}
        for pid, desc in VIETNAM_PHOTO_POOL
    ]


@admin_bp.route("/social/settings", methods=["POST"])
@login_required
def social_settings():
    from admin import facebook_service as fb

    fb.save_config(request.form.get("facebook_page_id", ""),
                   request.form.get("facebook_page_token", ""))
    flash("Configuration Facebook enregistrée.", "success")
    return redirect(url_for("admin.social"))


@admin_bp.route("/social/test", methods=["POST"])
@login_required
def social_test():
    from admin import facebook_service as fb

    try:
        info = fb.test_connection()
        flash(f"Connexion OK — page « {info.get('name', '?')} » "
              f"({info.get('fan_count', 0)} abonnés).", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Échec de la connexion Facebook : {fb.friendly_error(exc)}", "error")
    return redirect(url_for("admin.social"))


@admin_bp.route("/social/network/<key>/settings", methods=["POST"])
@login_required
def social_network_settings(key):
    from admin import social_networks as sn

    net = sn.NETWORK_KEYS.get(key)
    if not net:
        flash(f"Réseau inconnu : {key}", "error")
        return redirect(url_for("admin.social"))
    try:
        sn.save_network_config(key, request.form)
        flash(f"Configuration {net['name']} enregistrée.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Échec de l'enregistrement {net['name']} : {exc}", "error")
    return redirect(url_for("admin.social"))


@admin_bp.route("/social/network/<key>/test", methods=["POST"])
@login_required
def social_network_test(key):
    from admin import social_networks as sn

    net = sn.NETWORK_KEYS.get(key)
    if not net:
        flash(f"Réseau inconnu : {key}", "error")
        return redirect(url_for("admin.social"))
    try:
        # On enregistre d'abord les champs saisis pour tester la config à jour.
        sn.save_network_config(key, request.form)
        info = sn.test_connection(key)
        flash(f"Connexion {net['name']} OK — {info}.", "success")
    except Exception as exc:  # noqa: BLE001
        flash(f"Échec de la connexion {net['name']} : {exc}", "error")
    return redirect(url_for("admin.social"))


@admin_bp.route("/api/social/generate", methods=["POST"])
@login_required
def api_social_generate():
    from admin import social_networks as sn
    from admin.social_ai import find_page, generate_post, default_campaign

    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "page")
    lang = "en" if payload.get("lang") == "en" else "fr"
    network = payload.get("network") or "facebook"
    if network not in sn.NETWORK_KEYS:
        network = "facebook"
    page = find_page(payload.get("page_id", ""), lang) if mode == "page" else None
    brief = (payload.get("brief") or "").strip()

    if mode == "page" and not page:
        return jsonify({"ok": False, "error": "Sélectionnez une page du site."}), 400
    if mode == "new" and not brief:
        return jsonify({"ok": False, "error": "Expliquez le sujet du contenu nouveau."}), 400

    try:
        message = generate_post(page=page, brief=brief, lang=lang, network=network)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": ai_client.friendly_error(exc)}), 502

    campaign = default_campaign(page, brief, network)
    return jsonify({
        "ok": True,
        "message": message,
        "campaign": campaign,
        "link": sn.add_utm(page["url"], campaign, network) if page else "",
        "image": page["image"] if page else "",
    })


@admin_bp.route("/social/publish", methods=["POST"])
@login_required
def social_publish():
    from admin import facebook_service as fb
    from admin import social_networks as sn
    from admin.social_ai import find_page

    network = request.form.get("network") or "facebook"
    net = sn.NETWORK_KEYS.get(network)
    if not net:
        flash(f"Réseau inconnu : {network}", "error")
        return redirect(url_for("admin.social"))

    mode = request.form.get("mode", "page")
    message = (request.form.get("message") or "").strip()
    campaign = fb.sanitize_campaign(request.form.get("campaign", "") or f"{network}-post")
    if not message:
        flash("Le texte du post est vide.", "error")
        return redirect(url_for("admin.social"))

    # Lien et image selon le mode (page du site ou contenu nouveau).
    image_url = (request.form.get("image_url") or "").strip()
    if mode == "page":
        page = find_page(request.form.get("page_id", ""), "fr")
        if not page:
            flash("Page introuvable.", "error")
            return redirect(url_for("admin.social"))
        link = sn.add_utm(page["url"], campaign, network)
        if not image_url:
            image_url = page.get("image", "")
    else:
        link = (request.form.get("link") or "").strip()
        if link:
            link = sn.add_utm(link, campaign, network)

    try:
        if network == "facebook":
            if not fb.is_configured():
                flash("Configurez d'abord la connexion Facebook (ID de page + token).", "error")
                return redirect(url_for("admin.social"))
            if mode == "page":
                result = fb.publish_link(message, link)
            else:
                if not image_url:
                    flash("Une image est obligatoire pour un contenu nouveau.", "error")
                    return redirect(url_for("admin.social"))
                caption = f"{message}\n\n👉 {link}" if link else message
                result = fb.publish_photo(caption, image_url)
            permalink = fb.post_permalink(result)
        else:
            permalink = sn.publish(
                network,
                message=message,
                link=link,
                image_url=image_url,
                subreddit=(request.form.get("subreddit") or "").strip(),
            )
        flash(f"Publié sur {net['name']} ✅ {permalink}".strip(), "success")
    except Exception as exc:  # noqa: BLE001
        friendly = fb.friendly_error(exc) if network == "facebook" else str(exc)
        flash(f"Échec de la publication : {friendly}", "error")
    return redirect(url_for("admin.social"))


# ── Partenariats (influenceurs, guides, blogueurs, agences…) ──────────
@admin_bp.route("/partnerships", methods=["GET", "POST"])
@login_required
def partnerships():
    from admin import partners_service as ps

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "add":
                partner = ps.add_partnership({
                    "name": request.form.get("name", ""),
                    "type": request.form.get("type", "influenceur"),
                    "email": request.form.get("email", ""),
                    "links": request.form.get("links", ""),
                    "topics": request.form.get("topics", ""),
                    "followers": request.form.get("followers", ""),
                    "notes": request.form.get("notes", ""),
                    "source": "manuel",
                })
                flash(f"Partenaire « {partner['name']} » ajouté.", "success")
            elif action == "update":
                ps.update_partnership(request.form.get("partner_id", ""), {
                    "type": request.form.get("type"),
                    "email": request.form.get("email"),
                    "status": request.form.get("status"),
                    "topics": request.form.get("topics"),
                    "notes": request.form.get("notes"),
                    "links": request.form.get("links"),
                })
                flash("Partenaire mis à jour.", "success")
            elif action == "delete":
                ps.delete_partnership(request.form.get("partner_id", ""))
                flash("Partenaire supprimé.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:  # noqa: BLE001
            flash(f"Erreur : {e}", "error")
        return redirect(url_for("admin.partnerships"))

    status_filter = request.args.get("status", "")
    type_filter = request.args.get("type", "")
    items = ps.get_partnerships()
    if status_filter:
        items = [p for p in items if p.get("status") == status_filter]
    if type_filter:
        items = [p for p in items if p.get("type") == type_filter]

    return render_template(
        "admin/partnerships.html",
        partners=items,
        stats=ps.partnership_stats(),
        types=ps.PARTNER_TYPES,
        statuses=ps.PARTNER_STATUSES,
        type_labels=ps.PARTNER_TYPE_LABELS,
        status_labels=ps.PARTNER_STATUS_LABELS,
        status_filter=status_filter,
        type_filter=type_filter,
        ai_ready=ai_client.is_configured(),
        smtp_ok=is_smtp_configured(),
    )


@admin_bp.route("/api/partnerships/search", methods=["POST"])
@login_required
def api_partnerships_search():
    from admin import assistant_service
    from admin import partners_service as ps

    payload = request.get_json(silent=True) or {}
    brief = (payload.get("brief") or "").strip()
    if not brief:
        return jsonify({"ok": False, "error": "Décrivez la recherche (ex. « influenceurs francophones voyage Vietnam »)."}), 400
    if not ai_client.is_configured():
        return jsonify({"ok": False, "error": "Aucune clé IA configurée — la recherche IA est indisponible."}), 400

    token = assistant_service.start_action_job(
        lambda report: _search_partners_result(ps, brief, report),
        initial_phase="Recherche web des influenceurs…",
    )
    return jsonify({"ok": True, "job_token": token})


def _search_partners_result(ps, brief: str, report) -> dict:
    result = ps.search_and_save_influencers(brief, progress=report)
    saved = result["saved"]
    return {
        "saved": len(saved),
        "skipped": result["skipped"],
        "names": [f"{p['name']}" + (f" ({p['email']})" if p.get("email") else "") for p in saved],
        "message": f"{len(saved)} contact(s) enregistré(s), {result['skipped']} doublon(s) ignoré(s).",
    }


@admin_bp.route("/map", methods=["GET", "POST"])
@login_required
def map_admin():
    from admin import map_service

    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "add":
                result = map_service.add_map_point(request.form)
                if result["status"] == "published":
                    flash(f"Point ajouté sur la carte de {result['slug']}.", "success")
                else:
                    flash(result["message"], "warn")
            elif action == "delete":
                pid = request.form.get("point_id", "")
                pending = request.form.get("pending") == "1"
                if pid and map_service.delete_map_point(pid, pending=pending):
                    flash("Point supprimé.", "success")
            elif action == "publish_pending":
                pid = request.form.get("point_id", "")
                slug = request.form.get("destination_slug", "")
                if pid and map_service.publish_pending_point(pid, slug):
                    flash("Point publié sur la carte.", "success")
            elif action == "set_image":
                pid = request.form.get("point_id", "")
                point = map_service.set_point_image(pid, request.form.get("image", ""))
                flash(f"Image mise à jour pour « {point.get('title', '')} ».", "success")
            elif action == "backfill_images":
                map_service.defer_backfill_point_images()
                flash(
                    "Recherche d'images lancée pour tous les points sans photo "
                    "(quelques minutes en arrière-plan) — rechargez la page pour voir le résultat.",
                    "success",
                )
            elif action == "sync":
                result = map_service.sync_from_destinations(replace=request.form.get("replace") == "1")
                msg = f"{result['added']} point(s) affilié(s) synchronisé(s) sur la carte."
                if result.get("error_count"):
                    msg += f" {result['error_count']} adresse(s) non géolocalisée(s)."
                flash(msg, "success" if result["added"] else "warn")
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            flash(f"Erreur : {exc}", "error")
        return redirect(url_for("admin.map_admin"))

    store = map_service.get_map_store()
    points = store.get("points", [])
    all_kinds = list(map_service.KIND_LABELS) + [p.get("kind", "poi") for p in points]
    kind_meta = {
        item["kind"]: {"label": item["label"], "color": item["color"]}
        for item in map_service.legend_for_kinds(all_kinds, "fr")
    }
    return render_template(
        "admin/map.html",
        points=points,
        pending=store.get("pending", []),
        dest_options=map_service.destination_options(),
        city_options=[c for c in ALL_CITY_VALUES if c != "Tout le Vietnam"],
        kind_options=list(map_service.KIND_LABELS.keys()),
        kind_meta=kind_meta,
        provider_options=list(map_service.PROVIDER_LABELS.keys()),
    )


@admin_bp.route("/api/map/geocode", methods=["POST"])
@login_required
def api_map_geocode():
    from admin import map_service

    payload = request.get_json(silent=True) or {}
    address = (payload.get("address") or "").strip()
    try:
        geo = map_service.geocode_address(address)
        return jsonify({"ok": True, **geo})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 502


@admin_bp.route("/api/affiliate-verify", methods=["POST"])
@login_required
def api_affiliate_verify():
    payload = request.get_json(silent=True) or {}
    id_key = (payload.get("id_key") or request.form.get("id_key") or "").strip()
    value = payload.get("value") if payload else request.form.get("value", "")
    if not id_key:
        return jsonify({"ok": False, "error": "id_key manquant"}), 400
    result = verify_affiliate_id(id_key, value or "")
    return jsonify({"ok": True, **result})


@admin_bp.route("/api/realtime")
@login_required
def api_realtime():
    return jsonify(db.get_realtime_stats())


# ── Linh — copilote IA interne (développement & SEO) ──────────────────
# Différent de Mai (widget public) : voir admin/assistant_service.py.

@admin_bp.route("/api/assistant", methods=["POST"])
@login_required
def api_assistant():
    from admin import assistant_service

    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    try:
        return jsonify(assistant_service.chat_reply(message, history))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": ai_client.friendly_error(exc)}), 502


@admin_bp.route("/api/assistant/search", methods=["POST"])
@login_required
def api_assistant_search():
    """Deuxième temps de la recherche web de Linh (le widget affiche un loader)."""
    from admin import assistant_service

    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()
    message = (payload.get("message") or "").strip()
    history = payload.get("history") if isinstance(payload.get("history"), list) else []
    try:
        return jsonify(assistant_service.search_reply(query, message, history))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": ai_client.friendly_error(exc)}), 502


@admin_bp.route("/api/assistant/reset", methods=["POST"])
@login_required
def api_assistant_reset():
    from admin import assistant_service

    return jsonify(assistant_service.reset_conversation())


@admin_bp.route("/api/assistant/insights")
@login_required
def api_assistant_insights():
    from admin import assistant_service

    try:
        return jsonify(assistant_service.build_insights())
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


@admin_bp.route("/api/assistant/job/<kind>")
@login_required
def api_assistant_job(kind):
    from admin import assistant_service

    return jsonify(assistant_service.job_status(kind))


@admin_bp.route("/api/assistant/action-job/<token>")
@login_required
def api_assistant_action_job(token):
    from admin import assistant_service

    return jsonify(assistant_service.action_job_status(token))


@admin_bp.route("/api/assistant/confirm", methods=["POST"])
@login_required
def api_assistant_confirm():
    from admin import assistant_service

    payload = request.get_json(silent=True) or {}
    token = (payload.get("token") or "").strip()
    decision = payload.get("decision") or "confirm"
    if not token:
        return jsonify({"ok": False, "error": "Token manquant."}), 400
    if decision == "cancel":
        assistant_service.cancel_confirmation(token)
        return jsonify({"ok": True, "message": "Action annulée — rien n'a été publié."})
    try:
        result = assistant_service.execute_confirmation(token)
        return jsonify({"ok": True, **result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": ai_client.friendly_error(exc)}), 502
