"""Partenariats (influenceurs, guides, blogueurs, agences…) — store + recherche IA.

Store KV `partnerships` (Supabase JSONB ou data/store/partnerships.json) :
[{id, name, type, email, links[], topics, followers, status, source, notes,
  created_at, updated_at, last_contacted_at}]

`search_and_save_influencers(brief)` : recherche web (DuckDuckGo via web_search),
récupération des pages trouvées pour en EXTRAIRE LES EMAILS, structuration par IA
(nom, type, réseaux, email), puis enregistrement dédupliqué avec le statut
« à contacter ». Utilisée par l'outil Linh `find_influencers` et par la page
/admin/partnerships. Le contact se fait ensuite depuis /admin/newsletter
(email IA ou manuel, comme la newsletter).
"""

from __future__ import annotations

import re
import secrets
import time
from datetime import date

import requests

from admin.kv_store import get_json, set_json

PARTNER_TYPES = [
    ("influenceur", "🌟 Influenceur"),
    ("blogueur", "✍️ Blogueur / créateur"),
    ("guide", "🧭 Guide local"),
    ("agence", "🏢 Agence / tour-opérateur"),
    ("hotel", "🏨 Hôtel / hébergement"),
    ("autre", "🤝 Autre"),
]
PARTNER_TYPE_KEYS = {k for k, _ in PARTNER_TYPES}
PARTNER_TYPE_LABELS = dict(PARTNER_TYPES)

PARTNER_STATUSES = [
    ("a_contacter", "À contacter"),
    ("contacte", "Contacté"),
    ("en_discussion", "En discussion"),
    ("actif", "Partenariat actif"),
    ("refuse", "Refusé / sans suite"),
]
PARTNER_STATUS_KEYS = {k for k, _ in PARTNER_STATUSES}
PARTNER_STATUS_LABELS = dict(PARTNER_STATUSES)

FETCH_TIMEOUT = (4, 7)
MAX_PAGE_BYTES = 400_000
USER_AGENT = ("Mozilla/5.0 (compatible; InsideVietnamTravel/1.0; "
              "+https://www.insidevietnamtravel.fr)")

# Domaines qu'on ne télécharge pas pour chercher un email (anti-bot / inutile).
_NO_FETCH_DOMAINS = ("instagram.com", "tiktok.com", "youtube.com", "facebook.com",
                     "x.com", "twitter.com", "pinterest.", "linkedin.com")

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,10}")
_EMAIL_JUNK = ("example.", "sentry", "wixpress", "yourdomain", "domain.com",
               "email.com", "@2x", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
               "no-reply", "noreply", "w3.org", "schema.org")

# Locaux d'email génériques (info@, contact@…) — pas de prénom exploitable.
_GENERIC_EMAIL_LOCALS = frozenset({
    "info", "contact", "hello", "bonjour", "support", "team", "admin", "sales",
    "partnership", "partenariat", "collab", "hi", "mail", "office", "press",
    "media", "booking", "reservation", "reservations", "service", "services",
    "enquiries", "inquiry", "news", "marketing", "commercial", "business",
    "noreply", "no-reply", "webmaster", "postmaster", "abuse", "help", "careers",
})


# ── Store ─────────────────────────────────────────────────────────────────

def get_partnerships() -> list[dict]:
    stored = get_json("partnerships", [], file_name="partnerships.json")
    return list(stored) if stored else []


def save_partnerships(items: list[dict]) -> None:
    set_json("partnerships", items, file_name="partnerships.json")


def find_partnership(pid: str) -> dict | None:
    return next((p for p in get_partnerships() if p.get("id") == pid), None)


def find_partnership_by_email(email: str) -> dict | None:
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return None
    return next(
        (p for p in get_partnerships() if (p.get("email") or "").strip().lower() == email),
        None,
    )


def is_generic_contact_email(email: str) -> bool:
    """True si l'adresse est un contact générique (info@, contact@…)."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return True
    local = email.split("@", 1)[0].split("+", 1)[0]
    if local in _GENERIC_EMAIL_LOCALS:
        return True
    return any(local.startswith(f"{g}.") for g in ("info", "contact", "hello", "mail"))


def partnership_greeting(partner_name: str = "", recipient_email: str = "") -> str:
    """Salutation pour emails partenariat sans prénom de contact."""
    name = (partner_name or "").strip()
    email = (recipient_email or "").strip().lower()

    if email and not is_generic_contact_email(email):
        local = email.split("@", 1)[0].split("+", 1)[0]
        parts = re.split(r"[._-]+", local)
        if parts and parts[0] not in _GENERIC_EMAIL_LOCALS and len(parts[0]) >= 2:
            first = parts[0].capitalize()
            if first.isalpha():
                return f"Bonjour {first},"

    if name:
        return f"Bonjour à l'équipe {name},"
    return "Bonjour,"


def _normalize_links(links) -> list[str]:
    if isinstance(links, str):
        links = re.split(r"[\s,;]+", links)
    out = []
    for raw in links or []:
        url = str(raw).strip()
        if url.startswith("http") and url not in out:
            out.append(url[:300])
    return out[:8]


def _normalize(data: dict) -> dict:
    name = str(data.get("name") or "").strip()[:120]
    if not name:
        raise ValueError("Le nom du partenaire est obligatoire.")
    ptype = str(data.get("type") or "influenceur").strip().lower()
    if ptype not in PARTNER_TYPE_KEYS:
        ptype = "autre"
    status = str(data.get("status") or "a_contacter").strip().lower()
    if status not in PARTNER_STATUS_KEYS:
        status = "a_contacter"
    email = str(data.get("email") or "").strip().lower()[:160]
    if email and "@" not in email:
        email = ""
    today = date.today().isoformat()
    return {
        "id": data.get("id") or secrets.token_urlsafe(8),
        "name": name,
        "type": ptype,
        "email": email,
        "links": _normalize_links(data.get("links")),
        "topics": str(data.get("topics") or "").strip()[:200],
        "followers": str(data.get("followers") or "").strip()[:60],
        "status": status,
        "source": str(data.get("source") or "manuel").strip()[:40],
        "notes": str(data.get("notes") or "").strip()[:1000],
        "created_at": data.get("created_at") or today,
        "updated_at": today,
        "last_contacted_at": data.get("last_contacted_at") or "",
    }


def _is_duplicate(candidate: dict, existing: list[dict]) -> bool:
    email = (candidate.get("email") or "").lower()
    name = (candidate.get("name") or "").lower()
    for p in existing:
        if email and (p.get("email") or "").lower() == email:
            return True
        if name and (p.get("name") or "").lower() == name:
            return True
    return False


def add_partnership(data: dict) -> dict:
    partner = _normalize(data)
    items = get_partnerships()
    if _is_duplicate(partner, items):
        raise ValueError(f"« {partner['name']} » existe déjà dans les partenariats.")
    items.insert(0, partner)
    save_partnerships(items)
    return partner


def update_partnership(pid: str, fields: dict) -> dict:
    items = get_partnerships()
    for i, p in enumerate(items):
        if p.get("id") != pid:
            continue
        merged = {**p, **{k: v for k, v in fields.items() if v is not None}, "id": pid}
        items[i] = _normalize(merged)
        save_partnerships(items)
        return items[i]
    raise ValueError(f"Partenaire introuvable : {pid}")


def delete_partnership(pid: str) -> None:
    items = [p for p in get_partnerships() if p.get("id") != pid]
    save_partnerships(items)


def mark_contacted(pid: str) -> None:
    """Après un envoi d'email réussi : statut « contacté » + date (best-effort)."""
    mark_partner_emailed(partner_id=pid)


def mark_partner_emailed(*, partner_id: str = "", email: str = "") -> dict | None:
    """Met à jour last_contacted_at ; passe à « contacté » si encore « à contacter »."""
    partner = find_partnership(partner_id) if partner_id else None
    if not partner and email:
        partner = find_partnership_by_email(email)
    if not partner:
        return None
    try:
        fields = {"last_contacted_at": date.today().isoformat()}
        if partner.get("status") == "a_contacter":
            fields["status"] = "contacte"
        return update_partnership(partner["id"], fields)
    except Exception:  # noqa: BLE001
        return None


def sync_contacted_status_from_history() -> None:
    """Partenaires avec envoi ou date de contact mais statut « à contacter » → « contacté »."""
    from admin.email_tracking_service import get_latest_sends_by_partner

    items = get_partnerships()
    ids = [p["id"] for p in items if p.get("id")]
    sends = get_latest_sends_by_partner(ids)
    for p in items:
        if p.get("status") != "a_contacter":
            continue
        pid = p.get("id")
        if sends.get(pid) or p.get("last_contacted_at"):
            mark_partner_emailed(partner_id=pid)


def partnership_stats() -> dict:
    items = get_partnerships()
    by_status = {k: 0 for k, _ in PARTNER_STATUSES}
    with_email = 0
    for p in items:
        by_status[p.get("status", "a_contacter")] = by_status.get(p.get("status", "a_contacter"), 0) + 1
        if p.get("email"):
            with_email += 1
    return {
        "total": len(items),
        "with_email": with_email,
        "by_status": by_status,
        "recent": [p.get("name", "?") for p in items[:5]],
    }


def get_partners_pending_contact() -> list[dict]:
    """Partenaires avec email au statut « à contacter » (liste newsletter admin)."""
    return [
        p for p in get_partnerships()
        if p.get("email") and p.get("status", "a_contacter") == "a_contacter"
    ]


# ── Recherche d'influenceurs (web + extraction email + IA) ────────────────

def _extract_emails(text: str) -> list[str]:
    emails = []
    for m in _EMAIL_RE.findall(text or ""):
        low = m.lower()
        if any(junk in low for junk in _EMAIL_JUNK):
            continue
        if low not in emails:
            emails.append(low)
        if len(emails) >= 3:
            break
    return emails


def _fetch_page_emails(url: str) -> list[str]:
    if any(d in url.lower() for d in _NO_FETCH_DOMAINS):
        return []
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT})
        if resp.status_code >= 400:
            return []
        html = resp.content[:MAX_PAGE_BYTES].decode(resp.encoding or "utf-8", errors="ignore")
        # mailto: d'abord (les plus fiables), puis le texte de la page
        mailtos = re.findall(r'mailto:([^"\'>?\s]+)', html)
        return _extract_emails(" ".join(mailtos) + " " + html)
    except Exception:  # noqa: BLE001
        return []


def _build_queries(brief: str) -> list[str]:
    brief = re.sub(r"\s+", " ", (brief or "")).strip()
    base = brief or "influenceur voyage Vietnam"
    if "vietnam" not in base.lower():
        base += " Vietnam"
    return [
        f"{base} contact email partenariat",
        f"{base} blog voyage \"work with me\" OR \"contact\"",
        f"{base} instagram créateur collaboration",
    ]


def search_influencers(brief: str, progress=None) -> list[dict]:
    """Cherche des influenceurs/créateurs voyage Vietnam ouverts aux partenariats.

    Renvoie des candidats structurés [{name, type, email, links, topics,
    followers, notes}] — email vide si introuvable sur les pages publiques.
    """
    from admin import ai_client
    from admin.web_search import search_web

    ai_client.require_api_key()
    report = progress or (lambda *_: None)

    report("Recherche web des influenceurs et créateurs voyage Vietnam…")
    results: list[dict] = []
    seen_urls: set[str] = set()
    errors = 0
    for query in _build_queries(brief):
        try:
            for row in search_web(query, max_results=6):
                url = row.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(row)
        except Exception:  # noqa: BLE001
            errors += 1
        if len(results) >= 14:
            break
    if not results:
        raise ValueError("Recherche web indisponible ou sans résultat — réessayez dans un instant.")

    report(f"Lecture des pages trouvées ({min(len(results), 6)}) pour extraire les emails…")
    fetched = 0
    for row in results:
        if fetched >= 6:
            break
        if any(d in row["url"].lower() for d in _NO_FETCH_DOMAINS):
            continue
        emails = _fetch_page_emails(row["url"])
        fetched += 1
        if emails:
            row["emails"] = emails
        time.sleep(0.2)

    report("Structuration des contacts par IA (nom, réseau, email)…")
    listing = "\n".join(
        f"{i+1}. {r.get('title', '')}\n   URL : {r.get('url', '')}\n"
        f"   Extrait : {r.get('snippet', '')[:220]}"
        + (f"\n   EMAILS TROUVÉS SUR LA PAGE : {', '.join(r['emails'])}" if r.get("emails") else "")
        for i, r in enumerate(results[:14])
    )
    system = (
        "Tu identifies des partenaires potentiels (influenceurs, blogueurs, créateurs, "
        "guides locaux, agences) pour « Inside Vietnam Travel », un site français de "
        "voyage au Vietnam qui cherche des collaborations (articles invités, posts "
        "sponsorisés, échanges de visibilité, affiliation)."
    )
    user = (
        f"BRIEF DE L'ADMIN : {brief or 'influenceurs voyage Vietnam'}\n\n"
        f"RÉSULTATS WEB (avec emails extraits des pages quand trouvés) :\n{listing}\n\n"
        "À partir de ces résultats UNIQUEMENT, liste les personnes/medias RÉELS et "
        "PERTINENTS pour un partenariat voyage Vietnam (pas les annuaires, agrégateurs, "
        "articles de presse génériques ni grandes plateformes). Pour chaque candidat :\n"
        "- name : nom de la personne ou du blog/média\n"
        "- type : influenceur | blogueur | guide | agence | hotel | autre\n"
        "- email : UNIQUEMENT un email présent dans les résultats ci-dessus, sinon \"\"\n"
        "- links : URLs de ses pages/profils (depuis les résultats)\n"
        "- topics : sa niche en quelques mots (ex. « backpacking Vietnam, food »)\n"
        "- followers : taille d'audience si mentionnée, sinon \"\"\n"
        "- notes : pourquoi c'est un bon partenaire potentiel (1 phrase)\n"
        "N'INVENTE NI EMAIL NI NOM. Maximum 8 candidats.\n"
        'Réponds STRICTEMENT en JSON : {"candidates":[{"name":"…","type":"…","email":"…",'
        '"links":["…"],"topics":"…","followers":"…","notes":"…"}]}'
    )
    resp = ai_client.chat_completion(
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=1600, temperature=0.3, json_mode=True, deadline=60,
    )
    data = ai_client.parse_json(resp.choices[0].message.content)
    candidates = data.get("candidates") or []
    return [c for c in candidates if isinstance(c, dict) and (c.get("name") or "").strip()][:8]


def search_and_save_influencers(brief: str, progress=None) -> dict:
    """Recherche + enregistrement dédupliqué (statut « à contacter », source linh)."""
    report = progress or (lambda *_: None)
    candidates = search_influencers(brief, progress=report)
    report("Enregistrement des contacts dans Partenariats…")

    items = get_partnerships()
    saved: list[dict] = []
    skipped = 0
    for c in candidates:
        try:
            partner = _normalize({**c, "status": "a_contacter", "source": "recherche linh"})
        except ValueError:
            continue
        if _is_duplicate(partner, items):
            skipped += 1
            continue
        items.insert(0, partner)
        saved.append(partner)
    if saved:
        save_partnerships(items)
    return {"candidates": candidates, "saved": saved, "skipped": skipped}
