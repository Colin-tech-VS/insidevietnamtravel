"""Blueprint espace partenaires — /partners."""

from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from admin import ai_client
from admin import draft_store
from admin.groq_partner_page import generate_and_review_partner_page
from admin.partner_portal_service import (
    PAGE_STATUS_LABELS,
    PROFILE_TYPE_LABELS,
    PROFILE_TYPES,
    apply_ai_page_result,
    authenticate_partner,
    get_page_by_partner,
    is_hidden_test_partner,
    mark_page_ai_review,
    save_page_draft,
)
from partners.auth import (
    current_partner,
    do_partner_login,
    do_partner_logout,
    partner_login_required,
    request_path,
)

partners_bp = Blueprint("partners", __name__, url_prefix="/partners")

_JOB_KEY = "partner_page_job_token"


def _start_page_job(partner_id: str) -> str:
    account = current_partner()
    if not account or account["id"] != partner_id:
        raise ValueError("Accès refusé.")
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Enregistrez d'abord un brouillon de page.")

    mark_page_ai_review(partner_id)
    token = draft_store.new_token()
    session[_JOB_KEY] = token

    def _run(report):
        result = generate_and_review_partner_page(account, page, progress=report)
        apply_ai_page_result(partner_id, result)
        return result

    draft_store.start_job(
        token,
        _run,
        ai_client.friendly_error,
        initial_phase="Analyse du profil partenaire…",
    )
    return token


@partners_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_partner():
        return redirect(url_for("partners.dashboard"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        account = authenticate_partner(email, password)
        if account:
            do_partner_login(account["id"])
            nxt = (request.args.get("next") or request.form.get("next") or "").strip()
            if nxt.startswith("/partners"):
                return redirect(nxt)
            return redirect(url_for("partners.dashboard"))
        flash("Email ou mot de passe incorrect.", "error")
    return render_template(
        "partners/login.html",
        next_url=request.args.get("next") or "",
    )


@partners_bp.route("/logout", methods=["POST"])
def logout():
    do_partner_logout()
    session.pop(_JOB_KEY, None)
    return redirect(url_for("partners.login"))


@partners_bp.route("/")
@partner_login_required
def dashboard():
    partner = current_partner()
    page = get_page_by_partner(partner["id"]) if partner else None
    is_hidden = is_hidden_test_partner(partner) if partner else False
    return render_template(
        "partners/dashboard.html",
        partner=partner,
        page=page,
        is_hidden_account=is_hidden,
        profile_label=PROFILE_TYPE_LABELS.get(partner.get("profile_type"), ""),
        page_status_labels=PAGE_STATUS_LABELS,
        ai_ready=ai_client.is_configured(),
    )


@partners_bp.route("/page", methods=["GET", "POST"])
@partner_login_required
def page_edit():
    partner = current_partner()
    is_hidden = is_hidden_test_partner(partner)
    page = get_page_by_partner(partner["id"])
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "save":
                page = save_page_draft(
                    partner["id"],
                    pitch=request.form.get("pitch", ""),
                    highlights=request.form.get("highlights", ""),
                    offer_details=request.form.get("offer_details", ""),
                    city=request.form.get("city", ""),
                    contact_note=request.form.get("contact_note", ""),
                )
                flash("Brouillon enregistré.", "success")
            elif action == "submit_ai":
                if not ai_client.is_configured():
                    flash("Génération IA indisponible — contactez l'équipe.", "error")
                else:
                    save_page_draft(
                        partner["id"],
                        pitch=request.form.get("pitch", ""),
                        highlights=request.form.get("highlights", ""),
                        offer_details=request.form.get("offer_details", ""),
                        city=request.form.get("city", ""),
                        contact_note=request.form.get("contact_note", ""),
                    )
                    _start_page_job(partner["id"])
                    flash("Analyse IA lancée — patientez quelques instants.", "success")
                    return redirect(url_for("partners.page_review"))
        except ValueError as e:
            flash(str(e), "error")
        page = get_page_by_partner(partner["id"])
    extra = (page or {}).get("extra") or {}
    return render_template(
        "partners/page_edit.html",
        partner=partner,
        page=page,
        extra=extra,
        is_hidden_account=is_hidden,
        profile_label=PROFILE_TYPE_LABELS.get(partner.get("profile_type"), ""),
        profile_types=PROFILE_TYPES,
        ai_ready=ai_client.is_configured(),
    )


@partners_bp.route("/page/preview")
@partner_login_required
def page_preview():
    """Aperçu privé de la page (obligatoire pour le compte test invisible)."""
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    if not page or not (page.get("overview_html") or page.get("title")):
        flash("Aucune page à prévisualiser — soumettez d'abord à l'IA.", "error")
        return redirect(url_for("partners.page_edit"))
    return render_template(
        "partner_public.html",
        page=page,
        partner=partner,
        meta_title=(page.get("seo_title") or page.get("title") or "Aperçu"),
        meta_description=page.get("seo_description") or page.get("tagline") or "",
        is_private_preview=True,
    )


@partners_bp.route("/page/review")
@partner_login_required
def page_review():
    partner = current_partner()
    is_hidden = is_hidden_test_partner(partner)
    page = get_page_by_partner(partner["id"])
    job_token = session.get(_JOB_KEY)
    job_status = draft_store.status(job_token) if job_token else {"status": "missing"}
    if job_status.get("status") == "done":
        session.pop(_JOB_KEY, None)
        page = get_page_by_partner(partner["id"])
    return render_template(
        "partners/page_review.html",
        partner=partner,
        page=page,
        job_status=job_status,
        is_hidden_account=is_hidden,
        page_status_labels=PAGE_STATUS_LABELS,
    )


@partners_bp.route("/api/page-job-status")
@partner_login_required
def api_page_job_status():
    token = session.get(_JOB_KEY)
    return jsonify(draft_store.status(token))


@partners_bp.route("/api/page-job-poll")
@partner_login_required
def api_page_job_poll():
    """Attente légère côté serveur pour simplifier le front."""
    import time
    token = session.get(_JOB_KEY)
    if not token:
        return jsonify({"status": "missing"})
    for _ in range(40):
        st = draft_store.status(token)
        if st.get("status") in ("done", "error", "missing"):
            if st.get("status") == "done":
                session.pop(_JOB_KEY, None)
            return jsonify(st)
        time.sleep(1.5)
    return jsonify(draft_store.status(token))
