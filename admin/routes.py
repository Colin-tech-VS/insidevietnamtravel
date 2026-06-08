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
from admin import groq_destinations
from admin import groq_newsletter
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
from admin.store import (
    get_settings, save_settings,
    get_affiliate_ids, save_affiliate_ids,
    get_articles, add_article,
    get_destinations_dict, add_or_update_destination, delete_destination,
    count_newsletter_subscribers,
    add_custom_partner, delete_custom_partner, get_custom_partners,
    save_custom_partners, slugify,
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
                session["draft_article"] = article
                flash("Guide généré — vérifiez l'aperçu avant publication.", "success")
            elif action == "publish" and session.get("draft_article"):
                article = session["draft_article"]
                if request.form.get("featured") == "on":
                    article["featured"] = True
                if not article.get("image"):
                    article.update(attach_image_to_article(article, article.get("image_prompt")))
                add_article(article)
                session.pop("draft_article", None)
                flash(f"Article publié : /blog/{article['slug']}", "success")
                return redirect(url_for("admin.guides"))
            elif action == "improve" and session.get("draft_article"):
                if session["draft_article"].get("manual"):
                    flash("Utilisez l'onglet Manuel pour modifier ce brouillon.", "error")
                else:
                    article = _improve_draft(
                        session["draft_article"],
                        request.form.get("instructions", "Améliore le SEO et ajoute plus de détails pratiques."),
                    )
                    session["draft_article"] = article
                    flash("Article amélioré par l'IA.", "success")
            elif action in ("manual_draft", "manual_publish"):
                article = build_manual_article(request.form)
                if request.form.get("generate_image") == "on":
                    article.update(attach_image_to_article(article, None))
                if action == "manual_publish":
                    if request.form.get("featured") == "on":
                        article["featured"] = True
                    add_article(article)
                    session.pop("draft_article", None)
                    flash(f"Article publié : /blog/{article['slug']}", "success")
                    return redirect(url_for("admin.guides"))
                session["draft_article"] = article
                flash("Brouillon manuel enregistré — vérifiez l'aperçu.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Erreur : {e}", "error")

    suggestions = get_topic_suggestions(use_ai=bool(os.environ.get("GROQ_API_KEY")))

    return render_template(
        "admin/guides.html",
        draft=session.get("draft_article"),
        articles=get_articles()[:20],
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        suggestions=suggestions,
        vietnam_cities=VIETNAM_CITIES,
        guide_types=GUIDE_TYPES,
        article_categories=[{"value": k, "label": v} for k, v in CATEGORY_LABELS.items()],
        draft_is_manual=bool(session.get("draft_article", {}).get("manual")),
    )


@admin_bp.route("/api/guides/generate", methods=["POST"])
@login_required
def api_generate_guide():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    topic = (data.get("topic") or "").strip()
    guide_type = data.get("guide_type") or "article blog"

    if not city or city not in ALL_CITY_VALUES:
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400
    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    try:
        article = _generate_draft(topic, guide_type, city)
        session["draft_article"] = article
        return jsonify({"ok": True, "title": article["title"], "slug": article["slug"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@admin_bp.route("/api/guides/improve", methods=["POST"])
@login_required
def api_improve_guide():
    if not session.get("draft_article"):
        return jsonify({"ok": False, "error": "Aucun brouillon"}), 400
    if session["draft_article"].get("manual"):
        return jsonify({"ok": False, "error": "Brouillon manuel — utilisez l'onglet Manuel pour modifier."}), 400
    data = request.get_json(silent=True) or {}
    instructions = data.get("instructions") or "Améliore le SEO pour voyageurs français préparant un trip Vietnam."
    try:
        article = _improve_draft(session["draft_article"], instructions)
        session["draft_article"] = article
        return jsonify({"ok": True, "title": article["title"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


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
            if action == "publish" and session.get("draft_destination"):
                dest = session["draft_destination"]
                add_or_update_destination(dest)
                session.pop("draft_destination", None)
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
                    session.pop("draft_destination", None)
                    flash(f"Destination publiée : /{dest['slug']}", "success")
                    return redirect(url_for("admin.destinations_admin"))
                session["draft_destination"] = dest
                flash("Brouillon manuel enregistré — vérifiez l'aperçu.", "success")
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Erreur : {e}", "error")
        return redirect(url_for("admin.destinations_admin"))

    ensure_all_destination_images()
    dest_list = sorted(get_destinations_dict().values(), key=lambda d: d.get("name", ""))
    city_options = [c for c in ALL_CITY_VALUES if c != "Tout le Vietnam"]

    return render_template(
        "admin/destinations.html",
        draft=session.get("draft_destination"),
        destinations=dest_list,
        city_options=city_options,
        groq_ok=bool(os.environ.get("GROQ_API_KEY")),
        draft_is_manual=bool(session.get("draft_destination", {}).get("manual")),
    )


@admin_bp.route("/api/destinations/generate", methods=["POST"])
@login_required
def api_generate_destination():
    data = request.get_json(silent=True) or {}
    city = (data.get("city") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not city or city not in ALL_CITY_VALUES or city == "Tout le Vietnam":
        return jsonify({"ok": False, "error": "Ville obligatoire"}), 400

    try:
        dest = _generate_destination_draft(city, notes)
        session["draft_destination"] = dest
        return jsonify({"ok": True, "name": dest["name"], "slug": dest["slug"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@admin_bp.route("/newsletter", methods=["GET", "POST"])
@login_required
def newsletter_admin():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action in ("manual_draft",):
                draft = build_manual_newsletter(request.form)
                session["draft_newsletter"] = draft
                flash("Brouillon email enregistré — vérifiez l'aperçu.", "success")
            elif action == "send_test":
                draft = session.get("draft_newsletter")
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
                draft = session.get("draft_newsletter")
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
                draft = session.get("draft_newsletter")
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
    draft = session.get("draft_newsletter")
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
    draft = session.get("draft_newsletter")
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

    if not topic:
        return jsonify({"ok": False, "error": "Sujet obligatoire"}), 400

    try:
        draft = groq_newsletter.generate_newsletter_email(topic, email_type, notes)
        session["draft_newsletter"] = draft
        return jsonify({"ok": True, "subject": draft["subject"]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


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
            value = request.form.get("affiliate_id", "").strip()
            if id_key in PARTNER_BY_KEY or id_key in get_affiliate_ids():
                data = get_affiliate_ids()
                data[id_key] = value
                save_affiliate_ids(data)
                name = PARTNER_BY_KEY.get(id_key, {}).get("name", id_key)
                flash(f"ID {name} enregistré.", "success")

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


@admin_bp.route("/api/realtime")
@login_required
def api_realtime():
    return jsonify(db.get_realtime_stats())
