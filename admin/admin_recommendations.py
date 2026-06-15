"""Recommandations contextuelles pour chaque page admin."""

from __future__ import annotations

from datetime import date

from admin.store import get_affiliate_ids
from data.affiliate_partners import BUILTIN_PARTNERS
from admin.store import is_configured


def _reco(title: str, body: str, *, priority: str = "info", action_label: str = "", action_url: str = "", icon: str = "💡") -> dict:
    return {
        "title": title,
        "body": body,
        "priority": priority,
        "action_label": action_label,
        "action_url": action_url,
        "icon": icon,
    }


def get_dashboard_recommendations(
    *,
    groq_ok: bool,
    affiliates_configured: int,
    affiliates_total: int,
    articles_count: int,
    totals: dict,
    est_commission: float,
) -> list[dict]:
    recos: list[dict] = []

    if not groq_ok:
        recos.append(_reco(
            "Activer la génération IA",
            "Ajoutez GROQ_API_KEY ou MISTRAL_API_KEY dans .env pour générer des guides SEO automatiquement.",
            priority="haute",
            action_label="Ouvrir Guides IA",
            action_url="/admin/guides",
            icon="✦",
        ))

    if articles_count < 3:
        recos.append(_reco(
            "Publier vos premiers guides",
            f"Vous avez {articles_count} article(s). Visez 5–10 guides pour le référencement (Hanoï, Hội An, visa…).",
            priority="haute",
            action_label="Générer un guide",
            action_url="/admin/guides",
            icon="📚",
        ))

    if affiliates_configured < affiliates_total:
        missing = affiliates_total - affiliates_configured
        recos.append(_reco(
            f"{missing} partenaire(s) à configurer",
            "Booking et Agoda en priorité — ce sont vos liens hôtel les plus cliqués sur un site voyage.",
            priority="haute",
            action_label="Configurer l'affiliation",
            action_url="/admin/affiliates",
            icon="◇",
        ))

    if totals.get("total_visitors", 0) < 50:
        recos.append(_reco(
            "Booster le trafic initial",
            "Partagez vos articles sur Pinterest et forums voyage. Chaque visite alimente vos analytics.",
            priority="moyenne",
            action_label="Voir Analytics",
            action_url="/admin/analytics",
            icon="↗",
        ))

    if est_commission > 0 and totals.get("total_clicks", 0) > 0:
        recos.append(_reco(
            "Enregistrer vos commissions",
            f"~{est_commission:.0f} € estimés sur 30 jours — saisissez les paiements reçus des plateformes.",
            priority="moyenne",
            action_label="Saisir un revenu",
            action_url="/admin/revenue",
            icon="€",
        ))

    month = date.today().month
    if month in (3, 4, 9, 10):
        recos.append(_reco(
            "Saison haute Vietnam",
            "Publiez des guides « meilleure période » et itinéraires 2 semaines — pic de recherches printemps/automne.",
            priority="moyenne",
            action_label="Idées d'articles",
            action_url="/admin/guides",
            icon="🌏",
        ))

    if not recos:
        recos.append(_reco(
            "Tout est en ordre",
            "Continuez à publier du contenu et à suivre vos clics affiliés chaque semaine.",
            priority="info",
            icon="✓",
        ))

    return recos[:6]


def get_affiliate_recommendations(summary: dict) -> list[dict]:
    recos: list[dict] = []
    partners = summary.get("partners", [])
    unconfigured = [p for p in partners if not p.get("configured")]

    priority_order = ["booking", "agoda", "getyourguide", "viator", "esim_airalo"]
    for pid in priority_order:
        p = next((x for x in unconfigured if x.get("id") == pid), None)
        if p:
            recos.append(_reco(
                f"Configurer {p['name']}",
                p.get("what_you_earn", "Commission variable"),
                priority="haute",
                action_label="Voir la carte",
                action_url=f"#partner-{p['id']}",
                icon=p.get("icon", "🔗"),
            ))
        if len(recos) >= 3:
            break

    top = [p for p in partners if p.get("clicks", 0) > 0]
    if top:
        best = top[0]
        recos.insert(0, _reco(
            f"{best['name']} : votre meilleur convertisseur",
            f"{best['clicks']} clics sur la période — ~{best['estimated_eur']} € estimés. Doublez les liens sur les pages liées.",
            priority="info",
            icon="📈",
        ))

    if summary.get("clicks_period", 0) == 0:
        recos.append(_reco(
            "Aucun clic encore",
            "Visitez vos pages destinations (/hanoi, /hoi-an) et cliquez un lien test pour vérifier le tracking.",
            priority="moyenne",
            action_label="Voir le site",
            action_url="/",
            icon="🔍",
        ))

    if summary.get("estimated_eur", 0) > summary.get("confirmed_eur", 0) and summary.get("estimated_eur", 0) > 0:
        recos.append(_reco(
            "Écart estimé / confirmé",
            "Les plateformes paient avec 30–60 jours de délai. Enregistrez chaque paiement dans Revenus.",
            priority="moyenne",
            action_label="Saisir une commission",
            action_url="/admin/revenue",
            icon="€",
        ))

    if len(unconfigured) <= 2:
        recos.append(_reco(
            "Partenaires à ajouter",
            "Klook, 12Go.asia ou Heymondo complètent bien un site Vietnam (activités, bus, assurance).",
            priority="moyenne",
            icon="➕",
        ))

    return recos[:6]


def get_analytics_recommendations(stats: dict, days: int) -> list[dict]:
    recos: list[dict] = []
    visitors = stats.get("unique_visitors_period", 0)
    top_pages = stats.get("top_pages", [])

    if visitors == 0:
        recos.append(_reco(
            "Démarrer le suivi",
            "Naviguez sur le site public — chaque visiteur unique apparaîtra ici en quelques secondes.",
            priority="haute",
            action_label="Ouvrir le site",
            action_url="/",
            icon="↗",
        ))
    elif visitors < 100:
        recos.append(_reco(
            "Trafic en croissance",
            f"{visitors} visiteurs uniques sur {days} jours. Publiez 1–2 articles par semaine pour accélérer le SEO.",
            priority="moyenne",
            action_label="Guides IA",
            action_url="/admin/guides",
            icon="✦",
        ))

    if top_pages:
        best = top_pages[0]
        path = best.get("path", "/")
        recos.append(_reco(
            f"Page star : {path}",
            f"{best.get('c', 0)} visiteurs uniques (24h). Ajoutez des liens affiliés et un article complémentaire sur ce sujet.",
            priority="haute",
            action_label="Créer un guide",
            action_url="/admin/guides",
            icon="⭐",
        ))

        blog_pages = [p for p in top_pages if "/blog/" in p.get("path", "")]
        if not blog_pages and visitors > 20:
            recos.append(_reco(
                "Le blog attire peu",
                "Vos pages destinations performent mieux. Créez des articles qui renvoient vers /hanoi, /hoi-an…",
                priority="moyenne",
                action_url="/admin/guides",
                icon="📝",
            ))

    clicks = stats.get("clicks_30m", 0)
    if visitors > 50 and clicks == 0:
        recos.append(_reco(
            "Trafic sans clics affiliés",
            "Vérifiez que vos IDs affiliés sont configurés et que les CTA sont visibles dans les articles.",
            priority="haute",
            action_label="Affiliation",
            action_url="/admin/affiliates",
            icon="◇",
        ))

    if stats.get("active_visitors", 0) > 0:
        recos.append(_reco(
            f"{stats['active_visitors']} visiteur(s) en ce moment",
            "Consultez le flux temps réel pour voir quelles pages intéressent vos lecteurs.",
            priority="info",
            icon="🟢",
        ))

    seo = stats.get("seo") or {}
    organic = seo.get("total_organic_views", 0)
    organic_share = seo.get("organic_share_pct", 0)

    if visitors > 20 and organic == 0:
        recos.append(_reco(
            "Peu de trafic SEO détecté",
            "Les visites viennent surtout du direct ou des liens. Publiez des articles ciblés, "
            "soumettez le sitemap dans Google Search Console et renforcez les liens internes.",
            priority="haute",
            action_label="Guides IA",
            action_url="/admin/guides",
            icon="🔍",
        ))
    elif visitors > 50 and organic_share < 15:
        recos.append(_reco(
            f"SEO à {organic_share}% du trafic",
            f"Seulement {organic} visites organiques sur {days} jours. Optimisez titres/meta "
            "et créez du contenu sur les requêtes « voyage Vietnam » longue traîne.",
            priority="moyenne",
            action_label="Créer un guide",
            action_url="/admin/guides",
            icon="📈",
        ))
    elif organic >= 10:
        top_org = (seo.get("top_organic_pages") or [{}])[0]
        recos.append(_reco(
            f"Page SEO star : {top_org.get('path', '/')}",
            f"{top_org.get('views', 0)} visites depuis Google/Bing. Dupliquez ce format "
            "(FAQ, budget, itinéraire) sur d'autres villes.",
            priority="haute",
            action_label="Nouvel article",
            action_url="/admin/guides",
            icon="🏆",
        ))

    geo = stats.get("geo") or {}
    ai_views = geo.get("total_ai_views", 0)
    ai_share = geo.get("ai_share_pct", 0)

    if visitors > 0 and ai_views == 0:
        recos.append(_reco(
            "Activer la visibilité GEO",
            "Soumettez /llms.txt à Google Search Console et partagez vos guides sur Perplexity ou ChatGPT. "
            "Les robots IA (GPTBot, ClaudeBot) sont autorisés dans robots.txt.",
            priority="moyenne",
            action_label="Voir llms.txt",
            action_url="/llms.txt",
            icon="🤖",
        ))
    elif ai_views > 0 and ai_share < 5:
        recos.append(_reco(
            f"{ai_views} vues IA ({ai_share}%)",
            "Le trafic LLM est faible. Enrichissez vos FAQ et titres avec des questions directes "
            "(« comment préparer un voyage au Vietnam ? »).",
            priority="moyenne",
            action_label="Accueil",
            action_url="/",
            icon="🤖",
        ))
    elif ai_views >= 5:
        top_ai = (geo.get("top_ai_pages") or [{}])[0]
        recos.append(_reco(
            f"{ai_views} vues depuis les LLM ({ai_share}%)",
            f"Page la plus citée : {top_ai.get('path', '/')} — renforcez ce contenu et ajoutez des liens internes.",
            priority="haute",
            action_label="Analytics GEO",
            action_url="/admin/analytics",
            icon="🤖",
        ))

    if not recos:
        recos.append(_reco(
            "Analysez chaque semaine",
            "Comparez 7 vs 30 jours pour repérer les tendances et ajuster votre contenu.",
            priority="info",
            icon="📊",
        ))

    return recos[:6]


def get_revenue_recommendations(revenue: dict, est_commission: float, aff_stats: dict) -> list[dict]:
    recos: list[dict] = []
    total = revenue.get("total", 0)
    month_total = revenue.get("month_total", 0)
    entries = revenue.get("entries", [])

    if est_commission > 0 and total == 0:
        recos.append(_reco(
            "Première commission à saisir",
            f"~{est_commission:.0f} € estimés via les clics — dès qu'une plateforme vous paie, enregistrez-le ici.",
            priority="haute",
            icon="€",
        ))

    if est_commission > total * 1.5 and total > 0:
        recos.append(_reco(
            "Mise à jour recommandée",
            f"Estimation {est_commission:.0f} € vs {total:.0f} € enregistrés — des paiements manquent peut-être.",
            priority="moyenne",
            icon="📋",
        ))

    if not entries:
        recos.append(_reco(
            "Routine mensuelle",
            "Le 5 de chaque mois, exportez vos rapports Booking/Agoda et saisissez les montants reçus.",
            priority="moyenne",
            icon="📅",
        ))
    elif month_total == 0:
        recos.append(_reco(
            "Aucun revenu ce mois-ci",
            "Vérifiez vos emails partenaires — les commissions arrivent souvent avec 30–45 jours de retard.",
            priority="moyenne",
            icon="📬",
        ))

    by_provider = {r["provider"]: r["clicks"] for r in aff_stats.get("by_provider", [])}
    ids = get_affiliate_ids()
    for p in BUILTIN_PARTNERS[:4]:
        pid = p["id"]
        clicks = by_provider.get(pid, 0)
        aff_id = ids.get(p["id_key"], "")
        if clicks > 5 and not is_configured(aff_id):
            recos.append(_reco(
                f"Clics {p['name']} sans ID valide",
                f"{clicks} clics trackés — configurez l'ID pour que les conversions soient attribuées.",
                priority="haute",
                action_label="Configurer",
                action_url="/admin/affiliates",
                icon=p.get("icon", "🔗"),
            ))
            break

    recos.append(_reco(
        "Sources à ne pas oublier",
        "Booking, Agoda, GetYourGuide, eSIM et ventes PDF — une ligne par virement reçu.",
        priority="info",
        icon="💡",
    ))

    return recos[:6]
