"""IA interne « Linh » 🧭 — copilote développement & SEO de l'admin.

Différente de Mai (widget public pour les voyageurs) : Linh conseille l'ADMIN sur
l'évolution du site — détection de problèmes, améliorations, idées de contenus,
priorités et calendrier, toujours avec un objectif SEO. Elle connaît :
- toutes les pages /admin (inventaire DYNAMIQUE depuis l'url_map : une nouvelle
  page admin apparaît automatiquement dans sa connaissance) ;
- l'état réel du site (articles, destinations, analytics, SEO, GEO/LLM,
  affiliation, revenus, newsletter, avis, contact, configuration IA/Facebook).

Elle peut aussi AGIR (tout ce que l'admin peut faire) : générer un guide, une
destination, une newsletter ou un post Facebook — via les mêmes jobs en tâche de
fond que l'admin (draft_store, mêmes tokens de session : le brouillon apparaît
aussi dans la page admin correspondante). Toute PUBLICATION (site, newsletter,
réseaux sociaux) exige une confirmation explicite de l'admin : l'action est mise
en attente côté serveur et n'est exécutée qu'après clic sur « Confirmer ».
"""

from __future__ import annotations

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

ASSISTANT_NAME = "Linh"

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
    "admin.destinations_admin": ("Destinations", "Création/édition des pages destinations (IA ou manuel), images WebP, choix de la section Nord/Centre/Sud, publication sur /<slug>."),
    "admin.map_admin": ("Carte", "Points d'intérêt et pins affiliés (hôtels, activités) sur les cartes interactives des destinations."),
    "admin.newsletter_admin": ("Newsletter", "Composition d'emails (IA ou manuel), envoi test / abonné / tous, gestion des abonnés."),
    "admin.social": ("Réseaux sociaux", "Génération IA et publication de posts Facebook (lien UTM ou photo), configuration page/token."),
    "admin.contact_admin": ("Contact", "Messages reçus via le formulaire de contact public (lu / suppression)."),
    "admin.reviews_admin": ("Avis", "Gestion des témoignages voyageurs affichés sur le site."),
    "admin.affiliates": ("Affiliation", "IDs partenaires (Booking, Agoda, GetYourGuide, eSIM…), vérification du tracking, stats de clics."),
    "admin.revenue": ("Revenus", "Saisie des commissions reçues, estimé vs confirmé, historique."),
    "admin.analytics": ("Analytics", "Trafic (7/30/90 j), temps réel, SEO organique, GEO (trafic depuis ChatGPT/Perplexity…), pays/villes, profils visiteurs."),
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
            "views_30d": stats.get("views_period", 0),
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
        "config": {
            "ai_provider": _safe(ai_client.provider, "?"),
            "ai_status": _safe(ai_client.provider_status, {}),
            "facebook_ok": _safe(_facebook_ok, False),
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
        f"Config: moteur IA {snap.get('config', {}).get('ai_provider')}, Facebook {'connecté' if snap.get('config', {}).get('facebook_ok') else 'NON connecté'}",
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
        "Tu peux AGIR à la place de l'admin via le champ \"tool\" : générer un guide, une "
        "destination, une newsletter, un post Facebook, puis publier/envoyer. "
        "RÈGLE ABSOLUE : toute publication (site, newsletter, Facebook) passe par une "
        "confirmation explicite de l'admin — le système s'en charge quand tu utilises un "
        "outil de publication ; n'affirme jamais avoir publié sans confirmation. "
        "N'utilise un outil QUE si l'admin demande une action ; pour une question, réponds sans outil. "
        f"VILLES autorisées pour generate_guide/generate_destination : {cities}. "
        "OUTILS disponibles (champ \"tool\", sinon null) :\n"
        '- {"name":"web_search","params":{"query":"…"}} — rechercher sur internet (DuckDuckGo) : '
        "actualités/réglementation Vietnam (visa, prix, événements), concurrence, tendances SEO, "
        "vérification de faits. Utilise-le SPONTANÉMENT dès qu'une réponse fiable exige une info "
        "absente de ton contexte, au lieu de deviner ; les résultats te seront fournis dans un "
        "bloc RÉSULTATS WEB et tu rédigeras alors ta réponse en citant les URLs sources\n"
        '- {"name":"audit_site","params":{}} — relancer l\'audit complet et présenter les résultats\n'
        '- {"name":"generate_guide","params":{"city":"…","topic":"…","guide_type":"article blog"}} — guide SEO (job en arrière-plan)\n'
        '- {"name":"generate_destination","params":{"city":"…","notes":"…"}} — page destination (job en arrière-plan)\n'
        '- {"name":"generate_newsletter","params":{"topic":"…","email_type":"actualite","notes":"…"}} — email newsletter (job en arrière-plan)\n'
        '- {"name":"generate_social_post","params":{"page_id":"…","brief":"…"}} — post Facebook (page_id du bloc PAGES PUBLIQUES, ou brief libre)\n'
        '- {"name":"set_destination_region","params":{"slug":"…","region":"north|central|south"}} — déplacer une destination publiée dans la colonne Nord/Centre/Sud du menu Destinations (confirmation auto)\n'
        '- {"name":"update_destination","params":{"slug":"…","tagline":"…","meta_title":"…","meta_description":"…","overview":"…","region":"…"}} — modifier une page destination publiée ; tous les champs sont optionnels, ne passe que ceux à changer (confirmation auto)\n'
        '- {"name":"publish_draft","params":{"kind":"article"}} ou {"kind":"destination"} — publier le brouillon en attente (confirmation auto)\n'
        '- {"name":"publish_facebook","params":{}} — publier le dernier post généré (confirmation auto)\n'
        '- {"name":"send_newsletter","params":{"scope":"test","email":"…"}} ou {"scope":"all"} — envoyer la newsletter (confirmation auto)\n'
        "Ton : direct, structuré, orienté impact — un consultant produit/SEO senior. "
        "Mets en avant 2 à 5 points clés avec **double astérisques**. Termine toujours ta réponse. "
        "Les \"actions\" sont des liens internes UNIQUEMENT (URLs commençant par « / », "
        "pages admin ou pages publiques du site). "
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
    return {"token": token, "title": title, "summary": summary, "type": action_type}


def cancel_confirmation(token: str) -> bool:
    with _PENDING_LOCK:
        return _PENDING.pop(token, None) is not None


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
    if action == "publish_destination":
        return _exec_publish_destination()
    if action == "publish_facebook":
        return _exec_publish_facebook()
    if action == "send_newsletter":
        return _exec_send_newsletter(params)
    if action == "set_destination_region":
        return _exec_set_destination_region(params)
    if action == "update_destination":
        return _exec_update_destination(params)
    raise ValueError(f"Action inconnue : {action}")


# ── Brouillons partagés avec l'admin (mêmes tokens de session) ───────────────

def _draft_token_key(kind: str) -> str:
    return f"{kind}_draft_token"


def _get_draft(kind: str) -> dict | None:
    from admin import draft_store
    return draft_store.get_draft(session.get(_draft_token_key(kind)))


def _start_job(kind: str, fn, initial_phase: str) -> None:
    from admin import draft_store
    from admin import ai_client
    token = draft_store.new_token()
    session[_draft_token_key(kind)] = token
    draft_store.start_job(token, fn, ai_client.friendly_error, initial_phase=initial_phase)


def job_status(kind: str) -> dict:
    """Statut d'un job de génération + carte de confirmation quand c'est prêt."""
    from admin import draft_store

    if kind not in ("article", "destination", "newsletter", "social"):
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
        msg = (draft.get("message") or "")[:220]
        return {
            "summary": "Post Facebook prêt :\n" + msg,
            "preview_url": "/admin/social",
            "confirm": create_confirmation(
                "publish_facebook", {}, "Publier ce post sur Facebook ?",
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


def _exec_publish_destination() -> dict:
    from admin import draft_store
    from admin.store import add_or_update_destination

    dest = _get_draft("destination")
    if not dest:
        raise ValueError("Aucun brouillon de destination — demandez d'abord une génération.")
    add_or_update_destination(dest)
    draft_store.clear(session.pop(_draft_token_key("destination"), None))
    return {"message": f"✅ Destination publiée : /{dest['slug']}", "url": f"/{dest['slug']}"}


def _exec_publish_facebook() -> dict:
    from admin import draft_store
    from admin import facebook_service as fb

    post = _get_draft("social")
    if not post:
        raise ValueError("Aucun post Facebook en attente — demandez d'abord une génération.")
    if not fb.is_configured():
        raise ValueError("Facebook non configuré (ID de page + token) — voir /admin/social.")
    link = post.get("link") or ""
    if link:
        result = fb.publish_link(post.get("message", ""), link)
    elif post.get("image"):
        result = fb.publish_photo(post.get("message", ""), post["image"])
    else:
        result = fb.publish_link(post.get("message", ""), _site_url())
    draft_store.clear(session.pop(_draft_token_key("social"), None))
    permalink = fb.post_permalink(result)
    return {"message": f"✅ Publié sur Facebook. {permalink}".strip(), "url": permalink}


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

    slug = (params.get("slug") or "").strip()
    dest = update_destination_fields(slug, params)
    return {
        "message": f"✅ Page destination mise à jour : « {dest.get('name', slug)} » (/{slug}).",
        "url": f"/{slug}",
    }


def _exec_send_newsletter(params: dict) -> dict:
    from admin.newsletter_service import get_newsletter_subscribers, send_newsletter_email

    draft = _get_draft("newsletter")
    if not draft:
        raise ValueError("Aucun brouillon de newsletter — demandez d'abord une génération.")
    scope = params.get("scope") or "test"
    if scope == "all":
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
    )
    if not result["sent"]:
        raise ValueError("Échec de l'envoi — vérifiez la configuration SMTP.")
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
        _start_job(
            "newsletter",
            lambda report: groq_newsletter.generate_newsletter_email(topic, email_type, notes, progress=report),
            "Rédaction de l'email…",
        )
        return {"job": {"kind": "newsletter"}}

    if name == "generate_social_post":
        from admin import draft_store
        from admin import facebook_service as fb
        from admin.social_ai import default_campaign, find_page, generate_post

        page = find_page((params.get("page_id") or "").strip(), "fr")
        brief = (params.get("brief") or "").strip()
        if not page and not brief:
            raise ValueError("Indique une page du site (page_id) ou un brief libre.")
        message = generate_post(page=page, brief=brief, lang="fr")
        campaign = default_campaign(page, brief)
        post = {
            "message": message,
            "link": fb.add_utm(page["url"], campaign) if page else "",
            "image": page["image"] if page else "",
            "campaign": campaign,
        }
        token = draft_store.new_token()
        draft_store.set_draft(token, post)
        session[_draft_token_key("social")] = token
        return {
            "post_preview": message,
            "confirm": create_confirmation(
                "publish_facebook", {}, "Publier ce post sur Facebook ?",
                message[:220] + ("…" if len(message) > 220 else ""),
            ),
        }

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

    if name == "update_destination":
        from admin.store import DESTINATION_EDITABLE_FIELDS, get_destination_by_slug

        slug = (params.get("slug") or "").strip()
        dest = get_destination_by_slug(slug)
        if not dest:
            raise ValueError(f"Destination introuvable : « {slug} » — vérifie le slug dans l'ÉTAT DU SITE.")
        changed = [k for k in (*DESTINATION_EDITABLE_FIELDS, "tips", "region") if params.get(k)]
        if not changed:
            raise ValueError("Aucun champ à modifier — passe au moins tagline, meta_title, meta_description, overview, tips ou region.")
        return {"confirm": create_confirmation(
            "update_destination", params,
            f"Modifier la page « {dest.get('name', slug)} » ?",
            f"/{slug} — champs modifiés : {', '.join(changed)}. La version EN sera retraduite automatiquement si le texte FR change.",
        )}

    if name == "publish_draft":
        kind = params.get("kind") or "article"
        draft = _get_draft(kind)
        if not draft:
            raise ValueError(f"Aucun brouillon « {kind} » en attente — lance d'abord une génération.")
        desc = _describe_draft(kind, draft)
        return {"confirm": desc.get("confirm"), "summary": desc.get("summary")}

    if name == "publish_facebook":
        post = _get_draft("social")
        if not post:
            raise ValueError("Aucun post Facebook en attente — lance d'abord generate_social_post.")
        desc = _describe_draft("social", post)
        return {"confirm": desc.get("confirm")}

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
    return ai_client.parse_json(resp.choices[0].message.content)


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
    if isinstance(tool, dict) and (tool.get("name") or "").strip() == "web_search":
        data["tool"] = None  # une seule recherche par message — pas de boucle
    return data


def chat_reply(message: str, history: list[dict]) -> dict:
    from admin import ai_client

    if not is_enabled():
        raise ValueError("Aucune clé IA configurée (GROQ_API_KEY ou MISTRAL_API_KEY).")

    message = (message or "").strip()
    if len(message) < 2:
        raise ValueError("Message trop court.")
    if len(message) > 1500:
        raise ValueError("Message trop long (1500 caractères max).")

    snapshot = build_site_snapshot()
    inventory = build_admin_inventory()
    findings = run_audit(snapshot)

    hist_lines = []
    for turn in (history or [])[-8:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()[:700]
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

    data = _ask_linh(user_block)

    # Recherche internet : exécutée tout de suite (aller-retour serveur), les
    # autres outils suivent le circuit habituel via _handle_tool plus bas.
    tool = data.get("tool")
    if isinstance(tool, dict) and (tool.get("name") or "").strip() == "web_search":
        data = _web_search_round(user_block, tool.get("params") or {}, data)

    actions = []
    for link in (data.get("actions") or [])[:4]:
        url = (link.get("url") or "").strip()
        if url.startswith("/") and not url.startswith("//"):
            actions.append({"label": (link.get("label") or url)[:90], "url": url})

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
