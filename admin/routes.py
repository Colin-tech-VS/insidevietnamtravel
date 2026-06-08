"""Routes /admin — dashboard, IA, affiliation, revenus, analytics."""

import json
import os

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify,
)

from admin.auth import check_password, do_login, do_logout, login_required
from admin import db
from admin import groq_ai
from admin import groq_client
from admin import groq_destinations
from admin import groq_newsletter
from admin import draft_store
from admin.image_service import attach_image_to_article, attach_image_to_destination, ensure_all_destination_images
from admin.topic_suggestions import get_topic_suggestions
from admin.admin_recommendations import (
    get_dashboard_recommendations,
    get_affiliate_recommendations,
    get_analytics_recommendations,
    get_revenue_recommendations,
)
from data.vietnam_cities import VIETNAM_CITIES, GUIDE_TYPES, ALL_CITY_VALUES
from admin.affiliate_service import build_affiliate_summary, build_site_analytics, compute_estimated_commission
from admin.affiliate_verify import normalize_affiliate_input, parse_viator_embed, verify_affiliate_id
from admin.store import (
    get_settings, save_settings,
    get_affiliate_ids, save_affiliate_ids,
    get_articles, add_article,
    get_destinations_dict, add_or_update_destination, delete_destination,
    count_newsletter_subscribers,
    add_custom_partner, delete_custom_partner, get_custom_partners,
    save_custom_partners, slugify,
    get_reviews, save_reviews,
)
from admin.newsletter_service import (
    get_newsletter_subscribers,
    build_manual_newsletter,
    send_newsletter_email,
    remove_newsletter_subscriber,
    is_smtp_configured,
    render_newsletter_preview,
)
from admin.manual_content import build_manual_article, build_manual_destination, CATEGORY_LABELS
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


def _start_draft_job(kind: str, fn) -> None:
    token = draft_store.new_token()
    session[_draft_token_key(kind)] = token
    draft_store.start_job(token, fn, groq_client.friendly_error)


def _draft_status(kind: str) -> dict:
    return draft_store.status(session.get(_draft_token_key(kind)))


def _generate_draft(topic: str, guide_type: str, city: str) -> dict:
    import time
    article = groq_ai.generate_guide(topic=topic, guide_type=guide_type, city=city)
    article["city"] = city
    article.update(attach_image_to_article(
        article,
        article.get("image_prompt"),
        image_nonce=int(time.time() * 1000) % 1_000_000,
    ))
    return article


def _improve_draft(article: dict, instructions: str) -> dict:
    article = groq_ai.improve_guide(article, instructions)
    if article.get("image_prompt"):
        article.update(attach_image_to_article(article, article.get("image_prompt")))
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
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        recommendations=get_dashboard_recommendations(
            groq_ok=bool(os.environ.get("GROQ_API_KEY")),
            affiliates_configured=configured,
            affiliates_total=len(affiliates),
            articles_count=len(get_articles()),
            totals=totals,
            est_commission=est_commission,
        ),
    )


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
            elif action in ("manual_draft", "manual_publish"):
                article = build_manual_article(request.form)
                if request.form.get("generate_image") == "on":
                    article.update(attach_image_to_article(article, None))
                if action == "manual_publish":
                    if request.form.get("featured") == "on":
                        article["featured"] = True
                    add_article(article)
                    _clear_draft("article")
                    flash(f"Article publié : /blog/{article['slug']}", "success")
                    return redirect(url_for("admin.guides"))
                _store_draft("article", article)
                flash("Brouillon manuel enregistré — vérifiez l'aperçu.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(groq_client.friendly_error(e), "error")

    suggestions = get_topic_suggestions(use_ai=False)

    draft = _get_draft("article")
    return render_template(
        "admin/guides.html",
        draft=draft,
        articles=get_articles()[:20],
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        suggestions=suggestions,
        vietnam_cities=VIETNAM_CITIES,
        guide_types=GUIDE_TYPES,
        article_categories=[{"value": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        draft_is_manual=bool((draft or {}).get("manual")),
    )


@admin_bp.route("/api/guides/suggestions", methods=["POST"])
@login_required
def api_guide_suggestions():
    if not os.environ.get("GROQ_API_KEY"):
        return jsonify({"ok": False, "error": "GROQ_API_KEY manquante"}), 400
    try:
        suggestions = get_topic_suggestions(use_ai=True)
        return jsonify({"ok": True, "suggestions": suggestions})
    except Exception as e:
        return jsonify({"ok": False, "error": groq_client.friendly_error(e)}), 500


@admin_bp.route("/api/guides/generate", methods=["POST"])
@login_required
def api_generate_guide():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    topic = (data.get("topic") or "").strip()
    guide_type = data.get("guide_type") or "article blog"

    if not os.environ.get("GROQ_API_KEY"):
        return jsonify({"ok": False, "error": "GROQ_API_KEY manquante"}), 400
    if not city or city not in ALL_CITY_VALUES:
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400
    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    # Génération en tâche de fond : la requête répond aussitôt, le client interroge
    # /api/guides/draft-status. Évite le timeout du routeur et rend les pauses
    # anti rate-limit de Groq sans effet sur la requête HTTP.
    _start_draft_job("article", lambda: _generate_draft(topic, guide_type, city))
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
    _start_draft_job("article", lambda: _improve_draft(draft, instructions))
    return jsonify({"ok": True, "started": True})


@admin_bp.route("/api/guides/draft-status")
@login_required
def api_guide_draft_status():
    return jsonify(_draft_status("article"))


def _generate_destination_draft(city: str, notes: str = "") -> dict:
    import time
    dest = groq_destinations.generate_destination(city, notes)
    dest.update(attach_image_to_destination(
        dest,
        dest.get("image_prompt"),
        image_nonce=int(time.time() * 1000) % 1_000_000,
    ))
    return dest


@admin_bp.route("/destinations", methods=["GET", "POST"])
@login_required
def destinations_admin():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "publish" and _get_draft("destination"):
                dest = _get_draft("destination")
                add_or_update_destination(dest)
                _clear_draft("destination")
                flash(f"Destination publiée : /{dest['slug']}", "success")
                return redirect(url_for("admin.destinations_admin"))
            elif action == "delete":
                slug = request.form.get("slug", "")
                if slug:
                    delete_destination(slug)
                    flash("Destination supprimée.", "success")
            elif action in ("manual_draft", "manual_publish"):
                dest = build_manual_destination(request.form)
                if request.form.get("generate_image") == "on":
                    dest.update(attach_image_to_destination(dest, None))
                if action == "manual_publish":
                    add_or_update_destination(dest)
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

    ensure_all_destination_images()
    dest_list = sorted(get_destinations_dict().values(), key=lambda d: d.get("name", ""))
    city_options = [c for c in ALL_CITY_VALUES if c != "Tout le Vietnam"]

    draft = _get_draft("destination")
    return render_template(
        "admin/destinations.html",
        draft=draft,
        destinations=dest_list,
        city_options=city_options,
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        draft_is_manual=bool((draft or {}).get("manual")),
    )


@admin_bp.route("/api/destinations/generate", methods=["POST"])
@login_required
def api_generate_destination():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not os.environ.get("GROQ_API_KEY"):
        return jsonify({"ok": False, "error": "GROQ_API_KEY manquante"}), 400
    if not city or city not in ALL_CITY_VALUES or city == "Tout le Vietnam":
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400

    _start_draft_job("destination", lambda: _generate_destination_draft(city, notes))
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
    return render_template(
        "admin/newsletter.html",
        subscribers=subscribers,
        draft=draft,
        preview_html=preview_html,
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        smtp_ok=is_smtp_configured(),
        email_types=groq_newsletter.EMAIL_TYPES,
        draft_is_manual=bool(draft and draft.get("manual")),
        test_email_default=os.environ.get("LEGAL_CONTACT_EMAIL", ""),
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

    if not os.environ.get("GROQ_API_KEY"):
        return jsonify({"ok": False, "error": "GROQ_API_KEY manquante"}), 400
    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    _start_draft_job(
        "newsletter",
        lambda: groq_newsletter.generate_newsletter_email(topic, email_type, notes),
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

        elif action == "update_custom":
            pid = request.form.get("partner_id", "")
            partners = get_custom_partners()
            for p in partners:
                if p["id"] == pid:
                    p["affiliate_url"] = request.form.get("affiliate_url", "").strip()
                    p["avg_per_click"] = float(request.form.get("avg_per_click") or 3)
            save_custom_partners(partners)
            flash("Partenaire mis à jour.", "success")

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
    return render_template(
        "admin/analytics.html",
        stats=stats,
        days=days,
        recommendations=get_analytics_recommendations(stats, days),
    )


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
