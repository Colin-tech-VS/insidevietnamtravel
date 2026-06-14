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
from admin.groq_partner_page import generate_and_review_partner_page, suggest_partner_page_fixes
from admin.partner_portal_service import (
    PAGE_STATUS_LABELS,
    PROFILE_TYPE_LABELS,
    PROFILE_TYPES,
    apply_ai_page_result,
    apply_partner_fixes,
    authenticate_partner,
    get_page_by_partner,
    get_page_fixes,
    is_hidden_test_partner,
    mark_page_ai_review,
    page_ai_review_orphaned,
    page_ai_review_stale,
    page_review_job_running,
    partner_page_has_publishable_content,
    partner_page_can_preview,
    partner_page_publication,
    partner_page_workflow,
    publish_partner_page,
    release_page_from_ai_review,
    request_partner_password_reset,
    reset_partner_password_with_token,
    review_job_token,
    save_page_draft,
    save_page_review_hints,
    save_page_vitrine,
    page_vitrine_checklist,
)
from i18n_utils import get_lang
from partners.auth import (
    current_partner,
    do_partner_login,
    do_partner_logout,
    partner_login_required,
    request_path,
)

partners_bp = Blueprint("partners", __name__, url_prefix="/partners")

_JOB_KEY = "partner_page_job_token"

_PARTNER_META = {
    "partners.login": ("Connexion partenaire", "Connectez-vous à votre espace partenaire Inside Vietnam Travel."),
    "partners.forgot_password": ("Mot de passe oublié", "Réinitialisez le mot de passe de votre espace partenaire."),
    "partners.reset_password": ("Nouveau mot de passe", "Choisissez un nouveau mot de passe pour votre espace partenaire."),
    "partners.dashboard": ("Espace partenaire", "Gérez votre page partenaire et suivez la vérification."),
    "partners.page_edit": ("Ma page partenaire", "Rédigez votre fiche puis vérifiez-la avant publication."),
    "partners.page_review": ("Validation IA", "Suivi de l'analyse éditoriale de votre page partenaire."),
}


@partners_bp.context_processor
def partner_template_globals():
    import config as site_config
    from admin.partner_portal_service import get_page_by_partner, is_hidden_test_partner

    account = current_partner()
    ep = request.endpoint or ""
    title, desc = _PARTNER_META.get(ep, ("Espace partenaire", "Espace partenaire Inside Vietnam Travel."))
    page = get_page_by_partner(account["id"]) if account else None
    hidden = is_hidden_test_partner(account) if account else False
    return {
        "partner": account,
        "partner_page": page,
        "is_hidden_account": hidden,
        "meta_title": f"{title} — {site_config.SITE_NAME}",
        "meta_description": desc,
    }


def _sync_job_token(page, token: str | None) -> str | None:
    """Réattache le token de job depuis la BDD si la session Flask l'a perdu."""
    token = review_job_token(page, token)
    if token:
        session[_JOB_KEY] = token
    return token


def _resolve_review_page(partner_id: str, page, job_status: dict) -> tuple[dict | None, dict, bool]:
    """Normalise l'état page + job (orphelins, timeout, session perdue)."""
    token = _sync_job_token(page, session.get(_JOB_KEY))

    if job_status.get("status") == "done":
        session.pop(_JOB_KEY, None)
        page = get_page_by_partner(partner_id)
        token = review_job_token(page, session.get(_JOB_KEY))
        job_status = draft_store.status(token) if token else {"status": "missing", "error": "", "phase": ""}
    elif job_status.get("status") == "error":
        release_page_from_ai_review(partner_id)
        page = get_page_by_partner(partner_id)
        token = review_job_token(page, session.get(_JOB_KEY))
        job_status = draft_store.status(token) if token else job_status

    if page and page_ai_review_orphaned(page, token):
        release_page_from_ai_review(partner_id)
        page = get_page_by_partner(partner_id)
        if job_status.get("status") == "missing":
            job_status = {
                "status": "error",
                "error": "L'analyse a été interrompue (session expirée ou redémarrage serveur).",
                "phase": "",
            }
    elif page and page.get("status") == "ai_review" and page_ai_review_stale(page):
        release_page_from_ai_review(partner_id)
        page = get_page_by_partner(partner_id)
        if job_status.get("status") in ("missing", "running"):
            job_status = {
                "status": "error",
                "error": "L'analyse a pris trop de temps — relancez la vérification.",
                "phase": "",
            }

    token = review_job_token(page, session.get(_JOB_KEY))
    job_running = page_review_job_running(token) if token else False
    page_status = (page or {}).get("status")
    job_state = job_status.get("status")
    show_loader = job_running or (page_status == "ai_review" and job_running)

    return page, job_status, show_loader


def _start_page_job(partner_id: str) -> str:
    account = current_partner()
    if not account or account["id"] != partner_id:
        raise ValueError("Accès refusé.")
    page = get_page_by_partner(partner_id)
    if not page:
        raise ValueError("Enregistrez d'abord un brouillon de page.")

    token = draft_store.new_token()
    mark_page_ai_review(partner_id, job_token=token)
    session[_JOB_KEY] = token

    def _run(report):
        try:
            fresh_page = get_page_by_partner(partner_id)
            if not fresh_page:
                raise ValueError("Brouillon de page introuvable.")
            result = generate_and_review_partner_page(account, fresh_page, progress=report)
            apply_ai_page_result(partner_id, result)
            return result
        except Exception as exc:
            release_page_from_ai_review(partner_id)
            try:
                fresh_page = get_page_by_partner(partner_id)
                if fresh_page:
                    hints = suggest_partner_page_fixes(
                        account,
                        fresh_page,
                        reason=str(exc),
                    )
                    save_page_review_hints(
                        partner_id,
                        hints.get("review") or {},
                        error_reason=str(exc),
                    )
            except Exception:
                pass
            raise

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


@partners_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_partner():
        return redirect(url_for("partners.dashboard"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        try:
            request_partner_password_reset(email)
            flash(
                "Si un compte existe avec cet email, vous recevrez un lien de réinitialisation sous peu.",
                "success",
            )
            return redirect(url_for("partners.login"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("partners/forgot_password.html")


@partners_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_partner():
        return redirect(url_for("partners.dashboard"))
    if request.method == "POST":
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""
        try:
            reset_partner_password_with_token(
                token,
                password=password,
                password_confirm=password_confirm,
            )
            flash("Mot de passe mis à jour. Vous pouvez vous connecter.", "success")
            return redirect(url_for("partners.login"))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template("partners/reset_password.html", token=token)


@partners_bp.route("/logout", methods=["GET", "POST"])
def logout():
    do_partner_logout()
    session.pop(_JOB_KEY, None)
    flash("Vous êtes déconnecté de l'espace partenaire.", "success")
    return redirect(url_for("partners.login"))


@partners_bp.route("/")
@partner_login_required
def dashboard():
    partner = current_partner()
    page = get_page_by_partner(partner["id"]) if partner else None
    is_hidden = is_hidden_test_partner(partner) if partner else False
    publication = partner_page_publication(page, is_hidden=is_hidden)
    return render_template(
        "partners/dashboard.html",
        partner=partner,
        page=page,
        is_hidden_account=is_hidden,
        profile_label=PROFILE_TYPE_LABELS.get(partner.get("profile_type"), ""),
        page_status_labels=PAGE_STATUS_LABELS,
        publication=publication,
        workflow=partner_page_workflow(page, publication=publication, is_hidden=is_hidden),
        page_vitrine=page_vitrine_checklist(page),
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
            elif action == "save_vitrine":
                photo = request.files.get("photo_file")
                file_bytes = photo.read() if photo and photo.filename else None
                if file_bytes and len(file_bytes) > 5 * 1024 * 1024:
                    raise ValueError("Photo trop volumineuse (max 5 Mo).")
                page = save_page_vitrine(
                    partner["id"],
                    profile_highlights_text=request.form.get("profile_highlights", ""),
                    image_url=request.form.get("image_url", ""),
                    image_file=file_bytes,
                    clear_image=request.form.get("clear_image") == "1",
                )
                flash("Vitrine enregistrée.", "success")
                return redirect(url_for("partners.page_edit", step=4))
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
                    flash("Vérification lancée — patientez quelques instants.", "success")
                    return redirect(url_for("partners.page_review"))
        except ValueError as e:
            flash(str(e), "error")
        page = get_page_by_partner(partner["id"])
    elif request.method == "GET" and page and page.get("status") == "ai_review":
        token = _sync_job_token(page, session.get(_JOB_KEY))
        if page_ai_review_orphaned(page, token) or page_ai_review_stale(page):
            release_page_from_ai_review(partner["id"])
            page = get_page_by_partner(partner["id"])
    extra = (page or {}).get("extra") or {}
    vitrine = page_vitrine_checklist(page)
    wizard_step = request.args.get("step", type=int) or 1
    if wizard_step < 1 or wizard_step > 4:
        wizard_step = 1
    return render_template(
        "partners/page_edit.html",
        partner=partner,
        page=page,
        extra=extra,
        is_hidden_account=is_hidden,
        profile_label=PROFILE_TYPE_LABELS.get(partner.get("profile_type"), ""),
        profile_types=PROFILE_TYPES,
        ai_ready=ai_client.is_configured(),
        page_vitrine=vitrine,
        wizard_step=wizard_step,
    )


@partners_bp.route("/page/vitrine", methods=["GET", "POST"])
@partner_login_required
def page_vitrine():
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    if not page:
        flash("Créez d'abord votre page (accroche, atouts, offre).", "error")
        return redirect(url_for("partners.page_edit"))
    if request.method == "POST":
        try:
            photo = request.files.get("photo_file")
            file_bytes = photo.read() if photo and photo.filename else None
            if file_bytes and len(file_bytes) > 5 * 1024 * 1024:
                raise ValueError("Photo trop volumineuse (max 5 Mo).")
            save_page_vitrine(
                partner["id"],
                profile_highlights_text=request.form.get("profile_highlights", ""),
                image_url=request.form.get("image_url", ""),
                image_file=file_bytes,
                clear_image=request.form.get("clear_image") == "1",
            )
            flash("Vitrine enregistrée — visible sur votre page publique.", "success")
            return redirect(url_for("partners.page_vitrine"))
        except ValueError as exc:
            flash(str(exc), "error")
        page = get_page_by_partner(partner["id"])
    return render_template(
        "partners/page_vitrine.html",
        partner=partner,
        page=page,
        profile_label=PROFILE_TYPE_LABELS.get(partner.get("profile_type"), ""),
        vitrine=page_vitrine_checklist(page),
    )


@partners_bp.route("/page/preview")
@partner_login_required
def page_preview():
    """Aperçu privé de la page (obligatoire pour le compte test invisible)."""
    import config as site_config
    from admin.partner_seo import build_public_page_context
    from admin.partner_portal_service import page_public_highlights
    from i18n_utils import lang_url

    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    if not partner_page_can_preview(page) and not (page and (page.get("overview_html") or page.get("title"))):
        flash("Aucune page à prévisualiser — vérifiez d'abord votre page.", "error")
        return redirect(url_for("partners.page_edit"))
    lang = get_lang()
    slug = (page.get("slug") or "").strip()
    canonical = site_config.SITE_URL.rstrip("/") + (
        lang_url("partner_public", lang, slug=slug) if slug else request.path
    )
    try:
        ctx = build_public_page_context(page, partner, lang, canonical_url=canonical)
    except Exception:
        ctx = {
            "profile_badge": PROFILE_TYPE_LABELS.get(partner.get("profile_type"), "Partenaire"),
            "profile_label": PROFILE_TYPE_LABELS.get(partner.get("profile_type"), "Partenaire"),
            "meta_keywords": "",
            "maillage_links": [],
            "related_partners": [],
            "json_ld_schemas": [],
            "og_image": page.get("image_url") or None,
            "og_image_alt": page.get("title") or "",
            "partner_city": (page.get("extra") or {}).get("city") or partner.get("city") or "",
            "partner_languages": (partner.get("languages") or "").strip(),
            "partner_highlights": page_public_highlights(page),
        }
    return render_template(
        "partner_public.html",
        page=page,
        partner=partner,
        meta_title=(page.get("seo_title") or page.get("title") or "Aperçu"),
        meta_description=page.get("seo_description") or page.get("tagline") or "",
        is_private_preview=True,
        **ctx,
    )


@partners_bp.route("/page/review")
@partner_login_required
def page_review():
    partner = current_partner()
    is_hidden = is_hidden_test_partner(partner)
    page = get_page_by_partner(partner["id"])
    job_token = _sync_job_token(page, session.get(_JOB_KEY))
    job_status = draft_store.status(job_token) if job_token else {"status": "missing", "error": "", "phase": ""}
    page, job_status, show_loader = _resolve_review_page(partner["id"], page, job_status)
    publication = partner_page_publication(page, is_hidden=is_hidden)

    return render_template(
        "partners/page_review.html",
        partner=partner,
        page=page,
        page_fixes=get_page_fixes(page),
        job_status=job_status,
        show_loader=show_loader,
        can_publish=partner_page_has_publishable_content(page),
        publication=publication,
        workflow=partner_page_workflow(page, publication=publication, is_hidden=is_hidden),
        is_hidden_account=is_hidden,
        page_status_labels=PAGE_STATUS_LABELS,
        ai_ready=ai_client.is_configured(),
    )


@partners_bp.route("/page/publish", methods=["POST"])
@partner_login_required
def page_publish():
    partner = current_partner()
    is_hidden = is_hidden_test_partner(partner)
    try:
        page = publish_partner_page(partner["id"])
        if is_hidden:
            flash("Page publiée — visible en aperçu privé (compte test, hors site public).", "success")
        else:
            flash("Votre page est en ligne sur insidevietnamtravel.fr !", "success")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("partners.page_review"))
    return redirect(url_for("partners.dashboard"))


@partners_bp.route("/page/apply-fixes", methods=["POST"])
@partner_login_required
def page_apply_fixes():
    """Fallback formulaire — préférer l'API JSON côté front."""
    partner = current_partner()
    fix_id = (request.form.get("fix_id") or "").strip()
    apply_all = request.form.get("apply_all") == "1"
    try:
        result = apply_partner_fixes(
            partner["id"],
            fix_ids=[fix_id] if fix_id else None,
            apply_all=apply_all,
        )
        flash(
            f"{result['applied_count']} correction(s) appliquée(s) au brouillon — relancez la vérification quand vous êtes prêt.",
            "success",
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("partners.page_review"))
    return redirect(url_for("partners.page_edit"))


@partners_bp.route("/api/apply-fixes", methods=["POST"])
@partner_login_required
def api_apply_fixes():
    partner = current_partner()
    payload = request.get_json(silent=True) or {}
    fix_id = (payload.get("fix_id") or request.form.get("fix_id") or "").strip()
    apply_all = bool(payload.get("apply_all")) or request.form.get("apply_all") == "1"
    try:
        result = apply_partner_fixes(
            partner["id"],
            fix_ids=[fix_id] if fix_id else None,
            apply_all=apply_all,
        )
        return jsonify({"ok": True, **result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@partners_bp.route("/api/page-fixes")
@partner_login_required
def api_page_fixes():
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    fixes = get_page_fixes(page)
    extra = (page or {}).get("extra") or {}
    return jsonify({
        "ok": True,
        "fixes": fixes,
        "draft": {
            "pitch": extra.get("pitch") or "",
            "highlights": extra.get("highlights") or "",
            "offer_details": extra.get("offer_details") or "",
            "city": extra.get("city") or "",
            "contact_note": extra.get("contact_note") or "",
        },
    })


@partners_bp.route("/page/retry-ai", methods=["POST"])
@partner_login_required
def page_retry_ai():
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    if not page:
        flash("Créez d'abord votre brouillon.", "error")
        return redirect(url_for("partners.page_edit"))
    if not ai_client.is_configured():
        flash("Génération IA indisponible — contactez l'équipe.", "error")
        return redirect(url_for("partners.page_edit"))

    token = _sync_job_token(page, session.get(_JOB_KEY))
    if token and draft_store.status(token).get("status") == "running":
        flash("Analyse déjà en cours.", "success")
        return redirect(url_for("partners.page_review"))

    if page.get("status") == "ai_review":
        release_page_from_ai_review(partner["id"])

    try:
        _start_page_job(partner["id"])
        flash("Analyse relancée — patientez quelques instants.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("partners.page_edit"))
    return redirect(url_for("partners.page_review"))


@partners_bp.route("/api/page-review-state")
@partner_login_required
def api_page_review_state():
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    job_token = _sync_job_token(page, session.get(_JOB_KEY))
    job = draft_store.status(job_token) if job_token else {"status": "missing", "error": "", "phase": ""}
    page, job, _show_loader = _resolve_review_page(partner["id"], page, job)
    ps = (page or {}).get("status") or "none"
    return jsonify({
        "job": job,
        "page_status": ps,
        "page_ready": ps in ("published", "rejected", "approved"),
        "page_has_content": partner_page_has_publishable_content(page),
    })


@partners_bp.route("/api/page-job-status")
@partner_login_required
def api_page_job_status():
    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    token = _sync_job_token(page, session.get(_JOB_KEY))
    return jsonify(draft_store.status(token))


@partners_bp.route("/api/page-job-poll")
@partner_login_required
def api_page_job_poll():
    """Attente légère côté serveur pour simplifier le front."""
    import time

    partner = current_partner()
    page = get_page_by_partner(partner["id"])
    token = _sync_job_token(page, session.get(_JOB_KEY))
    if not token:
        return jsonify({"status": "missing"})
    for _ in range(60):
        st = draft_store.status(token)
        if st.get("status") in ("done", "error", "missing"):
            if st.get("status") == "done":
                session.pop(_JOB_KEY, None)
            return jsonify(st)
        time.sleep(1.5)
    return jsonify(draft_store.status(token))
