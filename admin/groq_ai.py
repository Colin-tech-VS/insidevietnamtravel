"""Génération de guides via Groq AI — SEO maximal, cible voyageurs Vietnam."""

import json
import re
from datetime import date

from admin import ai_client
from admin.store import slugify
from admin.groq_translate import translate_article_block
from i18n_utils import merge_bilingual_article

# Longueur minimale selon type de guide (recommandations SEO).
# max_tokens dimensionné sur la cible réelle (≈ mots × 2,2 + ~400 de JSON/HTML)
# pour NE PAS réserver tout le budget tokens/minute de Groq. Garde une marge
# confortable contre la troncature, tout en restant bien sous 8192.
SEO_WORD_TARGETS: dict[str, dict] = {
    "Article blog SEO": {"min": 800, "target": 950, "max_tokens": 3584},
    "Guide pratique": {"min": 1000, "target": 1200, "max_tokens": 4608},
    "Guide ville": {"min": 1200, "target": 1500, "max_tokens": 5120},
    "Itinéraire": {"min": 1500, "target": 1800, "max_tokens": 6144},
    "Conseils budget": {"min": 1000, "target": 1200, "max_tokens": 4608},
    "Gastronomie": {"min": 900, "target": 1100, "max_tokens": 4096},
}

DEFAULT_SEO = {"min": 1000, "target": 1200, "max_tokens": 4608}

# On ne relance un enrichissement (appel supplémentaire) que si l'article est
# nettement sous la cible. Un texte à 90 %+ du minimum est déjà publiable et
# évite un second appel coûteux en tokens et en temps.
EXPAND_TOLERANCE = 0.9

SYSTEM_PROMPT = """Tu es un rédacteur SEO senior spécialisé voyage au Vietnam pour "Inside Vietnam Travel".

PUBLIC CIBLE (OBLIGATOIRE) :
- Français qui PRÉPARENT un voyage au Vietnam ou qui SOUHAITENT y aller.
- Réponses concrètes : visa, budget, itinéraire, où manger, quand partir, erreurs à éviter.
- Ton expert bienveillant, honnête, pratique. Préfère "vous".
- Ne jamais inventer de noms de personnes ni de statistiques fictives.

RÈGLES SEO STRICTES :
1. Title (H1) : 50–65 car., mot-clé principal en début, "Vietnam" ou ville si pertinent.
2. meta_title : 50–60 car., title tag SEO (peut différer du H1), mot-clé en tête, sans répétition inutile.
3. meta_description : 140–160 car., incitatif, mot-clé principal, cible voyageurs français.
4. Excerpt : 140–160 car., résumé visible sur la page.
5. Longueur : RESPECTER le nombre de mots minimum indiqué dans le message utilisateur (compter le texte du HTML sans balises).
6. HTML : uniquement <h2>, <h3>, <p>, <ul>, <li>, <blockquote>, <table> — pas de <h1>.
7. Structure : Intro, sections <h2> (min 5), FAQ (4–6 Q/R en <h3>+<p>), Conclusion.
8. Mot-clé principal dans les 100 premiers mots.
9. Listes <ul>, 1+ <blockquote>, tableau si budget/comparatif.
10. Fourchettes de prix en euros. Paragraphes courts.
11. Pas de liens externes. Contenu 100% Vietnam.

JSON uniquement :
{
  "title": "...",
  "meta_title": "...",
  "meta_description": "...",
  "excerpt": "...",
  "category": "practical|food|itinerary|budget",
  "category_label": "Pratique|Gastronomie|Itinéraire|Budget",
  "tags": ["..."],
  "read_time": 10,
  "focus_keyword": "...",
  "image_prompt": "Unique English prompt: specific Vietnam scene for THIS article only, photorealistic, 16:9, no text",
  "content": "<p>...</p>"
}
"""


def _count_words(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return len(text.split()) if text else 0


def _read_time_from_words(word_count: int) -> int:
    return max(5, round(word_count / 200))


def _seo_target(guide_type: str) -> dict:
    return SEO_WORD_TARGETS.get(guide_type, DEFAULT_SEO)


def _parse_response(raw: str) -> dict:
    data = json.loads(raw)
    if "content" not in data or "title" not in data:
        raise ValueError("Réponse IA incomplète")
    return data


def _build_article(data: dict, topic: str, city: str, guide_type: str) -> dict:
    slug = slugify(data.get("title", topic))
    tags = list(data.get("tags", []))
    if city and city != "Tout le Vietnam" and city not in tags:
        tags.insert(0, city)
    if "vietnam" not in [t.lower() for t in tags]:
        tags.append("Vietnam")

    word_count = _count_words(data["content"])

    return {
        "slug": slug,
        "title": data["title"].strip(),
        "meta_title": (data.get("meta_title") or data["title"])[:70].strip(),
        "meta_description": (data.get("meta_description") or data["excerpt"])[:160].strip(),
        "excerpt": data["excerpt"][:160].strip(),
        "category": data.get("category", "practical"),
        "category_label": data.get("category_label", "Pratique"),
        "date": date.today().isoformat(),
        "read_time": _read_time_from_words(word_count),
        "word_count": word_count,
        "featured": False,
        "tags": tags[:12],
        "focus_keyword": data.get("focus_keyword", topic),
        "image_prompt": data.get("image_prompt", ""),
        "guide_type": guide_type,
        "content": data["content"],
        "ai_generated": True,
        "city": city,
    }


def _call_ai(messages: list, max_tokens: int, *, fast: bool = False, pause_before: float = 0) -> dict:
    response = ai_client.chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        fast=fast,
        pause_before=pause_before,
    )
    return _parse_response(response.choices[0].message.content)


def _expand_if_short(article: dict, guide_type: str) -> dict:
    target = _seo_target(guide_type)
    min_words = target["min"]
    current = _count_words(article["content"])

    # Tolérance : on n'engage un second appel que si l'article est nettement court.
    if current >= min_words * EXPAND_TOLERANCE:
        article["word_count"] = current
        article["read_time"] = _read_time_from_words(current)
        return article

    expand_prompt = f"""L'article ci-dessous fait seulement {current} mots. Il DOIT atteindre au minimum {min_words} mots (cible {target['target']} mots).
Type : {guide_type}. Ville : {article.get('city', 'Vietnam')}.

Enrichis SANS changer le slug implicite ni le sujet :
- Ajoute des sections pratiques, FAQ, budget, erreurs à éviter
- Garde le HTML existant et complète
- Voyageurs français préparant un trip Vietnam

Article :
{json.dumps({k: article[k] for k in ('title', 'excerpt', 'content', 'tags', 'city') if k in article}, ensure_ascii=False)}"""

    # Enrichissement sur le modèle rapide : bucket tokens/minute distinct du
    # modèle principal (ne grignote pas son quota) et nettement plus véloce.
    data = _call_ai(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": expand_prompt},
        ],
        target["max_tokens"],
        fast=True,
        pause_before=1.5,
    )

    article.update({
        "title": data.get("title", article["title"]).strip(),
        "meta_title": data.get("meta_title", article.get("meta_title", article["title"]))[:70].strip(),
        "meta_description": data.get("meta_description", article.get("meta_description", article["excerpt"]))[:160].strip(),
        "excerpt": data.get("excerpt", article["excerpt"])[:160].strip(),
        "content": data.get("content", article["content"]),
        "tags": data.get("tags", article.get("tags", [])),
        "image_prompt": data.get("image_prompt", article.get("image_prompt", "")),
        "focus_keyword": data.get("focus_keyword", article.get("focus_keyword", "")),
    })
    wc = _count_words(article["content"])
    article["word_count"] = wc
    article["read_time"] = _read_time_from_words(wc)
    return article


def generate_guide(topic: str, guide_type: str, city: str) -> dict:
    ai_client.require_api_key()
    year = date.today().year
    seo = _seo_target(guide_type)

    user_prompt = f"""Rédige un guide COMPLET ultra-optimisé SEO.

Année : {year}
Type de guide : {guide_type}
Sujet / requête : {topic}
Ville / région (OBLIGATOIRE) : {city}

LONGUEUR OBLIGATOIRE : minimum {seo['min']} mots, cible {seo['target']} mots dans le champ content (texte hors balises HTML).

Le lecteur est un voyageur FRANÇAIS qui prépare ou envisage un voyage au Vietnam.

Exigences :
- "{city}" et "Vietnam" dans titre, intro, H2, FAQ
- FAQ : 4–6 questions Google réelles
- Budget avec tableau si pertinent
- Erreurs à éviter pour débutants
- image_prompt : scène Vietnam UNIQUE et spécifique à CE sujet (pas générique)"""

    data = _call_ai(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        seo["max_tokens"],
    )

    article = _build_article(data, topic, city, guide_type)
    article = _expand_if_short(article, guide_type)
    try:
        en_data = translate_article_block(article, pause_before=1.5)
        shared = {
            k: v for k, v in article.items()
            if k not in (
                "title", "meta_title", "meta_description", "excerpt", "content",
                "category_label", "tags", "focus_keyword", "image_alt",
            )
        }
        return merge_bilingual_article(article, en_data, shared)
    except Exception:
        return merge_bilingual_article(article, {}, {
            k: v for k, v in article.items()
            if k not in (
                "title", "meta_title", "meta_description", "excerpt", "content",
                "category_label", "tags", "focus_keyword", "image_alt",
            )
        })


def improve_guide(article: dict, instructions: str) -> dict:
    ai_client.require_api_key()
    guide_type = article.get("guide_type", "Guide pratique")
    seo = _seo_target(guide_type)

    data = _call_ai(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Améliore cet article pour voyageurs français préparant un trip Vietnam.\n"
                    f"Instructions : {instructions}\n"
                    f"Minimum {seo['min']} mots dans content.\n\n"
                    f"Article :\n{json.dumps(article, ensure_ascii=False)}"
                ),
            },
        ],
        seo["max_tokens"],
    )

    article.update({
        "title": data.get("title", article["title"]).strip(),
        "meta_title": data.get("meta_title", article.get("meta_title", article["title"]))[:70].strip(),
        "meta_description": data.get("meta_description", article.get("meta_description", article["excerpt"]))[:160].strip(),
        "excerpt": data.get("excerpt", article["excerpt"])[:160].strip(),
        "content": data.get("content", article["content"]),
        "tags": data.get("tags", article.get("tags", [])),
        "focus_keyword": data.get("focus_keyword", article.get("focus_keyword", "")),
        "image_prompt": data.get("image_prompt", article.get("image_prompt", "")),
        "date": date.today().isoformat(),
    })
    wc = _count_words(article["content"])
    article["word_count"] = wc
    article["read_time"] = _read_time_from_words(wc)
    article = _expand_if_short(article, guide_type)
    try:
        en_data = translate_article_block(article, pause_before=1.5)
        shared = {
            k: v for k, v in article.items()
            if k not in (
                "title", "meta_title", "meta_description", "excerpt", "content",
                "category_label", "tags", "focus_keyword", "image_alt", "i18n",
            )
        }
        return merge_bilingual_article(article, en_data, shared)
    except Exception:
        return article
