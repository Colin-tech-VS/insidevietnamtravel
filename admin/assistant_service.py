"""IA interne « Linh » 🧭 — copilote développement & SEO de l'admin.

Différente de Mai (widget public pour les voyageurs) : Linh conseille l'ADMIN sur
l'évolution du site — détection de problèmes, améliorations, idées de contenus,
priorités et calendrier, toujours avec un objectif SEO. Elle connaît :
- toutes les pages /admin (inventaire DYNAMIQUE depuis l'url_map : une nouvelle
  page admin apparaît automatiquement dans sa connaissance) ;
- l'état réel du site (articles, destinations, analytics, SEO, GEO/LLM,
  affiliation, revenus, newsletter, avis, contact, partenariats CRM, portail
  partenaire self-service, emails trackés, configuration IA/Facebook/GSC).

Elle peut aussi AGIR (tout ce que l'admin peut faire) : générer un guide, une
destination, une newsletter ou un post Facebook, ajouter des points sur la
carte (restaurants, hôtels, activités…) — via les mêmes jobs en tâche de
fond que l'admin (draft_store, mêmes tokens de session : le brouillon apparaît
aussi dans la page admin correspondante). Toute PUBLICATION (site, newsletter,
réseaux sociaux) exige une confirmation explicite de l'admin : l'action est mise
en attente côté serveur et n'est exécutée qu'après clic sur « Confirmer ».
"""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
from datetime import date, datetime

from flask import current_app, session

# ── Actions en attente de confirmation (mémoire process, comme draft_store) ──
_PENDING_LOCK = threading.Lock()
_PENDING: dict[str, dict] = {}
_PENDING_TTL = 900  # 15 min pour confirmer, sinon l'action expire

# Jobs d'actions lourdes (ex. update_image) — hors requête HTTP pour éviter le timeout
# du routeur Scalingo (~60 s) quand téléchargement + Pixabay + WebP s'enchaînent.
_ACTION_JOB_LOCK = threading.Lock()
_ACTION_JOBS: dict[str, dict] = {}
_ACTION_JOB_TTL = 3600

# Tokens de confirmation mémorisés en session : un simple « oui » dans le chat
# exécute la dernière action en attente, sans repasser par le modèle.
_SESSION_PENDING_KEY = "linh_pending_tokens"

ASSISTANT_NAME = "Linh"

_AFFIRM_STARTS = (
    "oui", "ouais", "yes", "yep", "ok", "okay", "d'accord", "daccord",
    "parfait", "nickel", "tres bien", "très bien", "c'est bon", "cest bon",
    "go", "vas-y", "vas y", "vasy", "allez-y", "allez y", "allons-y", "fonce",
    "lance", "valide", "je valide", "confirme", "je confirme", "confirmé",
    "fais-le", "fais le", "fais-la", "fais la", "do it", "envoie", "applique",
    "publie", "execute", "exécute", "c'est parti", "cest parti", "banco",
    "carrément", "carrement",
)
_NEGATION_WORDS = {
    "pas", "non", "mais", "sauf", "annule", "attends", "attend", "stop",
    "plutot", "plutôt", "cancel", "finalement", "jamais",
}
_CANCEL_STARTS = (
    "non", "annule", "annuler", "cancel", "stop", "laisse tomber",
    "abandonne", "surtout pas", "n'envoie pas", "ne publie pas", "pas maintenant",
)


def _is_affirmation(message: str) -> bool:
    """« oui », « ok vas-y », « je confirme »… : l'admin valide la proposition."""
    msg = (message or "").strip().lower().rstrip(" !.👍✅🚀")
    if not msg or len(msg) > 80:
        return False
    words = set(re.findall(r"[a-zà-ÿ']+", msg))
    if words & _NEGATION_WORDS:
        return False
    return any(
        msg == s or msg.startswith(s + " ") or msg.startswith(s + ",")
        for s in _AFFIRM_STARTS
    )


def _is_cancellation(message: str) -> bool:
    msg = (message or "").strip().lower().rstrip(" !.")
    if not msg or len(msg) > 60:
        return False
    return any(
        msg == s or msg.startswith(s + " ") or msg.startswith(s + ",")
        for s in _CANCEL_STARTS
    )


def _remember_pending(token: str) -> None:
    try:
        tokens = list(session.get(_SESSION_PENDING_KEY) or [])
        tokens.append(token)
        session[_SESSION_PENDING_KEY] = tokens[-5:]
    except Exception:  # noqa: BLE001 — hors contexte requête (tests, jobs)
        pass


def _pop_session_pending() -> str | None:
    """Dernier token de confirmation encore valide mémorisé en session."""
    try:
        tokens = list(session.get(_SESSION_PENDING_KEY) or [])
    except Exception:  # noqa: BLE001
        return None
    if not tokens:
        return None
    found = None
    with _PENDING_LOCK:
        _prune_pending()
        for token in reversed(tokens):
            if token in _PENDING:
                found = token
                break
    try:
        session[_SESSION_PENDING_KEY] = [t for t in tokens if t != found] if found else []
    except Exception:  # noqa: BLE001
        pass
    return found

SUGGESTIONS = [
    "Fais un audit complet du site",
    "Quelles pages créer en priorité pour le SEO ?",
    "Cherche sur internet les tendances voyage Vietnam du moment",
    "Génère un guide SEO sur une ville peu couverte",
    "Prépare un post Facebook sur notre meilleure page",
]

# Notes métier par page admin — complétées dynamiquement par l'url_map pour que
# toute NOUVELLE page admin soit connue de Linh sans modifier ce fichier.
_ADMIN_PAGE_NOTES = {
    "admin.dashboard": ("Dashboard", "Vue d'ensemble : trafic, revenus, recommandations, choix du moteur IA (Groq/Mistral)."),
    "admin.guides": ("Guides IA", "Génération d'articles SEO par IA (ville + sujet + type), amélioration IA, rédaction manuelle, publication sur /blog."),
    "admin.seo_pages_admin": ("Pages SEO", "Créer des landing /seo/slug en 3 clics : idées prêtes → Générer → Publier. Plusieurs pages possible (sélection ou « Proposer 6 pages »). Linh peut aussi générer/publier."),
    "admin.destinations_admin": ("Destinations", "Création/édition des pages destinations (IA ou manuel), images WebP, choix de la section Nord/Centre/Sud, publication sur /<slug>."),
    "admin.map_admin": ("Carte", "Points d'intérêt et pins affiliés (hôtels, activités) sur les cartes interactives des destinations."),
    "admin.newsletter_admin": ("Newsletter", "Composition d'emails (IA ou manuel), envoi test / abonné / tous, gestion des abonnés, contact direct des partenaires."),
    "admin.social": ("Réseaux sociaux", "Publication multi-réseaux avec rédaction IA adaptée et suivi UTM : Facebook, Pinterest, Reddit, Telegram, X (Twitter), Threads, Instagram (TikTok : audit API requis). Configuration des connexions API de chaque réseau."),
    "admin.partnerships": ("Partenariats CRM", "Prospection partenaires (influenceurs, blogueurs, guides, agences) : recherche IA d'influenceurs voyage Vietnam avec extraction d'email, statuts de contact (à contacter → actif), envoi d'emails via la page Newsletter avec tracking ouvertures/clics."),
    "admin.partner_portal_admin": ("Espace partenaire", "Portail self-service : inscriptions via /devenir-partenaire, comptes partenaires, création de fiche par l'IA, vérification éditoriale, publication sur /partenaire/slug. Modération : suspendre, publier, refuser, dépublier."),
    "admin.contact_admin": ("Contact", "Messages reçus via le formulaire de contact public (lu / suppression)."),
    "admin.reviews_admin": ("Avis", "Gestion des témoignages voyageurs affichés sur le site."),
    "admin.affiliates": ("Affiliation", "IDs partenaires (Booking, Agoda, GetYourGuide, eSIM…), vérification du tracking, stats de clics."),
    "admin.revenue": ("Revenus", "Saisie des commissions reçues, estimé vs confirmé, historique."),
    "admin.analytics": ("Analytics", "Trafic (7/30/90 j), temps réel, SEO organique, GEO (trafic depuis ChatGPT/Perplexity…), pays/villes, profils visiteurs, stats Mai AI (dont questions posées)."),
    "admin.gsc": ("Google Search Console", "Connexion OAuth GSC, performances SEO (requêtes, pages, CTR), propriété verrouillée insidevietnamtravel.fr."),
}


def is_enabled() -> bool:
    from admin import ai_client
    return ai_client.is_configured()


# ── Inventaire dynamique des pages admin ─────────────────────────────────────

def build_admin_inventory() -> list[dict]:
    """Toutes les pages /admin (GET, sans paramètre) — y compris les futures."""
    items: list[dict] = []
    seen: set[str] = set()
    try:
        rules = list(current_app.url_map.iter_rules())
    except Exception:
        rules = []
    for rule in rules:
        ep = rule.endpoint
        if not ep.startswith("admin.") or ep in seen:
            continue
        if "GET" not in (rule.methods or set()) or rule.arguments:
            continue
        path = rule.rule
        if "/api/" in path or path.endswith(("/login", "/logout", "/preview")):
            continue
        seen.add(ep)
        label, note = _ADMIN_PAGE_NOTES.get(ep, (path.rsplit("/", 1)[-1] or "admin", "Page admin (nouvelle — non documentée)."))
        items.append({"endpoint": ep, "label": label, "url": path, "note": note})
    items.sort(key=lambda x: x["url"])
    return items


# ── Snapshot de l'état du site ───────────────────────────────────────────────

def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _article_inventory() -> list[dict]:
    from admin.store import get_articles

    out = []
    for a in get_articles("fr"):
        content = a.get("content") or ""
        words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", content)))
        internal_links = len(re.findall(r'href="(?:https?://[^"]*?)?/(?!/)[^"]*"', content))
        out.append({
            "slug": a.get("slug", ""),
            "title": a.get("title", ""),
            "category": a.get("category", ""),
            "city": a.get("city", ""),
            "date": a.get("date", ""),
            "words": words,
            "internal_links": internal_links,
            "has_image": bool(a.get("image")),
            "has_excerpt": bool((a.get("excerpt") or "").strip()),
        })
    return out


def build_site_snapshot() -> dict:
    """État factuel du site — chaque bloc est best-effort (jamais bloquant)."""
    from admin import db
    from admin.affiliate_service import build_affiliate_summary, build_site_analytics, compute_estimated_commission
    from admin.store import count_newsletter_subscribers, get_destinations_dict, get_reviews
    from admin import ai_client

    stats = _safe(lambda: build_site_analytics(30), {})
    aff = _safe(lambda: build_affiliate_summary(30), {})
    revenue = _safe(db.get_revenue_stats, {"total": 0, "month_total": 0, "entries": []})
    dests = _safe(get_destinations_dict, {})
    reviews = _safe(get_reviews, [])

    snapshot = {
        "today": date.today().isoformat(),
        "articles": _safe(_article_inventory, []),
        "destinations": [
            {
                "slug": s,
                "name": d.get("name", s),
                "region": _dest_region(s, d),
                "has_image": bool(d.get("image")),
                "has_meta": bool(d.get("meta_description")),
                "tips": len(d.get("tips") or []),
                "hotels": len(d.get("hotels") or []),
            }
            for s, d in dests.items()
        ],
        "traffic": {
            "views_30d": stats.get("unique_visitors_period", 0),
            "clicks_30d": stats.get("clicks_period", 0),
            "active_now": stats.get("active_visitors", 0),
            "top_pages_24h": (stats.get("top_pages") or [])[:8],
            "countries": [c for c in (stats.get("countries") or [])[:5]],
        },
        "seo": stats.get("seo") or {},
        "geo": stats.get("geo") or {},
        "affiliates": {
            "configured": sum(1 for p in aff.get("partners", []) if p.get("configured")),
            "total": len(aff.get("partners", [])),
            "unconfigured": [p["name"] for p in aff.get("partners", []) if not p.get("configured")][:8],
            "clicks_30d": aff.get("clicks_period", 0),
            "estimated_eur_30d": aff.get("estimated_eur", 0),
            "top_partners": (aff.get("clicks_by_partner") or [])[:5],
        },
        "revenue": {
            "total_eur": revenue.get("total", 0),
            "month_eur": revenue.get("month_total", 0),
            "estimated_30d": _safe(lambda: compute_estimated_commission(30), 0),
        },
        "newsletter": {
            "subscribers": _safe(count_newsletter_subscribers, 0),
            "smtp_ok": _safe(_smtp_ok, False),
        },
        "contact_unread": _safe(_contact_unread, 0),
        "reviews": {
            "count": len(reviews),
            "avg": round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 1) if reviews else 0,
        },
        "partnerships": _safe(_partnership_stats, {}),
        "partner_portal": _safe(_partner_portal_snapshot, {}),
        "email_tracking": _safe(_email_tracking_snapshot, {}),
        "config": {
            "ai_provider": _safe(ai_client.provider, "?"),
            "ai_status": _safe(ai_client.provider_status, {}),
            "facebook_ok": _safe(_facebook_ok, False),
            "social_networks": _safe(_connected_networks, []),
        },
    }
    return snapshot


def _dest_region(slug: str, dest: dict) -> str:
    from data.trip_planner import resolve_region
    return resolve_region(slug, dest)


def _smtp_ok() -> bool:
    from admin.newsletter_service import is_smtp_configured
    return is_smtp_configured()


def _contact_unread() -> int:
    from admin.contact_service import count_unread_messages
    return count_unread_messages()


def _facebook_ok() -> bool:
    from admin import facebook_service as fb
    return fb.is_configured()


def _connected_networks() -> list[str]:
    from admin import social_networks as sn
    return [n["key"] for n in sn.NETWORKS
            if n.get("publishable") and sn.is_network_configured(n["key"])]


def _partnership_stats() -> dict:
    from admin.partners_service import partnership_stats
    return partnership_stats()


def _partner_portal_snapshot() -> dict:
    from admin.partner_portal_service import (
        PAGE_STATUS_LABELS,
        PROFILE_TYPE_LABELS,
        get_account_by_id,
        list_accounts,
        list_pages,
        portal_stats,
    )

    stats = portal_stats()
    accounts = list_accounts()
    pages = list_pages()
    published = []
    for pg in [p for p in pages if p.get("status") == "published"][:20]:
        acc = get_account_by_id(pg.get("partner_id")) or {}
        published.append({
            "slug": pg.get("slug", ""),
            "title": pg.get("title") or acc.get("business_name") or acc.get("email", ""),
            "city": ((pg.get("extra") or {}).get("city") or acc.get("city") or "").strip(),
            "type": PROFILE_TYPE_LABELS.get(acc.get("profile_type"), ""),
        })
    pending = []
    for pg in [p for p in pages if p.get("status") != "published"][:15]:
        acc = get_account_by_id(pg.get("partner_id")) or {}
        pending.append({
            "slug": pg.get("slug", ""),
            "title": pg.get("title") or acc.get("business_name") or acc.get("email", ""),
            "status": PAGE_STATUS_LABELS.get(pg.get("status"), pg.get("status", "")),
            "email": acc.get("email", ""),
        })
    return {
        **stats,
        "accounts_active": sum(1 for a in accounts if a.get("status") == "active"),
        "published_pages": published,
        "pending_pages": pending,
    }


def _email_tracking_snapshot() -> dict:
    from admin.email_tracking_service import get_analytics_summary
    return get_analytics_summary()


# ── Audit déterministe (bugs / manques / SEO) ────────────────────────────────

def _finding(severity: str, icon: str, title: str, detail: str, url: str = "") -> dict:
    return {"severity": severity, "icon": icon, "title": title, "detail": detail, "url": url}


def run_audit(snapshot: dict | None = None) -> list[dict]:
    """Contrôles factuels — la base que Linh enrichit ensuite avec l'IA."""
    snap = snapshot or build_site_snapshot()
    findings: list[dict] = []

    cfg = snap.get("config", {})
    if not any((cfg.get("ai_status") or {}).values()):
        findings.append(_finding(
            "haute", "🔑", "Aucune clé IA configurée",
            "Sans GROQ_API_KEY ni MISTRAL_API_KEY, la génération de contenus et le chat Mai sont indisponibles.",
            "/admin",
        ))

    articles = snap.get("articles", [])
    if len(articles) < 5:
        findings.append(_finding(
            "haute", "📚", f"Seulement {len(articles)} article(s) publié(s)",
            "Visez 10+ guides longue traîne (visa, budget, itinéraires, saisons) — c'est le levier SEO n° 1.",
            "/admin/guides",
        ))
    last_date = max((a.get("date") or "" for a in articles), default="")
    if last_date:
        try:
            days_since = (date.today() - datetime.strptime(last_date[:10], "%Y-%m-%d").date()).days
            if days_since > 14:
                findings.append(_finding(
                    "moyenne", "🗓", f"Aucun article depuis {days_since} jours",
                    "Google favorise les sites actifs : publiez au moins 1 guide par semaine.",
                    "/admin/guides",
                ))
        except ValueError:
            pass

    thin = [a for a in articles if a.get("words", 0) < 400]
    if thin:
        findings.append(_finding(
            "moyenne", "✂️", f"{len(thin)} article(s) trop court(s) (<400 mots)",
            "Contenu fin = mauvais signal SEO. À enrichir : " + ", ".join(a["slug"] for a in thin[:4]) + ".",
            "/admin/guides",
        ))
    no_links = [a for a in articles if a.get("internal_links", 0) == 0]
    if no_links:
        findings.append(_finding(
            "moyenne", "🔗", f"{len(no_links)} article(s) sans lien interne",
            "Le maillage interne distribue le jus SEO : " + ", ".join(a["slug"] for a in no_links[:4]) + ".",
            "/admin/guides",
        ))
    no_img = [a for a in articles if not a.get("has_image")]
    if no_img:
        findings.append(_finding(
            "moyenne", "🖼", f"{len(no_img)} article(s) sans image",
            "Image manquante = pas de vignette dans Discover/partages : " + ", ".join(a["slug"] for a in no_img[:4]) + ".",
            "/admin/guides",
        ))

    dests = snap.get("destinations", [])
    d_no_meta = [d for d in dests if not d.get("has_meta")]
    if d_no_meta:
        findings.append(_finding(
            "moyenne", "🏷", f"{len(d_no_meta)} destination(s) sans meta description",
            "Meta absente = snippet Google improvisé : " + ", ".join(d["slug"] for d in d_no_meta[:5]) + ".",
            "/admin/destinations",
        ))
    d_no_img = [d for d in dests if not d.get("has_image")]
    if d_no_img:
        findings.append(_finding(
            "moyenne", "🖼", f"{len(d_no_img)} destination(s) sans image",
            ", ".join(d["slug"] for d in d_no_img[:5]) + ".",
            "/admin/destinations",
        ))

    traffic = snap.get("traffic", {})
    seo = snap.get("seo", {})
    views = traffic.get("views_30d", 0)
    organic = seo.get("total_organic_views", 0)
    share = seo.get("organic_share_pct", 0)
    if views > 20 and organic == 0:
        findings.append(_finding(
            "haute", "🔍", "Aucun trafic organique détecté",
            "Soumettez le sitemap dans Google Search Console et renforcez le maillage interne.",
            "/admin/analytics",
        ))
    elif views > 50 and share < 15:
        findings.append(_finding(
            "moyenne", "📉", f"SEO à {share}% du trafic seulement",
            f"{organic} visites organiques sur 30 j — optimisez titres/meta et ciblez la longue traîne « voyage Vietnam ».",
            "/admin/analytics",
        ))

    geo = snap.get("geo", {})
    if views > 0 and geo.get("total_ai_views", 0) == 0:
        findings.append(_finding(
            "info", "🤖", "Pas encore de trafic depuis les IA (ChatGPT, Perplexity…)",
            "Le fichier /llms.txt est en place — partagez vos guides et enrichissez les FAQ avec des questions directes.",
            "/admin/analytics",
        ))

    aff = snap.get("affiliates", {})
    if aff.get("configured", 0) < aff.get("total", 0):
        missing = aff.get("unconfigured", [])
        findings.append(_finding(
            "haute", "◇", f"{len(missing)} partenaire(s) affilié(s) non configuré(s)",
            "Priorité Booking/Agoda : " + ", ".join(missing[:5]) + ".",
            "/admin/affiliates",
        ))
    if views > 50 and aff.get("clicks_30d", 0) == 0:
        findings.append(_finding(
            "haute", "🛑", "Du trafic mais zéro clic affilié",
            "Vérifiez la visibilité des CTA et des pins de carte sur les pages les plus vues.",
            "/admin/affiliates",
        ))

    nl = snap.get("newsletter", {})
    if nl.get("subscribers", 0) > 0 and not nl.get("smtp_ok"):
        findings.append(_finding(
            "moyenne", "✉️", f"{nl['subscribers']} abonné(s) mais SMTP non configuré",
            "Impossible d'envoyer la newsletter — configurez les variables SMTP.",
            "/admin/newsletter",
        ))

    if not snap.get("config", {}).get("facebook_ok"):
        findings.append(_finding(
            "info", "📣", "Facebook non connecté",
            "Connectez la page (ID + token) pour publier les posts générés et capter du trafic social.",
            "/admin/social",
        ))

    if snap.get("contact_unread", 0) > 0:
        findings.append(_finding(
            "info", "📬", f"{snap['contact_unread']} message(s) contact non lu(s)",
            "Répondre vite améliore la confiance (et parfois des backlinks spontanés).",
            "/admin/contact",
        ))

    rev = snap.get("revenue", {})
    if rev.get("estimated_30d", 0) > max(rev.get("month_eur", 0), 0) * 1.5 and rev.get("estimated_30d", 0) > 0:
        findings.append(_finding(
            "info", "€", "Commissions estimées > enregistrées",
            f"~{rev['estimated_30d']:.0f} € estimés sur 30 j — pensez à saisir les paiements reçus.",
            "/admin/revenue",
        ))

    order = {"haute": 0, "moyenne": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f["severity"], 3))
    return findings


# ── Formatage du contexte pour le prompt ─────────────────────────────────────

def _format_snapshot(snap: dict) -> str:
    seo = snap.get("seo", {})
    geo = snap.get("geo", {})
    t = snap.get("traffic", {})
    aff = snap.get("affiliates", {})
    lines = [
        f"Date: {snap.get('today')}",
        f"Trafic 30j: {t.get('views_30d', 0)} vues, {t.get('clicks_30d', 0)} clics affiliés, {t.get('active_now', 0)} visiteur(s) actif(s)",
        "Top pages 24h: " + (", ".join(f"{p.get('path')}({p.get('c')})" for p in t.get("top_pages_24h", [])[:6]) or "aucune"),
        f"SEO: {seo.get('total_organic_views', 0)} vues organiques ({seo.get('organic_share_pct', 0)}%)"
        + (" — top: " + ", ".join(p.get("path", "") for p in (seo.get("top_organic_pages") or [])[:3]) if seo.get("top_organic_pages") else ""),
        f"GEO/LLM: {geo.get('total_ai_views', 0)} vues depuis des IA ({geo.get('ai_share_pct', 0)}%)",
        f"Affiliation: {aff.get('configured', 0)}/{aff.get('total', 0)} partenaires configurés, "
        f"{aff.get('clicks_30d', 0)} clics 30j, ~{aff.get('estimated_eur_30d', 0)} € estimés"
        + (" — manquants: " + ", ".join(aff.get("unconfigured", [])[:5]) if aff.get("unconfigured") else ""),
        f"Revenus: {snap.get('revenue', {}).get('total_eur', 0)} € total, {snap.get('revenue', {}).get('month_eur', 0)} € ce mois",
        f"Newsletter: {snap.get('newsletter', {}).get('subscribers', 0)} abonné(s), SMTP {'OK' if snap.get('newsletter', {}).get('smtp_ok') else 'NON configuré'}",
        f"Avis: {snap.get('reviews', {}).get('count', 0)} (moyenne {snap.get('reviews', {}).get('avg', 0)}/5) — Contact non lus: {snap.get('contact_unread', 0)}",
        f"Config: moteur IA {snap.get('config', {}).get('ai_provider')}, Facebook {'connecté' if snap.get('config', {}).get('facebook_ok') else 'NON connecté'}"
        + ", réseaux sociaux connectés: "
        + (", ".join(snap.get("config", {}).get("social_networks") or []) or "aucun (voir /admin/social)"),
        "Partenariats CRM (/admin/partnerships): "
        + (f"{snap.get('partnerships', {}).get('total', 0)} contact(s) "
           f"({snap.get('partnerships', {}).get('with_email', 0)} avec email) — "
           + ", ".join(f"{k}:{v}" for k, v in (snap.get('partnerships', {}).get('by_status') or {}).items() if v)
           if snap.get("partnerships", {}).get("total") else "aucun contact CRM enregistré"),
        "Espace partenaire self-service (/admin/partner-portal, /devenir-partenaire): "
        + (
            f"{snap.get('partner_portal', {}).get('accounts', 0)} compte(s) "
            f"({snap.get('partner_portal', {}).get('accounts_active', 0)} actifs), "
            f"{snap.get('partner_portal', {}).get('pages_published', 0)} page(s) publiée(s) "
            f"(/partenaire/slug), {snap.get('partner_portal', {}).get('pages_pending', 0)} en attente, "
            f"{snap.get('partner_portal', {}).get('pages_rejected', 0)} refusée(s)"
            if snap.get("partner_portal", {}).get("accounts") is not None
            else "portail partenaire actif"
        ),
        "Emails trackés (newsletter & partenariat): "
        + (
            f"{snap.get('email_tracking', {}).get('total_sends', 0)} envoi(s), "
            f"{snap.get('email_tracking', {}).get('total_opens', 0)} ouverture(s), "
            f"{snap.get('email_tracking', {}).get('total_clicks', 0)} clic(s)"
            if snap.get("email_tracking") else "suivi email actif via /admin/newsletter"
        ),
    ]
    arts = snap.get("articles", [])
    lines.append(f"Articles publiés ({len(arts)}):")
    for a in arts[:25]:
        flags = []
        if a.get("words", 0) < 400:
            flags.append("court")
        if not a.get("internal_links"):
            flags.append("0 lien interne")
        if not a.get("has_image"):
            flags.append("sans image")
        lines.append(
            f"  - /blog/{a['slug']} « {a['title']} » [{a.get('category', '?')}, {a.get('city', '?')}, "
            f"{a.get('words', 0)} mots, {a.get('date', '?')}]" + (f" ⚠ {', '.join(flags)}" if flags else "")
        )
    dests = snap.get("destinations", [])
    lines.append(
        f"Destinations publiées ({len(dests)}, avec leur région nord/centre/sud): "
        + ", ".join(f"{d['slug']} [{d.get('region', '?')}]" for d in dests)
    )
    pp = snap.get("partner_portal") or {}
    pub = pp.get("published_pages") or []
    if pub:
        lines.append(
            "Fiches partenaires publiques: "
            + ", ".join(
                f"/partenaire/{p['slug']} « {p['title']} » ({p.get('type', '?')}, {p.get('city', '?')})"
                for p in pub[:12]
            )
        )
    pend = pp.get("pending_pages") or []
    if pend:
        lines.append(
            "Pages partenaires en modération: "
            + ", ".join(f"{p.get('title', p.get('slug', '?'))} [{p.get('status', '?')}]" for p in pend[:8])
        )
    return "\n".join(lines)


def _format_inventory(inventory: list[dict]) -> str:
    return "\n".join(f"- {it['url']} « {it['label']} » : {it['note']}" for it in inventory)


def _format_findings(findings: list[dict]) -> str:
    if not findings:
        return "(aucun problème détecté par l'audit automatique)"
    return "\n".join(f"- [{f['severity']}] {f['title']} — {f['detail']}" for f in findings)


def _format_public_pages() -> str:
    from admin.social_ai import page_inventory
    items = page_inventory("fr")
    by_group: dict[str, list[str]] = {}
    for it in items:
        by_group.setdefault(it["group"], []).append(f"{it['id']} ({it['label']})")
    return "\n".join(f"- {g}: " + ", ".join(ids) for g, ids in by_group.items())


# ── Prompt système ───────────────────────────────────────────────────────────

def _system_prompt() -> str:
    from data.vietnam_cities import ALL_CITY_VALUES

    cities = ", ".join(ALL_CITY_VALUES)
    try:
        from admin.store import get_categories
        blog_categories = ", ".join(get_categories().keys())
    except Exception:  # noqa: BLE001
        blog_categories = "practical, food, itinerary, budget"
    return (
        "Tu es Linh 🧭, le copilote IA INTERNE de l'admin d'Inside Vietnam Travel "
        "(guide de voyage Vietnam, FR/EN). Tu n'es PAS Mai (l'assistante publique des "
        "voyageurs) : tu parles uniquement à l'ADMINISTRATEUR du site, dans /admin. "
        "Ta mission : faire ÉVOLUER le site — détecter bugs et manques, proposer des "
        "améliorations concrètes, des idées de nouvelles pages/contenus pertinentes, "
        "dire quoi faire, quoi ajouter et QUAND, avec TOUJOURS le SEO comme objectif "
        "central (trafic organique Google + visibilité GEO dans ChatGPT/Perplexity). "
        "Tu connais par cœur toutes les pages /admin (bloc PAGES ADMIN), l'état réel du "
        "site (bloc ÉTAT DU SITE) et les problèmes détectés (bloc AUDIT). Appuie-toi sur "
        "ces données chiffrées, jamais sur des inventions. "
        "ANTI-HALLUCINATION (règles critiques) : "
        "1) Réponds d'abord, directement et précisément, au MESSAGE DE L'ADMIN (dernier "
        "bloc) — ne récite pas l'audit ou les stats si la question porte sur autre chose. "
        "2) Toute affirmation factuelle (chiffre, URL, page, fonctionnalité, donnée externe) "
        "doit provenir des blocs de contexte fournis ou des RÉSULTATS WEB — n'invente JAMAIS "
        "rien, même de plausible. "
        "3) Si l'info demandée n'est pas dans ton contexte : utilise l'outil web_search "
        "(infos externes, fraîches ou vérifiables en ligne) ou dis franchement « je n'ai "
        "pas cette donnée » en proposant comment l'obtenir. "
        "4) Si la question est ambiguë, pose UNE question de clarification au lieu de "
        "deviner. "
        "Tu peux AGIR à la place de l'admin via le champ \"tool\" : tu sais faire TOUT ce "
        "que l'admin peut faire dans /admin — générer un guide, une destination, une "
        "newsletter, un post Facebook, modifier ou améliorer par IA un guide/article ou "
        "une destination publiée (une page ou un LOT de pages en une passe), mettre à "
        "jour l'image d'un article/d'une destination "
        "(y compris cherchée et téléchargée depuis internet), ajouter des points carte, "
        "publier/envoyer. Si l'admin demande une action couverte par un outil, appelle "
        "l'outil SANS tergiverser ; s'il n'existe pas d'outil, donne le lien admin prefill. "
        "MODIFICATIONS GROUPÉES : quand l'admin demande PLUSIEURS changements similaires "
        "(ex. les 15 images de bannière des destinations, la même retouche de contenu sur "
        "tous les guides, plusieurs points de carte), traite TOUT le lot en UN SEUL appel "
        "d'outil (update_images avec un item par image, update_pages avec un item par page "
        "— éditions directes ET réécritures IA, articles ET destinations mélangés —, "
        "add_map_points avec plusieurs points) — une seule confirmation pour "
        "l'ensemble, jamais une demande par élément. Tout ce que tu sais faire sur UNE page, "
        "tu sais le faire sur PLUSIEURS pages en une passe. "
        "CONFIRMATIONS — règles strictes : "
        "1) Ne demande JAMAIS toi-même de confirmation dans le texte (« veux-tu que je… ? », "
        "« es-tu sûr ? ») : appelle directement l'outil, le SYSTÈME affiche lui-même UNE carte "
        "de confirmation unique. UNE SEULE confirmation suffit, ne redemande jamais. "
        "2) Quand l'admin confirme une action en attente (carte ou simple « oui »), le système "
        "l'exécute automatiquement — toi, si l'admin ACCEPTE une action que tu viens de proposer "
        "(« oui », « ok », « vas-y », « fais-le », « ajoute-les »), tu DOIS appeler IMMÉDIATEMENT "
        "l'outil correspondant dans cette réponse. "
        "3) Ne dis JAMAIS qu'une action est faite ou en cours si le champ \"tool\" est null, "
        "et n'affirme jamais avoir publié sans confirmation. "
        "Après une recherche web, tu peux enchaîner directement un outil d'action (ex. "
        "add_map_points avec les restaurants trouvés et leurs adresses). "
        f"VILLES autorisées pour generate_guide/generate_destination : {cities}. "
        f"generate_seo_page : city optionnelle (vide = Vietnam général).\n"
        f"CATÉGORIES blog existantes (clé du champ category) : {blog_categories}. "
        "RÉSEAUX SOCIAUX (/admin/social) — tu les connais tous : publication multi-réseaux "
        "avec rédaction IA adaptée aux codes de chaque plateforme et suivi UTM "
        "(utm_source = réseau). Réseaux disponibles (clé network) : facebook (page existante), "
        "pinterest (n°1 planification voyage, image obligatoire), reddit (r/VietnamTravel — "
        "voyageurs très qualifiés, autopromo limitée, titre honnête sans emoji), telegram "
        "(canaux voyageurs/expats Asie SE), x (conseils rapides, 280 car.), threads "
        "(conversationnel), instagram (image obligatoire, lien non cliquable → « lien en "
        "bio »). tiktok est listé mais non publiable par API (audit TikTok 2-4 semaines). "
        "Les réseaux connectés sont dans ÉTAT DU SITE (Config) ; la connexion (clés API) se "
        "fait sur /admin/social. "
        "PARTENARIATS — deux systèmes distincts : "
        "1) CRM (/admin/partnerships) : prospection influenceurs/blogueurs avec emails, statuts, "
        "envoi d'emails partenariat via /admin/newsletter (tracking ouvertures/clics). "
        "Outils find_influencers et add_partner. "
        "2) PORTAIL PARTENAIRE (/admin/partner-portal) : comptes self-service inscrits via "
        "/devenir-partenaire, fiches créées par les partenaires, vérification IA, publication "
        "sur /partenaire/slug. Tu vois les stats et fiches dans ÉTAT DU SITE. "
        "Pour modérer (publier/refuser/suspendre), dirige l'admin vers /admin/partner-portal. "
        "Pour écrire à un contact CRM, propose /admin/newsletter?prefill=1&topic=…&email_type=partenariat. "
        "Mai (widget public) connaît les fiches partenaires publiées et la page devenir-partenaire. "
        "OUTILS disponibles (champ \"tool\", sinon null) :\n"
        '- {"name":"web_search","params":{"query":"…"}} — rechercher sur internet (DuckDuckGo) : '
        "actualités/réglementation Vietnam (visa, prix, événements), concurrence, tendances SEO, "
        "vérification de faits. Utilise-le SPONTANÉMENT dès qu'une réponse fiable exige une info "
        "absente de ton contexte, au lieu de deviner. Quand tu appelles web_search, mets dans "
        "\"message\" UNE phrase courte annonçant ta recherche (le système affiche un indicateur "
        "de chargement, exécute la recherche et te rappelle avec un bloc RÉSULTATS WEB) ; tu "
        "rédigeras alors ta réponse finale en citant les URLs sources. Ne dis JAMAIS que tu "
        "recherches sans appeler l'outil web_search. JAMAIS web_search pour trouver des "
        "images : utilise search_images (dédié, bien plus rapide)\n"
        '- {"name":"search_images","params":{"query":"mots-clés ANGLAIS (ex. Hoi An lanterns night)"}} — '
        "chercher des PHOTOS directement téléchargeables sur les banques d'images libres "
        "(Pixabay, Openverse, Wikimedia Commons, DuckDuckGo Images) : le système exécute la "
        "recherche et te renvoie une liste d'images candidates (URL DIRECTE image_url, "
        "dimensions, source, page d'origine). Utilise-le dès que l'admin veut TROUVER, VOIR ou "
        "CHOISIR des images, ou qu'il faut la photo d'un lieu précis ; si l'admin a demandé de "
        "REMPLACER une image, enchaîne immédiatement update_image/update_images avec "
        "l'image_url choisie (le système télécharge, optimise en WebP et remplace). "
        "Pour un simple remplacement sans choix, update_image avec query suffit (recherche auto)\n"
        '- {"name":"audit_site","params":{}} — relancer l\'audit complet et présenter les résultats\n'
        '- {"name":"generate_guide","params":{"city":"…","topic":"…","guide_type":"article blog"}} — guide SEO (job en arrière-plan)\n'
        '- {"name":"generate_seo_page","params":{"topic":"…","keywords":"mot1, mot2, mot3","city":"…","page_type":"landing"}} — une page SEO landing sur /seo/slug (job arrière-plan, SEO max)\n'
        '- {"name":"generate_seo_matrix","params":{"brief":"…","count":10,"city":"…"}} — matrice de pages SEO (clusters mots-clés) sans rédiger encore\n'
        '- {"name":"generate_seo_batch","params":{"rows":[{"topic":"…","keywords":["…"],"city":"…","page_type":"landing"}]}} — générer PLUSIEURS pages SEO d\'un coup (max 12, job long)\n'
        '- {"name":"generate_destination","params":{"city":"…","notes":"…"}} — page destination (job en arrière-plan)\n'
        '- {"name":"generate_newsletter","params":{"topic":"…","email_type":"actualite","notes":"…"}} — email newsletter (job en arrière-plan)\n'
        '- {"name":"generate_social_post","params":{"page_id":"…","brief":"…","network":"facebook|pinterest|reddit|telegram|x|threads|instagram"}} — post réseau social rédigé selon les codes du réseau choisi (network optionnel, facebook par défaut ; page_id du bloc PAGES PUBLIQUES, ou brief libre)\n'
        '- {"name":"set_destination_region","params":{"slug":"…","region":"north|central|south"}} — déplacer une destination publiée dans la colonne Nord/Centre/Sud du menu Destinations (confirmation auto)\n'
        '- {"name":"update_article","params":{"slug":"…","title":"…","meta_title":"…","meta_description":"…","excerpt":"…","content":"…","tags":["…"],"focus_keyword":"…","category":"…"}} — modifier un guide/article publié (/blog/slug) ; champs optionnels, ne passe que ceux à changer. category = clé d\'une CATÉGORIE existante (sinon crée-la d\'abord avec add_category) (confirmation auto)\n'
        '- {"name":"add_category","params":{"label_fr":"…","label_en":"…","description_fr":"…","description_en":"…","key":"…"}} — créer une catégorie de blog : page /categorie/<key> FR+EN, ajoutée automatiquement au menu du blog et au sitemap. key optionnelle (slug auto depuis label_fr) (confirmation auto)\n'
        '- {"name":"improve_article","params":{"slug":"…","instructions":"…"}} — réécrire/améliorer un guide publié par IA (SEO, clarté, maillage interne, longueur…) selon tes instructions ; job en arrière-plan après confirmation\n'
        '- {"name":"update_destination","params":{"slug":"…","tagline":"…","meta_title":"…","meta_description":"…","overview":"…","tips":["…"],"things_to_do":[{"title":"…","desc":"…"}],"region":"…"}} — modifier une page destination publiée ; champs optionnels (confirmation auto). slug = slug ÉTAT DU SITE (ex. delta-du-mekong)\n'
        '- {"name":"improve_destination","params":{"slug":"…","instructions":"…"}} — réécrire/améliorer une destination publiée par IA selon tes instructions ; job en arrière-plan après confirmation\n'
        '- {"name":"update_pages","params":{"items":[{"target":"article|destination","slug":"…","title":"…","content":"…","instructions":"…"},…]}} — modifier PLUSIEURS pages en UNE SEULE action (une seule confirmation, puis job en arrière-plan page par page). Chaque item est SOIT une édition directe (mêmes champs que update_article pour un article, que update_destination pour une destination), SOIT une réécriture IA (champ instructions, comme improve_article/improve_destination) ; articles et destinations peuvent être mélangés dans le même lot. Dès que l\'admin demande la même modification sur PLUS D\'UNE page (ex. « ajoute une FAQ à tous les guides », « réécris les meta descriptions de toutes les destinations »), utilise update_pages, JAMAIS update_article/improve_article en boucle\n'
        '- {"name":"update_image","params":{"target":"article|destination","slug":"…","image_url":"https://…","query":"…","alt":"…"}} — mettre à jour l\'image d\'UN SEUL article ou destination publiée. slug = slug ÉTAT DU SITE (ex. hue pour Huế, delta-du-mekong). Deux façons : query (mots-clés ANGLAIS, ex. « Hue imperial citadel Vietnam ») = le serveur cherche tout seul dans les banques d\'images libres (Pixabay, Openverse, Wikimedia Commons), fiable et sans URL cassée ; ou image_url = lien DIRECT (.jpg/.webp), page Wikimedia Commons /wiki/File:…, ou image_url d\'un résultat search_images — pas une page galerie HTML (pixnio, shutterstock…). alt facultatif. Le système télécharge, optimise en WebP et REMPLACE l\'image (job après confirmation)\n'
        '- {"name":"update_images","params":{"items":[{"target":"article|destination","slug":"…","query":"…","image_url":"…","alt":"…"},…]}} — mettre à jour PLUSIEURS images en UNE SEULE action (une seule confirmation, puis job en arrière-plan image par image, sans doublon de photo). Dès que l\'admin demande plus d\'une image (ex. « change les bannières de toutes les destinations »), utilise update_images, JAMAIS update_image en boucle. Raccourci : {"all_destinations":true,"query":"ambiance optionnelle (ex. sunset)"} = nouvelle bannière pour CHAQUE destination publiée. query optionnelle par item (mots-clés auto sinon)\n'
        '- {"name":"add_map_points","params":{"city":"slug ou nom de la ville","points":[{"title":"…","address":"adresse complète","kind":"restaurant","desc":"…","price_hint":"…","image_url":"https://…"}]}} — ajouter des points sur la carte interactive : restaurants, bars, hôtels, activités, lieux… kind de préférence ∈ hotel|activity|restaurant|bar|poi|service, mais tout autre type est accepté (ex. « spa », « marché nocturne ») : il est créé automatiquement avec sa couleur et sa légende ; address = adresse la plus précise possible (géocodée via OpenStreetMap), sinon « Nom, Ville » ; image_url facultative (lien DIRECT vers une photo du lieu) — sans elle une photo est cherchée automatiquement dans les banques d\'images libres (confirmation auto)\n'
        '- {"name":"update_map_images","params":{"title":"nom du point","city":"ville","image_url":"https://… ou mots-clés"}} ou {"all_missing":true} — mettre à jour la photo d\'un point existant de la carte (URL directe, mots-clés, ou vide = recherche auto), ou trouver une photo pour TOUS les points sans image (job en arrière-plan) (confirmation auto)\n'
        '- {"name":"publish_draft","params":{"kind":"article|destination|seo_page|seo_batch"}} — publier le brouillon en attente (confirmation auto)\n'
        '- {"name":"publish_facebook","params":{}} — publier le dernier post généré sur Facebook (confirmation auto)\n'
        '- {"name":"publish_social","params":{"network":"…"}} — publier le dernier post généré sur le réseau indiqué (doit être connecté sur /admin/social ; confirmation auto)\n'
        '- {"name":"send_newsletter","params":{"scope":"test","email":"…"}} ou {"scope":"all"} — envoyer la newsletter (confirmation auto)\n'
        '- {"name":"find_influencers","params":{"brief":"…"}} — chercher sur internet des influenceurs/blogueurs/créateurs voyage Vietnam ouverts aux partenariats (recherche web + lecture des pages pour extraire les EMAILS), puis les enregistrer dans /admin/partnerships au statut « à contacter » (job en arrière-plan après confirmation). brief = niche/angle souhaité (ex. « influenceurs francophones backpacking Vietnam »)\n'
        '- {"name":"add_partner","params":{"name":"…","type":"influenceur|blogueur|guide|agence|hotel|autre","email":"…","links":["https://…"],"topics":"…","notes":"…"}} — enregistrer manuellement un partenaire dans /admin/partnerships (confirmation auto)\n'
        "Ton : direct, structuré, orienté impact — un consultant produit/SEO senior. "
        "Mets en avant 2 à 5 points clés avec **double astérisques**. Termine toujours ta réponse. "
        "Les \"actions\" sont des liens internes UNIQUEMENT (URLs commençant par « / », "
        "pages admin ou pages publiques du site) ; ils s'ouvrent dans le même onglet sans "
        "fermer la conversation. Pour ouvrir une page admin avec son formulaire DÉJÀ "
        "PRÉ-REMPLI, ajoute ?prefill=1&<champ>=<valeur> à l'URL (champ = attribut name du "
        "formulaire). Exemples : /admin/map?prefill=1&title=…&address=…&kind=food&city=… · "
        "/admin/guides?prefill=1&city=…&topic=… · /admin/destinations?prefill=1&city=…&notes=… · "
        "/admin/seo-pages?prefill=1&topic=…&keywords=mot1,mot2 · "
        "/admin/newsletter?prefill=1&topic=…&notes=… "
        'Réponds STRICTEMENT en JSON : {"message":"…","actions":[{"label":"…","url":"/…"}],"tool":null}'
    )


# ── Confirmations (publication = double validation) ──────────────────────────

def _prune_pending() -> None:
    now = time.time()
    stale = [k for k, v in _PENDING.items() if now - v.get("ts", now) > _PENDING_TTL]
    for k in stale:
        _PENDING.pop(k, None)


def create_confirmation(action_type: str, params: dict, title: str, summary: str) -> dict:
    token = secrets.token_urlsafe(16)
    with _PENDING_LOCK:
        _prune_pending()
        _PENDING[token] = {"type": action_type, "params": params, "ts": time.time()}
    _remember_pending(token)
    return {"token": token, "title": title, "summary": summary, "type": action_type}


def cancel_confirmation(token: str) -> bool:
    with _PENDING_LOCK:
        return _PENDING.pop(token, None) is not None


def reset_conversation() -> dict:
    """Nouvelle conversation Linh : annule les confirmations en attente de la session.

    L'historique de chat est géré côté navigateur (sessionStorage) ; ici on purge
    uniquement la mémoire serveur (tokens « oui » / cartes de confirmation).
    Les brouillons admin (guides, destinations…) ne sont pas touchés.
    """
    try:
        tokens = list(session.get(_SESSION_PENDING_KEY) or [])
    except Exception:  # noqa: BLE001
        tokens = []
    cancelled = sum(1 for t in tokens if cancel_confirmation(t))
    try:
        session[_SESSION_PENDING_KEY] = []
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "cancelled": cancelled}


def _prune_action_jobs() -> None:
    now = time.time()
    stale = [k for k, v in _ACTION_JOBS.items() if now - v.get("ts", now) > _ACTION_JOB_TTL]
    for k in stale:
        _ACTION_JOBS.pop(k, None)


def start_action_job(fn, *, initial_phase: str = "") -> str:
    """Lance une action admin lourde en arrière-plan ; renvoie un token de suivi."""
    from admin import ai_client

    job_token = secrets.token_urlsafe(16)
    with _ACTION_JOB_LOCK:
        _prune_action_jobs()
        _ACTION_JOBS[job_token] = {
            "status": "running",
            "result": None,
            "error": "",
            "phase": initial_phase,
            "ts": time.time(),
        }

    def _run() -> None:
        t0 = time.time()

        def report(phase: str) -> None:
            with _ACTION_JOB_LOCK:
                entry = _ACTION_JOBS.get(job_token)
                if entry and entry.get("status") == "running":
                    entry["phase"] = phase
                    entry["ts"] = time.time()

        try:
            result = fn(report)
            with _ACTION_JOB_LOCK:
                _ACTION_JOBS[job_token] = {
                    "status": "done",
                    "result": result,
                    "error": "",
                    "phase": "",
                    "ts": time.time(),
                }
        except Exception as exc:  # noqa: BLE001
            message = ai_client.friendly_error(exc)
            with _ACTION_JOB_LOCK:
                _ACTION_JOBS[job_token] = {
                    "status": "error",
                    "result": None,
                    "error": message or str(exc),
                    "phase": "",
                    "ts": time.time(),
                }

    threading.Thread(target=_run, daemon=True).start()
    return job_token


def action_job_status(job_token: str) -> dict:
    """Statut d'un job d'action Linh (running|done|error|missing)."""
    with _ACTION_JOB_LOCK:
        entry = _ACTION_JOBS.get(job_token)
        if not entry:
            return {"status": "missing", "error": "", "phase": ""}
        out = {
            "status": entry.get("status", "missing"),
            "error": entry.get("error", ""),
            "phase": entry.get("phase", ""),
        }
        if entry.get("status") == "done" and entry.get("result"):
            out.update(entry["result"])
        return out


def execute_confirmation(token: str) -> dict:
    """Exécute l'action confirmée. Lève ValueError avec message lisible sinon."""
    with _PENDING_LOCK:
        _prune_pending()
        pending = _PENDING.pop(token, None)
    if not pending:
        raise ValueError("Action expirée ou introuvable — redemandez à Linh de la préparer.")

    action = pending["type"]
    params = pending.get("params") or {}

    if action == "publish_article":
        return _exec_publish_article()
    if action == "publish_seo_page":
        return _exec_publish_seo_page()
    if action == "publish_seo_batch":
        return _exec_publish_seo_batch()
    if action == "publish_destination":
        return _exec_publish_destination()
    if action == "publish_facebook":
        return _exec_publish_social({"network": "facebook"})
    if action == "publish_social":
        return _exec_publish_social(params)
    if action == "send_newsletter":
        return _exec_send_newsletter(params)
    if action == "add_partner":
        return _exec_add_partner(params)
    if action == "find_influencers":
        job_token = start_action_job(
            lambda report: _exec_find_influencers(params, report),
            initial_phase="Recherche web des influenceurs…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": "⏳ Recherche d'influenceurs en cours (web + extraction des emails + tri IA)…",
        }
    if action == "set_destination_region":
        return _exec_set_destination_region(params)
    if action == "update_article":
        return _exec_update_article(params)
    if action == "add_category":
        return _exec_add_category(params)
    if action == "update_destination":
        return _exec_update_destination(params)
    if action == "improve_article":
        job_token = start_action_job(
            lambda report: _exec_improve_article(params, report),
            initial_phase="Préparation de l'amélioration IA…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": "⏳ Amélioration IA de l'article en cours (rédaction + maillage interne)…",
        }
    if action == "improve_destination":
        job_token = start_action_job(
            lambda report: _exec_improve_destination(params, report),
            initial_phase="Préparation de l'amélioration IA…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": "⏳ Amélioration IA de la destination en cours…",
        }
    if action == "update_pages":
        count = len(params.get("items") or [])
        job_token = start_action_job(
            lambda report: _exec_update_pages(params, report),
            initial_phase=f"Préparation des {count} pages…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": (
                f"⏳ Modification de {count} page(s) en cours (une par une, "
                "version EN retraduite si le texte FR change)…"
            ),
        }
    if action == "update_image":
        job_token = start_action_job(
            lambda report: _exec_update_image(params, report),
            initial_phase="Préparation de l'image…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": "⏳ Mise à jour d'image en cours (téléchargement + optimisation WebP)…",
        }
    if action == "update_images":
        count = len(params.get("items") or [])
        job_token = start_action_job(
            lambda report: _exec_update_images(params, report),
            initial_phase=f"Préparation des {count} images…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": f"⏳ Mise à jour de {count} image(s) en cours (recherche + téléchargement + WebP, une par une)…",
        }
    if action == "add_map_points":
        # Géocodage OSM (≥1,1 s/requête) + photo Pixabay par point : plusieurs
        # points dépassent le timeout routeur (~60 s) → job en arrière-plan.
        job_token = start_action_job(
            lambda report: _exec_add_map_points(params, report),
            initial_phase="Géolocalisation des points (OpenStreetMap)…",
        )
        return {
            "async": True,
            "job_token": job_token,
            "message": "⏳ Ajout des points sur la carte en cours (géocodage OpenStreetMap + photo de chaque lieu)…",
        }
    if action == "update_map_images":
        return _exec_update_map_images(params)
    raise ValueError(f"Action inconnue : {action}")


# ── Brouillons partagés avec l'admin (mêmes tokens de session) ───────────────

def _draft_token_key(kind: str) -> str:
    return f"{kind}_draft_token"


def _get_draft(kind: str) -> dict | None:
    from admin import draft_store
    return draft_store.get_draft(session.get(_draft_token_key(kind)))


def _store_draft(kind: str, draft: dict) -> None:
    from admin import draft_store
    token = draft_store.new_token()
    draft_store.set_draft(token, draft)
    session[_draft_token_key(kind)] = token


def _start_job(kind: str, fn, initial_phase: str) -> None:
    from admin import draft_store
    from admin import ai_client
    token = draft_store.new_token()
    session[_draft_token_key(kind)] = token
    draft_store.start_job(token, fn, ai_client.friendly_error, initial_phase=initial_phase)


def job_status(kind: str) -> dict:
    """Statut d'un job de génération + carte de confirmation quand c'est prêt."""
    from admin import draft_store

    if kind not in ("article", "destination", "newsletter", "social", "seo_page", "seo_batch"):
        return {"status": "missing", "error": "", "phase": ""}
    st = draft_store.status(session.get(_draft_token_key(kind)))
    result = {"status": st["status"], "error": st["error"], "phase": st["phase"], "kind": kind}
    if st["status"] == "done":
        draft = _get_draft(kind) or {}
        result.update(_describe_draft(kind, draft))
    return result


def _describe_draft(kind: str, draft: dict) -> dict:
    if kind == "article":
        title = draft.get("title", "(sans titre)")
        return {
            "summary": f"Guide prêt : « {title} » (/blog/{draft.get('slug', '?')}) — relisez l'aperçu avant publication.",
            "preview_url": "/admin/guides",
            "confirm": create_confirmation(
                "publish_article", {}, "Publier l'article sur le site ?",
                f"« {title} » sera publié sur /blog/{draft.get('slug', '?')} (FR + EN).",
            ),
        }
    if kind == "seo_batch":
        n = len((draft or {}).get("pages") or [])
        total = (draft or {}).get("total") or n
        return {
            "summary": f"Lot SEO prêt : {n}/{total} page(s) générée(s) — aperçu et publication sur /admin/seo-pages.",
            "preview_url": "/admin/seo-pages",
            "confirm": create_confirmation(
                "publish_seo_batch", {}, f"Publier les {n} pages SEO du lot ?",
                f"{n} landing(s) seront publiées sur /seo/… (FR+EN, sitemap).",
            ),
        }
    if kind == "seo_page":
        title = draft.get("title", "(sans titre)")
        return {
            "summary": f"Page SEO prête : « {title} » (/seo/{draft.get('slug', '?')}) — relisez l'aperçu avant publication.",
            "preview_url": "/admin/seo-pages",
            "confirm": create_confirmation(
                "publish_seo_page", {}, "Publier la page SEO sur le site ?",
                f"« {title} » sera publiée sur /seo/{draft.get('slug', '?')} (FR + EN, sitemap + maillage).",
            ),
        }
    if kind == "destination":
        name = draft.get("name", "(sans nom)")
        return {
            "summary": f"Page destination prête : « {name} » (/{draft.get('slug', '?')}).",
            "preview_url": "/admin/destinations",
            "confirm": create_confirmation(
                "publish_destination", {}, "Publier la destination ?",
                f"« {name} » sera publiée sur /{draft.get('slug', '?')}.",
            ),
        }
    if kind == "newsletter":
        subject = draft.get("subject", "(sans objet)")
        return {
            "summary": f"Newsletter prête : « {subject} » — aperçu disponible dans l'admin.",
            "preview_url": "/admin/newsletter",
            "confirm": create_confirmation(
                "send_newsletter", {"scope": "all"}, "Envoyer la newsletter à tous les abonnés ?",
                f"« {subject} » partira vers tous les abonnés. (Astuce : demandez d'abord un envoi test.)",
            ),
        }
    if kind == "social":
        from admin import social_networks as sn

        msg = (draft.get("message") or "")[:220]
        network = (draft.get("network") or "facebook").strip().lower()
        net_name = sn.NETWORK_KEYS.get(network, {}).get("name", network.title())
        return {
            "summary": f"Post {net_name} prêt :\n" + msg,
            "preview_url": "/admin/social",
            "confirm": create_confirmation(
                "publish_social", {"network": network}, f"Publier ce post sur {net_name} ?",
                msg + ("…" if len(draft.get("message") or "") > 220 else ""),
            ),
        }
    return {}


# ── Exécuteurs (après confirmation uniquement) ───────────────────────────────

def _exec_publish_article() -> dict:
    from admin import draft_store
    from admin.image_service import attach_image_to_article
    from admin.store import add_article

    article = _get_draft("article")
    if not article:
        raise ValueError("Aucun brouillon d'article — demandez d'abord une génération.")
    if not article.get("image"):
        article.update(attach_image_to_article(article, article.get("image_prompt")))
    add_article(article)
    draft_store.clear(session.pop(_draft_token_key("article"), None))
    return {"message": f"✅ Article publié : /blog/{article['slug']}", "url": f"/blog/{article['slug']}"}


def _exec_publish_seo_page() -> dict:
    from admin import draft_store
    from admin.image_service import attach_image_to_article
    from admin.seo_pages_service import add_seo_page, replace_seo_page

    page = _get_draft("seo_page")
    if not page:
        raise ValueError("Aucun brouillon de page SEO — demandez d'abord une génération.")
    if not page.get("image"):
        page.update(attach_image_to_article(page, page.get("image_prompt")))
    editing_slug = (page.pop("editing_slug", None) or "").strip()
    if editing_slug:
        replace_seo_page(editing_slug, page)
    else:
        add_seo_page(page)
    draft_store.clear(session.pop(_draft_token_key("seo_page"), None))
    return {"message": f"✅ Page SEO publiée : /seo/{page['slug']}", "url": f"/seo/{page['slug']}"}


def _exec_publish_seo_batch() -> dict:
    from admin import draft_store
    from admin.image_service import attach_image_to_article
    from admin.seo_pages_service import add_seo_page

    batch = _get_draft("seo_batch") or {}
    pages = list(batch.get("pages") or [])
    if not pages:
        raise ValueError("Aucun lot SEO — générez d'abord un batch.")
    published = 0
    urls: list[str] = []
    for page in pages:
        if not page.get("image"):
            page.update(attach_image_to_article(page, page.get("image_prompt")))
        add_seo_page(page)
        published += 1
        urls.append(f"/seo/{page['slug']}")
    draft_store.clear(session.pop(_draft_token_key("seo_batch"), None))
    return {
        "message": f"✅ {published} page(s) SEO publiée(s).",
        "urls": urls[:5],
    }


def _exec_publish_destination() -> dict:
    from admin import draft_store
    from admin.store import add_or_update_destination

    dest = _get_draft("destination")
    if not dest:
        raise ValueError("Aucun brouillon de destination — demandez d'abord une génération.")
    add_or_update_destination(dest)
    draft_store.clear(session.pop(_draft_token_key("destination"), None))
    return {"message": f"✅ Destination publiée : /{dest['slug']}", "url": f"/{dest['slug']}"}


def _exec_publish_social(params: dict) -> dict:
    from admin import draft_store
    from admin import facebook_service as fb
    from admin import social_networks as sn

    post = _get_draft("social")
    if not post:
        raise ValueError("Aucun post en attente — demandez d'abord une génération.")
    network = (params.get("network") or post.get("network") or "facebook").strip().lower()
    net_name = sn.NETWORK_KEYS.get(network, {}).get("name", network.title())

    if network == "facebook":
        if not fb.is_configured():
            raise ValueError("Facebook non configuré (ID de page + token) — voir /admin/social.")
        link = post.get("link") or ""
        if link:
            result = fb.publish_link(post.get("message", ""), link)
        elif post.get("image"):
            result = fb.publish_photo(post.get("message", ""), post["image"])
        else:
            result = fb.publish_link(post.get("message", ""), _site_url())
        permalink = fb.post_permalink(result)
    else:
        permalink = sn.publish(
            network,
            message=post.get("message", ""),
            link=post.get("link") or "",
            image_url=post.get("image") or "",
        )
    draft_store.clear(session.pop(_draft_token_key("social"), None))
    return {"message": f"✅ Publié sur {net_name}. {permalink}".strip(), "url": permalink}


def _exec_add_partner(params: dict) -> dict:
    from admin.partners_service import add_partnership

    partner = add_partnership({**params, "source": "linh"})
    return {
        "message": f"✅ Partenaire « {partner['name']} » enregistré (statut : à contacter)"
                   + (f" — email : {partner['email']}" if partner.get("email") else " — sans email pour l'instant")
                   + ".",
        "url": "/admin/partnerships",
    }


def _exec_find_influencers(params: dict, report) -> dict:
    from admin.partners_service import search_and_save_influencers

    result = search_and_save_influencers((params.get("brief") or "").strip(), progress=report)
    saved = result["saved"]
    if not saved and not result["candidates"]:
        return {"message": "Aucun candidat pertinent trouvé — reformulez le brief (niche, langue, plateforme).",
                "url": "/admin/partnerships"}
    lines = [
        f"• {p['name']} ({p.get('type', '?')})" + (f" — {p['email']}" if p.get("email") else " — email à trouver")
        for p in saved[:8]
    ]
    msg = (
        f"✅ {len(saved)} contact(s) enregistré(s) dans Partenariats (statut « à contacter »)"
        + (f", {result['skipped']} doublon(s) ignoré(s)" if result["skipped"] else "") + ".\n"
        + "\n".join(lines)
        + "\n\nContactez-les depuis /admin/newsletter (email IA « partenariat » ou manuel)."
    )
    return {"message": msg, "url": "/admin/partnerships"}


def _exec_set_destination_region(params: dict) -> dict:
    from data.trip_planner import REGION_LABELS_FR
    from admin.store import set_destination_region

    slug = (params.get("slug") or "").strip()
    region = (params.get("region") or "").strip().lower()
    dest = set_destination_region(slug, region)
    label = REGION_LABELS_FR.get(region, region)
    return {
        "message": f"✅ « {dest.get('name', slug)} » est maintenant dans la section {label} du menu Destinations.",
        "url": f"/{slug}",
    }


def _exec_update_destination(params: dict) -> dict:
    from admin.store import update_destination_fields

    resolved_slug, _dest = _resolve_destination_slug((params.get("slug") or "").strip())
    dest = update_destination_fields(resolved_slug, params)
    return {
        "message": f"✅ Page destination mise à jour : « {dest.get('name', resolved_slug)} » (/{resolved_slug}).",
        "url": f"/{resolved_slug}",
    }


def _article_payload_for_ai(slug: str) -> dict:
    """Article publié au format plat attendu par improve_guide."""
    from admin.store import ARTICLE_EDITABLE_FIELDS, get_article_by_slug

    article = get_article_by_slug(slug)
    if not article:
        raise ValueError(f"Article introuvable : « {slug} ».")
    fr = article.get("i18n", {}).get("fr", {})
    payload = {
        k: article.get(k) or fr.get(k, "")
        for k in (*ARTICLE_EDITABLE_FIELDS, "guide_type", "city", "category", "image_prompt")
    }
    payload["slug"] = slug
    payload["guide_type"] = article.get("guide_type", "Guide pratique")
    payload["tags"] = article.get("tags") or fr.get("tags") or []
    return payload


def _destination_payload_for_ai(dest: dict) -> dict:
    """Destination publiée au format attendu par improve_destination."""
    from admin.store import DESTINATION_EDITABLE_FIELDS, DESTINATION_LIST_FIELDS

    fr = dest.get("i18n", {}).get("fr", {})
    payload = {k: dest.get(k) or fr.get(k, "") for k in DESTINATION_EDITABLE_FIELDS}
    for key in (*DESTINATION_LIST_FIELDS, "tips", "hotels", "activities", "image_prompt", "location_meta"):
        val = dest.get(key) or fr.get(key)
        if val:
            payload[key] = val
    payload["slug"] = dest["slug"]
    payload["name"] = dest.get("name") or fr.get("name", dest["slug"])
    return payload


def _exec_add_category(params: dict) -> dict:
    from admin.store import add_category

    key, cat = add_category(
        params.get("label_fr", ""),
        key=params.get("key", ""),
        label_en=params.get("label_en", ""),
        description_fr=params.get("description_fr", ""),
        description_en=params.get("description_en", ""),
    )
    return {
        "message": (
            f"✅ Catégorie créée : « {cat['label']} » — /categorie/{key} "
            "(menu du blog et sitemap mis à jour automatiquement)."
        ),
        "url": f"/categorie/{key}",
    }


def _exec_update_article(params: dict) -> dict:
    from admin.store import ARTICLE_EDITABLE_FIELDS, update_article_fields

    slug = (params.get("slug") or "").strip()
    if not slug:
        raise ValueError("Slug d'article manquant.")
    changed = [k for k in (*ARTICLE_EDITABLE_FIELDS, "category") if params.get(k)]
    if not changed:
        raise ValueError("Aucun champ à modifier.")
    article = update_article_fields(slug, params)
    return {
        "message": f"✅ Article mis à jour : « {article.get('title', slug)} » (/blog/{slug}).",
        "url": f"/blog/{slug}",
    }


def _exec_improve_article(params: dict, report=None) -> dict:
    from admin import groq_ai
    from admin.store import apply_improved_article

    slug = (params.get("slug") or "").strip()
    instructions = (params.get("instructions") or "").strip()
    if not slug:
        raise ValueError("Slug d'article manquant.")
    if not instructions:
        raise ValueError("Instructions d'amélioration manquantes.")
    article = _article_payload_for_ai(slug)
    if report:
        report("Réécriture IA de l'article…")
    improved = groq_ai.improve_guide(article, instructions, progress=report)
    apply_improved_article(slug, improved)
    return {
        "message": f"✅ Article amélioré par l'IA : « {improved.get('title', slug)} » — version EN retraduite.",
        "url": f"/blog/{slug}",
    }


def _exec_improve_destination(params: dict, report=None) -> dict:
    from admin import groq_destinations
    from admin.store import apply_improved_destination

    resolved_slug, dest = _resolve_destination_slug((params.get("slug") or "").strip())
    instructions = (params.get("instructions") or "").strip()
    if not instructions:
        raise ValueError("Instructions d'amélioration manquantes.")
    payload = _destination_payload_for_ai(dest)
    if report:
        report("Réécriture IA de la page destination…")
    improved = groq_destinations.improve_destination(payload, instructions, progress=report)
    apply_improved_destination(resolved_slug, improved)
    return {
        "message": f"✅ Destination améliorée par l'IA : « {improved.get('name', resolved_slug)} » — version EN retraduite.",
        "url": f"/{resolved_slug}",
    }


def _exec_update_pages(params: dict, report=None) -> dict:
    """Lot de modifications de CONTENU (articles et destinations mélangés) — un
    job, une page à la fois. Chaque item est soit une édition directe de champs
    (comme update_article/update_destination), soit une réécriture IA quand il
    porte des `instructions` (comme improve_article/improve_destination). Une
    page en échec ne bloque jamais le reste du lot."""
    items = params.get("items") or []
    done: list[str] = []
    errors: list[str] = []

    for i, item in enumerate(items, 1):
        slug = (item.get("slug") or "").strip()
        target = (item.get("target") or "article").strip().lower()
        instructions = (item.get("instructions") or "").strip()
        if report:
            report(f"Page {i}/{len(items)} : {slug}…")
        try:
            if instructions:
                if target == "destination":
                    _exec_improve_destination({"slug": slug, "instructions": instructions}, report)
                else:
                    _exec_improve_article({"slug": slug, "instructions": instructions}, report)
            elif target == "destination":
                _exec_update_destination(item)
            else:
                _exec_update_article(item)
            done.append(item.get("label") or slug)
        except Exception as exc:  # noqa: BLE001 — une page en échec ne bloque pas le lot
            errors.append(f"{slug} ({exc})")

    parts = []
    if done:
        parts.append(f"✅ {len(done)} page(s) modifiée(s) : " + ", ".join(done) + ".")
    if errors:
        parts.append("⚠️ Échec pour : " + " ; ".join(errors))
    if not parts:
        parts.append("Aucune page n'a pu être modifiée.")
    return {"message": "\n".join(parts), "url": "/admin"}


def _image_query_for_params(params: dict) -> str:
    """Mots-clés de recherche d'image par défaut quand l'URL fournie n'est pas exploitable."""
    from admin.image_service import destination_pixabay_query

    query = (params.get("query") or "").strip()
    if query:
        return query
    target = (params.get("target") or "").strip().lower()
    slug = (params.get("slug") or "").strip()
    if target == "destination" and slug:
        try:
            resolved, dest = _resolve_destination_slug(slug)
            return destination_pixabay_query(resolved, dest)
        except ValueError:
            pass
    if slug:
        return destination_pixabay_query(slug)
    return "Vietnam travel destination landmark"


def _resolve_image_url(params: dict, report=None) -> str:
    """URL d'image : directe/Commons/og:image, sinon banques d'images libres.

    La recherche par mots-clés interroge en cascade Pixabay (si clé), Openverse,
    Wikimedia Commons puis DuckDuckGo Images — toutes renvoient des URLs
    directement téléchargeables, plus de dépendance dure à PIXABAY_API_KEY.
    """
    from admin.image_search import find_image_url
    from admin.image_service import resolve_direct_image_url

    image_url = (params.get("image_url") or "").strip()
    if image_url:
        direct = resolve_direct_image_url(image_url)
        if direct:
            return direct
        query = _image_query_for_params(params)
        if report:
            report(
                f"URL page non utilisable — recherche d'image « {query[:60]} »…"
            )
        return find_image_url(query)

    query = _image_query_for_params(params)
    if not query:
        raise ValueError("Indique une URL d'image (image_url) ou des mots-clés (query).")
    if report:
        report(f"Recherche d'image « {query[:60]} »…")
    return find_image_url(query)


def _resolve_destination_slug(slug: str) -> tuple[str, dict]:
    """Slug canonique + destination, avec résolution d'alias (ex. m-tho-delta-mekong)."""
    from admin.store import find_destination_slug, get_destination_by_slug

    slug = (slug or "").strip().strip("/")
    resolved = find_destination_slug(slug) or slug
    dest = get_destination_by_slug(resolved)
    if not dest:
        raise ValueError(
            f"Destination introuvable : « {slug} » — utilise le slug exact du bloc ÉTAT DU SITE "
            f"(ex. delta-du-mekong, pas m-tho-delta-mekong)."
        )
    return resolved, dest


def _apply_resolved_image(target: str, slug: str, image_url: str, alt: str | None) -> tuple[str, str]:
    """Télécharge + optimise WebP + applique. Retourne (libellé, url publique)."""
    from admin.image_service import (
        set_remote_image_for_article,
        set_remote_image_for_destination,
    )
    from admin.store import (
        get_article_by_slug,
        update_article_image,
        update_destination_image,
    )

    if target == "destination":
        resolved_slug, dest = _resolve_destination_slug(slug)
        meta = set_remote_image_for_destination(dest, image_url, alt)
        update_destination_image(resolved_slug, meta)
        return dest.get("name", resolved_slug), f"/{resolved_slug}"

    article = get_article_by_slug(slug)
    if not article:
        raise ValueError(f"Article introuvable : « {slug} ».")
    meta = set_remote_image_for_article(article, image_url, alt)
    update_article_image(slug, meta)
    return article.get("title", slug), f"/blog/{slug}"


def _exec_update_image(params: dict, report=None) -> dict:
    target = (params.get("target") or "article").strip().lower()
    slug = (params.get("slug") or "").strip()
    alt = (params.get("alt") or "").strip() or None
    if not slug:
        raise ValueError("Slug manquant pour la mise à jour d'image.")

    image_url = _resolve_image_url(params, report)
    if report:
        report("Téléchargement et optimisation WebP…")

    label, url = _apply_resolved_image(target, slug, image_url, alt)
    what = "la destination" if target == "destination" else "l'article"
    return {"message": f"✅ Image mise à jour pour {what} « {label} ».", "url": url}


def _exec_update_images(params: dict, report=None) -> dict:
    """Lot d'images (ex. toutes les bannières destinations) — un job, une image
    à la fois, et jamais deux fois la même photo dans le même lot."""
    from admin.image_search import find_image_url

    items = params.get("items") or []
    used_urls: set[str] = set()
    done: list[str] = []
    errors: list[str] = []

    for i, item in enumerate(items, 1):
        slug = (item.get("slug") or "").strip()
        target = (item.get("target") or "destination").strip().lower()
        if report:
            report(f"Image {i}/{len(items)} : {slug}…")
        try:
            image_url = _resolve_image_url(item)
            if image_url in used_urls and not (item.get("image_url") or "").strip():
                # Même photo qu'un item précédent : on varie avec un seed.
                query = _image_query_for_params(item)
                for seed in range(1, 4):
                    candidate = find_image_url(query, seed)
                    if candidate not in used_urls:
                        image_url = candidate
                        break
            used_urls.add(image_url)
            label, _url = _apply_resolved_image(
                target, slug, image_url, (item.get("alt") or "").strip() or None,
            )
            done.append(label)
        except Exception as exc:  # noqa: BLE001 — une image en échec ne bloque pas le lot
            errors.append(f"{slug} ({exc})")

    parts = []
    if done:
        parts.append(f"✅ {len(done)} image(s) mise(s) à jour : " + ", ".join(done) + ".")
    if errors:
        parts.append("⚠️ Échec pour : " + " ; ".join(errors))
    if not parts:
        parts.append("Aucune image n'a pu être mise à jour.")
    return {"message": "\n".join(parts), "url": "/admin/destinations"}


def _exec_add_map_points(params: dict, report=None) -> dict:
    from admin import map_service

    published: list[str] = []
    pending: list[str] = []
    approx: list[str] = []
    errors: list[str] = []
    points = params.get("points") or []
    for i, point in enumerate(points, 1):
        if report:
            report(f"Point {i}/{len(points)} : {point.get('title', '?')}…")
        try:
            result = map_service.add_map_point(point)
            if result.get("approx"):
                approx.append(point["title"])
            (published if result["status"] == "published" else pending).append(point["title"])
        except Exception as exc:  # noqa: BLE001 — un point en échec ne bloque pas les autres
            errors.append(f"{point.get('title', '?')} ({exc})")

    parts = []
    if published:
        parts.append(f"✅ {len(published)} point(s) ajouté(s) sur la carte : " + ", ".join(published) + ".")
    if approx:
        parts.append(
            f"📍 {len(approx)} point(s) placé(s) près du centre-ville (adresse exacte introuvable "
            "sur OpenStreetMap) : " + ", ".join(approx) + " — position affinable depuis /admin/map."
        )
    if pending:
        parts.append(
            f"⏳ {len(pending)} point(s) en attente (pas de page destination publiée pour cette ville) : "
            + ", ".join(pending) + " — publiez-les depuis /admin/map."
        )
    if errors:
        parts.append("⚠️ Non ajouté(s) : " + " ; ".join(errors))
    if not parts:
        parts.append("Aucun point n'a pu être ajouté.")
    return {"message": "\n".join(parts), "url": "/admin/map"}


def _exec_update_map_images(params: dict) -> dict:
    from admin import map_service

    if params.get("all_missing"):
        map_service.defer_backfill_point_images()
        return {
            "message": "🖼️ Recherche d'images lancée en arrière-plan pour tous les points de "
            "carte sans photo — résultat visible dans /admin/map d'ici quelques minutes.",
            "url": "/admin/map",
        }
    point = map_service.set_point_image_by_title(
        (params.get("city") or "").strip(),
        (params.get("title") or "").strip(),
        (params.get("image_url") or params.get("query") or "").strip(),
    )
    return {
        "message": f"🖼️ Image mise à jour pour « {point.get('title', '')} » sur la carte.",
        "url": "/admin/map",
    }


def _exec_send_newsletter(params: dict) -> dict:
    from admin.newsletter_service import get_newsletter_subscribers, send_newsletter_email

    draft = _get_draft("newsletter")
    if not draft:
        raise ValueError("Aucun brouillon de newsletter — demandez d'abord une génération.")
    scope = params.get("scope") or "test"
    if scope == "all":
        if draft.get("email_type") == "partenariat":
            raise ValueError(
                "Brouillon partenariat — envoyez-le à un partenaire depuis /admin/newsletter, "
                "pas à toute la newsletter."
            )
        subs = get_newsletter_subscribers()
        if not subs:
            raise ValueError("Aucun abonné à la newsletter.")
        recipients = [s["email"] for s in subs]
    else:
        email = (params.get("email") or "").strip().lower()
        if not email or "@" not in email:
            raise ValueError("Adresse email de test invalide.")
        recipients = [email]
    result = send_newsletter_email(
        recipients, draft["subject"], draft["body_html"], preheader=draft.get("preheader", ""),
        email_type=params.get("email_type") or draft.get("email_type") or "newsletter",
        partner_id=(params.get("partner_id") or "").strip(),
        recipient_name=(params.get("partner_name") or params.get("recipient_name") or "").strip(),
    )
    if not result["sent"]:
        raise ValueError("Échec de l'envoi — vérifiez la configuration SMTP.")
    email_type = params.get("email_type") or draft.get("email_type") or "newsletter"
    if scope != "all" and email_type == "partenariat":
        from admin.partners_service import mark_partner_emailed
        mark_partner_emailed(
            partner_id=(params.get("partner_id") or "").strip(),
            email=recipients[0],
        )
    return {"message": f"✅ Newsletter envoyée : {result['sent']}/{result['total']} email(s).", "url": "/admin/newsletter"}


def _site_url() -> str:
    import config
    return config.SITE_URL.rstrip("/") + "/"


# ── Outils déclenchés par l'IA ───────────────────────────────────────────────

def _handle_tool(tool: dict, snapshot: dict) -> dict:
    """Exécute l'intention outil de Linh. Retourne des compléments de réponse."""
    name = (tool.get("name") or "").strip()
    params = tool.get("params") or {}
    from data.vietnam_cities import ALL_CITY_VALUES

    if name == "audit_site":
        return {"findings": run_audit(snapshot)[:10]}

    if name == "generate_guide":
        city = (params.get("city") or "").strip()
        topic = (params.get("topic") or "").strip()
        if city not in ALL_CITY_VALUES:
            raise ValueError(f"Ville invalide « {city} » — choisis parmi la liste VILLES.")
        if not topic:
            raise ValueError("Sujet manquant pour le guide.")
        from admin import groq_ai
        from admin.image_service import attach_image_to_article

        guide_type = params.get("guide_type") or "article blog"

        def _gen(report):
            article = groq_ai.generate_guide(topic=topic, guide_type=guide_type, city=city, progress=report)
            article["city"] = city
            report("Génération de l'image Vietnam (WebP)…")
            article.update(attach_image_to_article(
                article, article.get("image_prompt"),
                image_nonce=int(time.time() * 1000) % 1_000_000,
            ))
            report("Finalisation de l'article…")
            return article

        _start_job("article", _gen, "Rédaction du guide SEO…")
        return {"job": {"kind": "article"}}

    if name == "generate_seo_page":
        topic = (params.get("topic") or "").strip()
        keywords = (params.get("keywords") or params.get("target_keywords") or "").strip()
        city = (params.get("city") or "").strip()
        if city and city not in ALL_CITY_VALUES:
            raise ValueError(f"Ville invalide « {city} » — laissez vide pour Vietnam général.")
        if not topic and not keywords:
            raise ValueError("Indiquez topic et/ou keywords (mots-clés séparés par des virgules).")
        from admin import groq_seo_page
        from admin.image_service import attach_image_to_article
        from admin.seo_pages_service import _parse_keywords

        page_type = (params.get("page_type") or "landing").strip()

        def _gen(report):
            page = groq_seo_page.generate_seo_page(
                topic=topic,
                keywords=_parse_keywords(keywords),
                city=city,
                page_type=page_type,
                progress=report,
            )
            report("Génération de l'image Vietnam (WebP)…")
            page.update(attach_image_to_article(
                page, page.get("image_prompt"),
                image_nonce=int(time.time() * 1000) % 1_000_000,
            ))
            report("Finalisation de la page SEO…")
            return page

        _start_job("seo_page", _gen, "Analyse des mots-clés SEO…")
        return {"job": {"kind": "seo_page"}}

    if name == "generate_seo_matrix":
        from admin import ai_client
        from admin.seo_keyword_matrix import build_manual_matrix, generate_matrix_ai

        brief = (params.get("brief") or "").strip()
        city = (params.get("city") or "").strip()
        axis_a = (params.get("axis_a") or "").strip()
        axis_b = (params.get("axis_b") or "").strip()
        try:
            count = int(params.get("count") or 10)
        except ValueError:
            count = 10
        if axis_a and axis_b:
            rows = build_manual_matrix(axis_a, axis_b, city=city, page_type=params.get("page_type") or "landing")
        else:
            if not ai_client.is_configured():
                raise ValueError("Clé IA requise pour générer une matrice par IA.")
            rows = generate_matrix_ai(brief=brief, count=count, city=city)
        _store_draft("seo_matrix", {"matrix": True, "rows": rows})
        topics = ", ".join(f"« {r.get('topic', '')[:40]} »" for r in rows[:4])
        return {
            "message": f"Matrice SEO prête : {len(rows)} lignes ({topics}{'…' if len(rows) > 4 else ''}).",
            "actions": [{"label": "Ouvrir la matrice", "url": "/admin/seo-pages"}],
            "matrix_rows": len(rows),
        }

    if name == "generate_seo_batch":
        from admin import groq_seo_page
        from admin.seo_keyword_matrix import clamp_batch_rows

        rows = params.get("rows")
        if not rows:
            matrix_draft = _get_draft("seo_matrix") or {}
            rows = matrix_draft.get("rows") or []
        if not isinstance(rows, list) or not rows:
            raise ValueError("Matrice vide — lance generate_seo_matrix d'abord ou passe rows.")
        selected = [r for r in rows if r.get("selected", True) and not r.get("duplicate")]
        if not selected:
            selected = rows

        def _batch(report):
            return groq_seo_page.generate_seo_batch(clamp_batch_rows(selected), progress=report)

        _start_job("seo_batch", _batch, "Préparation du lot SEO…")
        return {"job": {"kind": "seo_batch"}}

    if name == "generate_destination":
        city = (params.get("city") or "").strip()
        if city not in ALL_CITY_VALUES or city == "Tout le Vietnam":
            raise ValueError(f"Ville invalide « {city} » pour une page destination.")
        from admin import groq_destinations
        from admin.image_service import attach_image_to_destination

        notes = (params.get("notes") or "").strip()

        def _gen(report):
            dest = groq_destinations.generate_destination(city, notes, progress=report)
            report("Génération de l'image de la destination (WebP)…")
            dest.update(attach_image_to_destination(
                dest, dest.get("image_prompt"),
                image_nonce=int(time.time() * 1000) % 1_000_000,
            ))
            report("Finalisation de la page…")
            return dest

        _start_job("destination", _gen, "Rédaction de la page destination…")
        return {"job": {"kind": "destination"}}

    if name == "generate_newsletter":
        topic = (params.get("topic") or "").strip()
        if not topic:
            raise ValueError("Sujet manquant pour la newsletter.")
        from admin import groq_newsletter

        email_type = params.get("email_type") or "actualite"
        notes = (params.get("notes") or "").strip()
        partner_name = (params.get("partner_name") or "").strip()
        recipient_email = (params.get("recipient_email") or "").strip()
        _start_job(
            "newsletter",
            lambda report: groq_newsletter.generate_newsletter_email(
                topic, email_type, notes,
                progress=report,
                partner_name=partner_name,
                recipient_email=recipient_email,
            ),
            "Rédaction de l'email…",
        )
        return {"job": {"kind": "newsletter"}}

    if name == "generate_social_post":
        from admin import draft_store
        from admin import social_networks as sn
        from admin.social_ai import default_campaign, find_page, generate_post

        network = (params.get("network") or "facebook").strip().lower()
        net = sn.NETWORK_KEYS.get(network)
        if not net or not net.get("publishable"):
            raise ValueError(
                f"Réseau inconnu ou non publiable : « {network} » — choisis parmi "
                "facebook, pinterest, reddit, telegram, x, threads, instagram."
            )
        page = find_page((params.get("page_id") or "").strip(), "fr")
        brief = (params.get("brief") or "").strip()
        if not page and not brief:
            raise ValueError("Indique une page du site (page_id) ou un brief libre.")
        message = generate_post(page=page, brief=brief, lang="fr", network=network)
        campaign = default_campaign(page, brief, network)
        post = {
            "message": message,
            "link": sn.add_utm(page["url"], campaign, network) if page else "",
            "image": page["image"] if page else "",
            "campaign": campaign,
            "network": network,
        }
        token = draft_store.new_token()
        draft_store.set_draft(token, post)
        session[_draft_token_key("social")] = token
        return {
            "post_preview": message,
            "confirm": create_confirmation(
                "publish_social", {"network": network},
                f"Publier ce post sur {net['name']} ?",
                message[:220] + ("…" if len(message) > 220 else ""),
            ),
        }

    if name == "find_influencers":
        brief = (params.get("brief") or params.get("query") or "").strip()
        if not brief:
            raise ValueError("Précise le brief de recherche (ex. « influenceurs francophones voyage Vietnam »).")
        return {"confirm": create_confirmation(
            "find_influencers", {"brief": brief},
            "Lancer la recherche d'influenceurs ?",
            f"Recherche web « {brief} » + lecture des pages trouvées pour extraire les "
            "emails ; les contacts pertinents seront enregistrés dans Partenariats "
            "(statut « à contacter »).",
        )}

    if name == "add_partner":
        from admin.partners_service import PARTNER_TYPE_KEYS

        pname = (params.get("name") or "").strip()
        if not pname:
            raise ValueError("Le nom du partenaire est obligatoire.")
        ptype = (params.get("type") or "influenceur").strip().lower()
        if ptype not in PARTNER_TYPE_KEYS:
            ptype = "autre"
        email = (params.get("email") or "").strip()
        clean = {
            "name": pname, "type": ptype, "email": email,
            "links": params.get("links") or [],
            "topics": _coerce_str(params.get("topics")),
            "notes": _coerce_str(params.get("notes")),
        }
        return {"confirm": create_confirmation(
            "add_partner", clean,
            f"Enregistrer « {pname} » dans les partenariats ?",
            f"Type : {ptype} · Email : {email or '(aucun)'} — statut « à contacter », "
            "visible sur /admin/partnerships.",
        )}

    if name == "set_destination_region":
        from data.trip_planner import REGION_LABELS_FR, REGION_ORDER
        from admin.store import get_destination_by_slug

        slug = (params.get("slug") or "").strip()
        region = (params.get("region") or "").strip().lower()
        dest = get_destination_by_slug(slug)
        if not dest:
            raise ValueError(f"Destination introuvable : « {slug} » — vérifie le slug dans l'ÉTAT DU SITE.")
        if region not in REGION_ORDER:
            raise ValueError("Région invalide — utilise north, central ou south.")
        label = REGION_LABELS_FR.get(region, region)
        return {"confirm": create_confirmation(
            "set_destination_region", {"slug": slug, "region": region},
            f"Déplacer « {dest.get('name', slug)} » dans la section {label} ?",
            f"/{slug} apparaîtra dans la colonne {label} du menu Destinations (Nord/Centre/Sud).",
        )}

    if name == "add_category":
        from admin.store import get_categories, slugify

        label_fr = (params.get("label_fr") or params.get("label") or "").strip()
        if not label_fr:
            raise ValueError("Indique le nom FR de la catégorie (label_fr).")
        key = slugify((params.get("key") or "").strip() or label_fr)
        if key in get_categories():
            raise ValueError(f"La catégorie « {key} » existe déjà — visible sur /categorie/{key}.")
        return {"confirm": create_confirmation(
            "add_category",
            {
                "key": key,
                "label_fr": label_fr,
                "label_en": (params.get("label_en") or "").strip(),
                "description_fr": (params.get("description_fr") or "").strip(),
                "description_en": (params.get("description_en") or "").strip(),
            },
            f"Créer la catégorie « {label_fr} » ?",
            f"/categorie/{key} sera ajoutée au blog (FR + EN), au menu des catégories et au sitemap.",
        )}

    if name == "update_article":
        from admin.store import ARTICLE_EDITABLE_FIELDS, get_article_by_slug, get_categories

        slug = (params.get("slug") or "").strip()
        article = get_article_by_slug(slug)
        if not article:
            raise ValueError(f"Article introuvable : « {slug} » — vérifie le slug dans l'ÉTAT DU SITE.")
        changed = [k for k in (*ARTICLE_EDITABLE_FIELDS, "category") if params.get(k)]
        if not changed:
            raise ValueError(
                "Aucun champ à modifier — passe au moins title, meta_title, meta_description, "
                "excerpt, content, tags, focus_keyword ou category."
            )
        category = (params.get("category") or "").strip()
        if category and category not in get_categories():
            raise ValueError(
                f"Catégorie inconnue « {category} » — crée-la d'abord avec add_category."
            )
        return {"confirm": create_confirmation(
            "update_article",
            {**params, "slug": slug},
            f"Modifier l'article « {article.get('title', slug)} » ?",
            f"/blog/{slug} — champs modifiés : {', '.join(changed)}. La version EN sera retraduite si le texte FR change.",
        )}

    if name == "improve_article":
        from admin.store import get_article_by_slug

        slug = (params.get("slug") or "").strip()
        instructions = (params.get("instructions") or "").strip()
        if not slug:
            raise ValueError("Indique le slug de l'article (bloc ÉTAT DU SITE).")
        if not instructions:
            raise ValueError("Indique les instructions d'amélioration (ex. « enrichir la section visa », « optimiser le SEO »).")
        article = get_article_by_slug(slug)
        if not article:
            raise ValueError(f"Article introuvable : « {slug} » — vérifie le slug.")
        preview = instructions[:120] + ("…" if len(instructions) > 120 else "")
        return {"confirm": create_confirmation(
            "improve_article",
            {"slug": slug, "instructions": instructions},
            f"Améliorer par IA l'article « {article.get('title', slug)} » ?",
            f"/blog/{slug}\nInstructions : {preview}\nL'IA réécrira le contenu FR (maillage interne inclus), puis retraduction EN.",
        )}

    if name == "update_destination":
        from admin.store import DESTINATION_EDITABLE_FIELDS, DESTINATION_LIST_FIELDS

        slug = (params.get("slug") or "").strip()
        resolved_slug, dest = _resolve_destination_slug(slug)
        changed = [
            k for k in (*DESTINATION_EDITABLE_FIELDS, *DESTINATION_LIST_FIELDS, "tips", "region")
            if params.get(k)
        ]
        if not changed:
            raise ValueError(
                "Aucun champ à modifier — passe au moins tagline, meta_title, meta_description, "
                "overview, things_to_do, tips ou region."
            )
        confirm_params = {**params, "slug": resolved_slug}
        return {"confirm": create_confirmation(
            "update_destination", confirm_params,
            f"Modifier la page « {dest.get('name', resolved_slug)} » ?",
            f"/{resolved_slug} — champs modifiés : {', '.join(changed)}. La version EN sera retraduite si le texte FR change.",
        )}

    if name == "improve_destination":
        slug = (params.get("slug") or "").strip()
        instructions = (params.get("instructions") or "").strip()
        if not slug:
            raise ValueError("Indique le slug de la destination (bloc ÉTAT DU SITE).")
        if not instructions:
            raise ValueError("Indique les instructions d'amélioration (ex. « ajouter Mỹ Tho », « enrichir les conseils pratiques »).")
        resolved_slug, dest = _resolve_destination_slug(slug)
        preview = instructions[:120] + ("…" if len(instructions) > 120 else "")
        return {"confirm": create_confirmation(
            "improve_destination",
            {"slug": resolved_slug, "instructions": instructions},
            f"Améliorer par IA la destination « {dest.get('name', resolved_slug)} » ?",
            f"/{resolved_slug}\nInstructions : {preview}\nL'IA réécrira la page FR, puis retraduction EN.",
        )}

    if name == "update_pages":
        from admin.store import (
            ARTICLE_EDITABLE_FIELDS,
            DESTINATION_EDITABLE_FIELDS,
            DESTINATION_LIST_FIELDS,
            get_article_by_slug,
            get_categories,
        )

        raw_items = params.get("items") or []
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except ValueError:
                raw_items = []
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        if not isinstance(raw_items, list):
            raw_items = []

        items: list[dict] = []
        for it in raw_items[:20]:
            if not isinstance(it, dict):
                continue
            slug = _coerce_str(it.get("slug"))
            if not slug:
                continue
            target = (_coerce_str(it.get("target")) or "article").lower()
            if target not in ("article", "destination"):
                raise ValueError(f"Cible invalide pour « {slug} » — target=article ou destination.")
            instructions = _coerce_str(it.get("instructions"))
            if target == "destination":
                resolved_slug, dest = _resolve_destination_slug(slug)
                slug = resolved_slug
                label = dest.get("name", resolved_slug)
                fields = [
                    k for k in (*DESTINATION_EDITABLE_FIELDS, *DESTINATION_LIST_FIELDS, "tips", "region")
                    if it.get(k)
                ]
            else:
                article = get_article_by_slug(slug)
                if not article:
                    raise ValueError(f"Article introuvable : « {slug} » — vérifie le slug.")
                label = article.get("title", slug)
                fields = [k for k in (*ARTICLE_EDITABLE_FIELDS, "category") if it.get(k)]
                category = _coerce_str(it.get("category"))
                if category and category not in get_categories():
                    raise ValueError(
                        f"Catégorie inconnue « {category} » — crée-la d'abord avec add_category."
                    )
            if not instructions and not fields:
                raise ValueError(
                    f"Rien à modifier pour « {slug} » — passe des champs directs "
                    "(title, content, overview…) ou des instructions (réécriture IA)."
                )
            items.append({**it, "target": target, "slug": slug, "label": label})

        if not items:
            raise ValueError(
                "Aucune page à modifier — passe items:[{target, slug, champs…|instructions}]."
            )

        def _item_summary(it: dict) -> str:
            instructions = _coerce_str(it.get("instructions"))
            if instructions:
                return "réécriture IA : " + instructions[:70] + ("…" if len(instructions) > 70 else "")
            if it["target"] == "destination":
                keys = (*DESTINATION_EDITABLE_FIELDS, *DESTINATION_LIST_FIELDS, "tips", "region")
            else:
                keys = (*ARTICLE_EDITABLE_FIELDS, "category")
            return "champs : " + ", ".join(k for k in keys if it.get(k))

        listing = "\n".join(f"• {it['label']} ({it['target']}) — {_item_summary(it)}" for it in items)
        return {"confirm": create_confirmation(
            "update_pages", {"items": items},
            f"Modifier {len(items)} page(s) en une fois ?",
            listing + "\n\nUne seule confirmation pour tout le lot : les pages seront "
            "traitées une par une en arrière-plan (version EN retraduite si le texte "
            "FR change) ; une page en échec ne bloque pas les autres.",
        )}

    if name == "update_image":
        from admin.store import get_article_by_slug

        target = (params.get("target") or "article").strip().lower()
        slug = (params.get("slug") or "").strip()
        image_url = (params.get("image_url") or "").strip()
        query = (params.get("query") or "").strip()
        if target not in ("article", "destination"):
            raise ValueError("Cible invalide — utilise target=article ou target=destination.")
        if not slug:
            raise ValueError("Indique le slug de l'article ou de la destination.")
        if not image_url and not query:
            raise ValueError("Donne une URL d'image (image_url) ou des mots-clés (query).")

        resolved_slug = slug
        if target == "destination":
            resolved_slug, item = _resolve_destination_slug(slug)
            label = item.get("name", resolved_slug)
            where = f"la destination « {label} » (/{resolved_slug})"
        else:
            item = get_article_by_slug(slug)
            if not item:
                raise ValueError(f"Article introuvable : « {slug} » — vérifie le slug.")
            label = item.get("title", slug)
            where = f"l'article « {label} » (/blog/{slug})"

        # Pré-résolution AVANT confirmation : URL directe, Commons, og:image ou Pixabay.
        resolve_params = {
            "target": target,
            "slug": resolved_slug if target == "destination" else slug,
            "image_url": image_url,
            "query": query,
        }
        try:
            resolved_image_url = _resolve_image_url(resolve_params)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        src = resolved_image_url
        return {"confirm": create_confirmation(
            "update_image",
            {
                "target": target,
                "slug": resolved_slug if target == "destination" else slug,
                "image_url": resolved_image_url,
                "query": "",
                "alt": params.get("alt", ""),
            },
            f"Mettre à jour l'image de {where} ?",
            f"Nouvelle image : {src}\nElle sera téléchargée, optimisée en WebP puis appliquée.",
        )}

    if name == "update_images":
        from admin.image_service import destination_pixabay_query
        from admin.store import get_article_by_slug, get_destinations_dict

        raw_items = params.get("items") or []
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except ValueError:
                raw_items = []
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        if not isinstance(raw_items, list):
            raw_items = []

        if params.get("all_destinations"):
            # Raccourci : une nouvelle bannière pour CHAQUE destination publiée.
            extra = _coerce_str(params.get("query"))
            existing = {(_coerce_str(it.get("slug")) if isinstance(it, dict) else "") for it in raw_items}
            for slug, dest in get_destinations_dict().items():
                if slug in existing:
                    continue
                query = destination_pixabay_query(slug, dest)
                if extra:
                    query = f"{dest.get('name', slug)} Vietnam {extra}"
                raw_items.append({"target": "destination", "slug": slug, "query": query})

        items: list[dict] = []
        for it in raw_items[:30]:
            if not isinstance(it, dict):
                continue
            slug = _coerce_str(it.get("slug"))
            if not slug:
                continue
            target = (_coerce_str(it.get("target")) or "destination").lower()
            if target not in ("article", "destination"):
                raise ValueError(f"Cible invalide pour « {slug} » — target=article ou destination.")
            query = _coerce_str(it.get("query"))
            image_url = _coerce_str(it.get("image_url"))
            if target == "destination":
                resolved_slug, dest = _resolve_destination_slug(slug)
                slug = resolved_slug
                if not query and not image_url:
                    query = destination_pixabay_query(resolved_slug, dest)
                label = dest.get("name", resolved_slug)
            else:
                article = get_article_by_slug(slug)
                if not article:
                    raise ValueError(f"Article introuvable : « {slug} » — vérifie le slug.")
                label = article.get("title", slug)
                if not query and not image_url:
                    query = f"{label} Vietnam"
            items.append({
                "target": target,
                "slug": slug,
                "query": query,
                "image_url": image_url,
                "alt": _coerce_str(it.get("alt")),
                "label": label,
            })
        if not items:
            raise ValueError(
                "Aucune image à mettre à jour — passe items:[{target, slug, query|image_url}] "
                "ou all_destinations:true."
            )

        listing = "\n".join(
            f"• {it['label']} ({it['target']}) — "
            + (it["image_url"] or f"recherche « {it['query'][:60]} »")
            for it in items
        )
        return {"confirm": create_confirmation(
            "update_images", {"items": items},
            f"Mettre à jour {len(items)} image(s) en une fois ?",
            listing + "\n\nUne seule confirmation pour tout le lot : chaque image sera "
            "cherchée (ou téléchargée), optimisée en WebP puis appliquée, une par une "
            "en arrière-plan — sans jamais réutiliser deux fois la même photo.",
        )}

    if name == "add_map_points":
        from admin import map_service

        raw_points = params.get("points") or []
        if isinstance(raw_points, str):
            # Liste encodée en JSON-chaîne par le modèle — on la décode.
            try:
                raw_points = json.loads(raw_points)
            except ValueError:
                raw_points = []
        if isinstance(raw_points, dict):
            raw_points = [raw_points]
        if not isinstance(raw_points, list):
            raw_points = []
        default_city = _coerce_str(params.get("city"))
        points: list[dict] = []
        for p in raw_points[:10]:
            if not isinstance(p, dict):
                continue
            title = _coerce_str(p.get("title") or p.get("name"))
            address = _coerce_str(p.get("address"))
            if not title or not address:
                continue
            # On garde le libellé brut (accents, casse) : add_map_point normalise le
            # slug et mémorise ce libellé pour la légende des types personnalisés.
            kind = _coerce_str(p.get("kind")) or "poi"
            points.append({
                "title": title,
                "address": address,
                "city": _coerce_str(p.get("city")) or default_city,
                "kind": kind,
                "desc": _coerce_str(p.get("desc") or p.get("description")),
                "price_hint": _coerce_str(p.get("price_hint")),
                "affiliate_provider": _coerce_str(p.get("affiliate_provider")) or "custom",
                "affiliate_search": _coerce_str(p.get("affiliate_search")) or title,
                "affiliate_url": _coerce_str(p.get("affiliate_url")),
                "image_url": _coerce_str(p.get("image_url")),
            })
        if not points:
            raise ValueError("Aucun point valide — chaque point doit avoir au minimum un title et une address.")

        slug = map_service.resolve_destination_slug(points[0]["city"])
        if slug:
            place = map_service.get_destinations_dict_safe().get(slug, {}).get("name", slug)
            where = f"sur la carte de {place}"
        else:
            where = (
                f"pour « {points[0]['city'] or 'ville non précisée'} » (pas de page destination publiée : "
                "les points iront en attente dans /admin/map)"
            )
        listing = "\n".join(
            f"• {p['title']} ({map_service.kind_label(map_service.normalize_kind(p['kind']), 'fr')}) — {p['address']}"
            for p in points
        )
        return {"confirm": create_confirmation(
            "add_map_points", {"points": points},
            f"Ajouter {len(points)} point(s) {where} ?",
            listing + "\n\nChaque adresse sera géolocalisée via OpenStreetMap "
            "(si une adresse est introuvable, le point sera placé près du centre-ville, "
            "position affinable ensuite). Une photo du lieu est ajoutée automatiquement "
            "si image_url n'est pas fournie.",
        )}

    if name == "update_map_images":
        if params.get("all_missing"):
            return {"confirm": create_confirmation(
                "update_map_images", {"all_missing": True},
                "Chercher une photo pour tous les points de carte sans image ?",
                "Recherche automatique (Pixabay) en arrière-plan : nom du lieu, "
                "sinon type + ville. Les images déjà en place ne sont pas touchées.",
            )}
        title = (params.get("title") or "").strip()
        if not title:
            raise ValueError("Précise le titre du point (title) ou all_missing:true pour tout traiter.")
        city = (params.get("city") or "").strip()
        image = (params.get("image_url") or params.get("query") or "").strip()
        how = (
            f"Image : {image}" if image.startswith("http")
            else f"Recherche Pixabay : « {image} »" if image
            else "Recherche automatique (nom du lieu, sinon type + ville)"
        )
        return {"confirm": create_confirmation(
            "update_map_images", {"title": title, "city": city, "image_url": image},
            f"Mettre à jour la photo de « {title} » sur la carte ?",
            how,
        )}

    if name == "publish_draft":
        kind = params.get("kind") or "article"
        draft = _get_draft(kind)
        if not draft:
            raise ValueError(f"Aucun brouillon « {kind} » en attente — lance d'abord une génération.")
        desc = _describe_draft(kind, draft)
        return {"confirm": desc.get("confirm"), "summary": desc.get("summary")}

    if name in ("publish_facebook", "publish_social"):
        from admin import social_networks as sn

        post = _get_draft("social")
        if not post:
            raise ValueError("Aucun post en attente — lance d'abord generate_social_post.")
        network = (params.get("network") or post.get("network") or "facebook").strip().lower()
        net = sn.NETWORK_KEYS.get(network)
        if not net or not net.get("publishable"):
            raise ValueError(f"Réseau inconnu ou non publiable : « {network} ».")
        msg = (post.get("message") or "")[:220]
        return {"confirm": create_confirmation(
            "publish_social", {"network": network},
            f"Publier ce post sur {net['name']} ?",
            msg + ("…" if len(post.get("message") or "") > 220 else ""),
        )}

    if name == "send_newsletter":
        draft = _get_draft("newsletter")
        if not draft:
            raise ValueError("Aucun brouillon de newsletter — lance d'abord generate_newsletter.")
        scope = params.get("scope") or "test"
        email = (params.get("email") or "").strip()
        if scope == "all":
            return {"confirm": create_confirmation(
                "send_newsletter", {"scope": "all"},
                "Envoyer la newsletter à TOUS les abonnés ?",
                f"« {draft.get('subject', '')} » partira vers tous les abonnés.",
            )}
        return {"confirm": create_confirmation(
            "send_newsletter", {"scope": "test", "email": email},
            "Envoyer un email de test ?",
            f"« {draft.get('subject', '')} » sera envoyé à {email or '(adresse manquante)'}.",
        )}

    raise ValueError(f"Outil inconnu : {name}")


# ── Chat principal ───────────────────────────────────────────────────────────

def _coerce_str(value) -> str:
    """Texte sûr depuis une valeur IA : str/nombre acceptés, le reste → ''."""
    if isinstance(value, str):
        return value.strip()
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _normalize_tool(tool) -> dict | None:
    """Champ tool → {"name": str, "params": dict} ou None, quel que soit le format.

    Les modèles renvoient parfois "tool":"add_map_points" (chaîne), des params
    encodés en JSON-chaîne, ou un objet sans params : sans normalisation, ces
    variantes faisaient soit planter le chat ('str' object has no attribute
    'get'), soit ignorer silencieusement l'action demandée.
    """
    if isinstance(tool, str):
        name = tool.strip()
        if not name or name.lower() in ("null", "none"):
            return None
        tool = {"name": name, "params": {}}
    if not isinstance(tool, dict):
        return None
    name = tool.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    params = tool.get("params") or tool.get("parameters") or tool.get("arguments")
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError:
            params = {}
    if not isinstance(params, dict):
        params = {}
    # Nombres isolés (ex. price_hint: 50000) → texte, pour que les .strip()
    # des handlers restent sûrs ; listes/dicts/bools conservés tels quels.
    params = {
        k: (str(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
        for k, v in params.items()
    }
    return {"name": name.strip(), "params": params}


def _normalize_reply(data) -> dict:
    """Réponse IA → dict {message, actions, tool} TOUJOURS exploitable.

    Malgré le json_mode et le prompt, les modèles dévient parfois du schéma :
    réponse = chaîne ou liste, actions en liste de chaînes, tool aplati au
    niveau racine… On répare ici au lieu de laisser remonter une AttributeError
    jusqu'au chat de l'admin.
    """
    if isinstance(data, list):
        data = next((d for d in data if isinstance(d, dict)), None) or {
            "message": "\n".join(x for x in data if isinstance(x, str)),
        }
    if isinstance(data, str):
        data = {"message": data}
    if not isinstance(data, dict):
        data = {"message": _coerce_str(data)}

    message = data.get("message")
    if isinstance(message, list):
        message = "\n".join(x for x in message if isinstance(x, str))
    if not isinstance(message, str):
        message = _coerce_str(message)

    actions = data.get("actions")
    if isinstance(actions, dict):
        actions = [actions]
    norm_actions: list[dict] = []
    for a in actions if isinstance(actions, list) else []:
        if isinstance(a, str):
            a = {"label": a, "url": a}
        if isinstance(a, dict):
            norm_actions.append(a)

    tool = _normalize_tool(data.get("tool"))
    if tool is None and isinstance(data.get("name"), str) and (
        "params" in data or data.get("name", "").strip() in _KNOWN_TOOLS
    ):
        # Outil aplati à la racine : {"message":…, "name":"web_search", "params":{…}}
        tool = _normalize_tool({"name": data["name"], "params": data.get("params")})

    return {**data, "message": message.strip(), "actions": norm_actions, "tool": tool}


_KNOWN_TOOLS = {
    "web_search", "search_images", "audit_site", "generate_guide", "generate_seo_page",
    "generate_seo_matrix", "generate_seo_batch", "generate_destination",
    "generate_newsletter", "generate_social_post", "set_destination_region",
    "update_article", "add_category", "improve_article", "update_destination",
    "improve_destination", "update_pages", "update_image", "update_images",
    "add_map_points", "update_map_images",
    "publish_draft", "publish_facebook", "publish_social", "send_newsletter",
    "find_influencers", "add_partner",
}


def _ask_linh(user_block: str) -> dict:
    from admin import ai_client

    resp = ai_client.chat_completion(
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": user_block},
        ],
        max_tokens=1600,
        # Température basse : Linh doit rester factuelle et collée à son contexte
        # (anti-hallucination) — la créativité est utile aux générateurs, pas ici.
        temperature=0.3,
        json_mode=True,
        deadline=90,
    )
    raw = resp.choices[0].message.content
    try:
        data = ai_client.parse_json(raw)
    except ValueError:
        # JSON irrécupérable : on montre le texte brut plutôt que planter le chat.
        data = {"message": (raw or "").strip(), "tool": None}
    return _normalize_reply(data)


def _web_search_round(user_block: str, params: dict, first: dict) -> dict:
    """Exécute la recherche web demandée par Linh puis redemande la réponse finale.

    Une seule passe par message : la recherche est faite côté serveur, ses
    résultats sont réinjectés dans le prompt et Linh rédige une réponse sourcée.
    """
    from admin.web_search import format_results, search_web

    query = (params.get("query") or "").strip()
    try:
        results = search_web(query, max_results=6)
    except Exception as exc:  # noqa: BLE001 — la recherche échoue, pas le chat
        first["message"] = ((first.get("message") or "").strip() + f"\n\n⚠️ {exc}").strip()
        first["tool"] = None
        return first

    followup = (
        user_block
        + "\n\nRÉSULTATS WEB (recherche effectuée à l'instant) :\n"
        + format_results(query, results)
        + "\n\nRédige maintenant ta réponse finale au MESSAGE DE L'ADMIN en t'appuyant "
        "sur ces RÉSULTATS WEB : cite dans le message les URLs sources que tu utilises, "
        "et signale ce que la recherche ne permet pas de confirmer. "
        "Ne rappelle plus l'outil web_search."
    )
    data = _ask_linh(followup)
    tool = data.get("tool")
    if isinstance(tool, dict) and (tool.get("name") or "").strip() in ("web_search", "search_images"):
        data["tool"] = None  # une seule recherche par message — pas de boucle
    return data


def _image_search_round(user_block: str, params: dict, first: dict) -> dict:
    """Exécute la recherche d'IMAGES demandée par Linh puis redemande la réponse finale.

    Même flux en deux temps que web_search, mais sur les banques d'images libres
    (Pixabay, Openverse, Wikimedia Commons, DuckDuckGo Images) : les candidates ont
    des URLs DIRECTES téléchargeables, Linh peut donc enchaîner immédiatement
    update_image/update_images si l'admin a demandé un remplacement.
    """
    from admin.image_search import format_image_results, search_images

    query = (params.get("query") or "").strip()
    try:
        results = search_images(query, max_results=8)
    except Exception as exc:  # noqa: BLE001 — la recherche échoue, pas le chat
        first["message"] = ((first.get("message") or "").strip() + f"\n\n⚠️ {exc}").strip()
        return first

    followup = (
        user_block
        + "\n\nRÉSULTATS IMAGES (recherche effectuée à l'instant sur les banques d'images libres) :\n"
        + format_image_results(query, results)
        + "\n\nRédige maintenant ta réponse finale au MESSAGE DE L'ADMIN : "
        "1) si l'admin a demandé de CHANGER/REMPLACER une image, appelle DIRECTEMENT l'outil "
        "update_image (ou update_images) avec en image_url l'URL DIRECTE du meilleur résultat "
        "ci-dessus (champ image_url, JAMAIS le champ page) — privilégie une image large "
        "(≥ 1200 px) et en rapport exact avec le sujet ; "
        "2) sinon, présente les 3 à 5 meilleures images (titre, dimensions, source, image_url) "
        "et propose de l'appliquer. N'invente AUCUNE URL ; ne rappelle plus search_images."
    )
    data = _ask_linh(followup)
    tool = data.get("tool")
    if isinstance(tool, dict) and (tool.get("name") or "").strip() in ("web_search", "search_images"):
        data["tool"] = None  # une seule recherche par message — pas de boucle
    return data


# Linh dit « je recherche… » sans appeler web_search : on force la recherche
# plutôt que de laisser l'admin attendre un résultat qui ne viendra jamais.
_SEARCH_CLAIM_RE = re.compile(
    r"(je (?:vais |re)?cherche|je vais v[ée]rifier|laissez?[- ]moi (?:chercher|v[ée]rifier)|"
    r"recherche en cours|je recherche sur internet|un instant[^.]{0,40}(?:cherche|recherche)|"
    r"i(?:'|’)?ll (?:search|look)|let me (?:search|check)|searching the web)",
    re.I,
)


def _build_context(message: str, history: list[dict]) -> tuple[dict, str]:
    snapshot = build_site_snapshot()
    inventory = build_admin_inventory()
    findings = run_audit(snapshot)

    hist_lines = []
    for turn in (history or [])[-8:]:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = _coerce_str(turn.get("content"))[:700]
        if role in ("user", "assistant") and content:
            hist_lines.append(f"{role.upper()}: {content}")

    user_block = (
        f"ÉTAT DU SITE (données réelles):\n{_format_snapshot(snapshot)}\n\n"
        f"PAGES ADMIN (tu les connais toutes):\n{_format_inventory(inventory)}\n\n"
        f"AUDIT AUTOMATIQUE (problèmes détectés):\n{_format_findings(findings[:10])}\n\n"
        f"PAGES PUBLIQUES (page_id pour generate_social_post):\n{_format_public_pages()}\n\n"
        "HISTORIQUE:\n" + ("\n".join(hist_lines) if hist_lines else "(premier message)") + "\n\n"
        f"MESSAGE DE L'ADMIN:\n{message}"
    )
    return snapshot, user_block


def _finalize(data: dict, snapshot: dict) -> dict:
    """Actions (liens internes) + exécution de l'outil demandé par Linh."""
    from admin import ai_client

    actions = []
    for link in (data.get("actions") or [])[:4]:
        if isinstance(link, str):
            link = {"label": link, "url": link}
        if not isinstance(link, dict):
            continue
        url = _coerce_str(link.get("url"))
        if url.startswith("/") and not url.startswith("//"):
            actions.append({"label": (_coerce_str(link.get("label")) or url)[:90], "url": url})

    result = {
        "ok": True,
        "message": (data.get("message") or "").strip(),
        "actions": actions,
    }

    tool = data.get("tool")
    if isinstance(tool, dict) and tool.get("name"):
        try:
            result.update(_handle_tool(tool, snapshot))
        except ValueError as exc:
            result["message"] = (result["message"] + f"\n\n⚠️ {exc}").strip()
        except Exception as exc:  # noqa: BLE001 — l'outil échoue, pas le chat
            result["message"] = (result["message"] + f"\n\n⚠️ Échec de l'action : {ai_client.friendly_error(exc)}").strip()

    return result


def _tool_name(data: dict) -> str:
    tool = data.get("tool")
    if isinstance(tool, dict):
        return (tool.get("name") or "").strip()
    return ""


def chat_reply(message: str, history: list[dict]) -> dict:
    if not is_enabled():
        raise ValueError("Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY).")

    message = (message or "").strip()
    if len(message) < 2:
        raise ValueError("Message trop court.")
    if len(message) > 1500:
        raise ValueError("Message trop long (1500 caractères max).")

    # Confirmation / annulation textuelle : exécutée DIRECTEMENT, sans repasser
    # par le modèle — une seule confirmation suffit (clic sur la carte OU « oui »).
    if _is_cancellation(message):
        token = _pop_session_pending()
        if token:
            cancel_confirmation(token)
            return {
                "ok": True,
                "message": "C'est annulé — **rien n'a été publié**. Le brouillon éventuel reste disponible dans l'admin.",
                "actions": [],
            }
    affirmed = _is_affirmation(message)
    if affirmed:
        token = _pop_session_pending()
        if token:
            try:
                result = execute_confirmation(token)
            except ValueError as exc:
                return {"ok": True, "message": f"⚠️ {exc}", "actions": []}
            if result.get("async") and result.get("job_token"):
                return {
                    "ok": True,
                    "message": result.get("message") or "⏳ Action en cours…",
                    "action_job": {"token": result["job_token"]},
                    "actions": [],
                }
            actions = []
            url = (result.get("url") or "").strip()
            if url.startswith("/") and not url.startswith("//"):
                actions.append({"label": "Ouvrir", "url": url})
            return {"ok": True, "message": result.get("message") or "✅ Fait.", "actions": actions}

    snapshot, user_block = _build_context(message, history)

    if affirmed:
        # L'admin valide une proposition de Linh (aucune action serveur en
        # attente) : on exige l'appel d'outil au lieu d'un « c'est fait » vide.
        user_block += (
            "\n\nNOTE SYSTÈME : le MESSAGE DE L'ADMIN est une CONFIRMATION de ta dernière "
            "proposition (voir HISTORIQUE). Appelle MAINTENANT l'outil correspondant "
            "(champ \"tool\" non null) — ne repose pas de question, ne redemande pas "
            "confirmation, ne dis pas que c'est fait sans outil."
        )

    data = _ask_linh(user_block)

    if affirmed and not _tool_name(data):
        # Linh « comprend mais n'applique pas » : une relance stricte, une seule.
        data = _ask_linh(
            user_block
            + "\n\nRAPPEL SYSTÈME : ta réponse précédente n'a déclenché AUCUN outil alors que "
            "l'admin a confirmé. Réponds à nouveau avec le champ \"tool\" rempli pour exécuter "
            "l'action confirmée, ou explique en une phrase quel paramètre exact te manque."
        )

    # Recherche internet : flux en deux temps — on renvoie tout de suite
    # l'annonce + un marqueur "search", le widget affiche un loader et rappelle
    # /api/assistant/search qui exécute la recherche et rédige la réponse finale.
    if _tool_name(data) in ("web_search", "search_images"):
        tool = data.get("tool") or {}
        query = (_coerce_str((tool.get("params") or {}).get("query")) or message)[:200]
        if _tool_name(data) == "search_images":
            intro = (data.get("message") or "").strip() or f"Je cherche des images : « {query} »…"
            return {"ok": True, "message": intro, "actions": [], "search": {"query": query, "kind": "images"}}
        intro = (data.get("message") or "").strip() or f"Je lance une recherche sur internet : « {query} »…"
        return {"ok": True, "message": intro, "actions": [], "search": {"query": query, "kind": "web"}}
    if not _tool_name(data) and _SEARCH_CLAIM_RE.search(data.get("message") or ""):
        return {
            "ok": True,
            "message": (data.get("message") or "").strip(),
            "actions": [],
            "search": {"query": message[:200], "kind": "web"},
        }

    return _finalize(data, snapshot)


def search_reply(query: str, message: str, history: list[dict], kind: str = "web") -> dict:
    """Deuxième temps de la recherche web/images : exécute la recherche puis
    Linh rédige sa réponse finale sourcée (le widget affiche un loader entre les
    deux temps et revient seul avec les résultats réels).

    kind="images" → banques d'images libres (search_images) ; sinon DuckDuckGo texte.
    """
    if not is_enabled():
        raise ValueError("Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY).")

    query = re.sub(r"\s+", " ", (query or "")).strip()[:200]
    if len(query) < 2:
        raise ValueError("Requête de recherche vide.")
    message = (message or "").strip() or query

    snapshot, user_block = _build_context(message, history)
    round_fn = _image_search_round if kind == "images" else _web_search_round
    data = round_fn(user_block, {"query": query}, {"message": "", "tool": None})
    return _finalize(data, snapshot)


def build_insights() -> dict:
    """Briefing d'ouverture du widget : audit express + suggestions."""
    snapshot = build_site_snapshot()
    findings = run_audit(snapshot)
    high = sum(1 for f in findings if f["severity"] == "haute")
    if not findings:
        greeting = (
            f"Bonjour, je suis {ASSISTANT_NAME} 🧭 — votre copilote développement & SEO. "
            "L'audit automatique ne détecte **aucun problème** : parlons stratégie de contenu."
        )
    else:
        greeting = (
            f"Bonjour, je suis {ASSISTANT_NAME} 🧭 — votre copilote développement & SEO. "
            f"J'ai analysé le site : **{len(findings)} point(s) d'attention**"
            + (f" dont **{high} prioritaire(s)**" if high else "")
            + ". Voici l'essentiel — demandez-moi le plan d'action, ou déléguez-moi la création de contenus."
        )
    return {
        "ok": True,
        "greeting": greeting,
        "findings": findings[:6],
        "suggestions": SUGGESTIONS,
        "traffic": {
            "views_30d": snapshot.get("traffic", {}).get("views_30d", 0),
            "organic_pct": snapshot.get("seo", {}).get("organic_share_pct", 0),
        },
    }
