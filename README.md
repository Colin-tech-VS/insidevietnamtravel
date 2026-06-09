# Inside Vietnam Travel

Site de guide voyage Vietnam (Python / Flask) — contenu SEO + liens affiliés.

**Ce n'est pas une agence de voyage.** Site indépendant : guides, itinéraires, blog et recommandations affiliées.

## Démarrage local

```bash
pip install -r requirements.txt
cp .env.example .env   # puis éditez .env
python app.py
```

→ Site : [http://localhost:5002](http://localhost:5002)  
→ Admin : [http://localhost:5002/admin](http://localhost:5002/admin) (mot de passe dans `.env`)

## Déploiement Scalingo

### 1. Créer l'app

```bash
# CLI Scalingo installée et connectée
scalingo create insidevietnamtravel --region osc-fr1
scalingo --app insidevietnamtravel git-setup
```

Ou liez le dépôt GitHub depuis le dashboard Scalingo (déploiement automatique à chaque push).

### 2. Variables d'environnement (obligatoires)

```bash
scalingo --app insidevietnamtravel env-set \
  SECRET_KEY="votre-cle-secrete-longue" \
  ADMIN_PASSWORD="votre-mot-de-passe-admin" \
  GROQ_API_KEY="gsk_..."
```

Optionnel :

```bash
scalingo --app insidevietnamtravel env-set \
  SITE_URL="https://votre-domaine.fr" \
  GA4_MEASUREMENT_ID="G-XXXXXXXX" \
  MISTRAL_API_KEY="..." \
  AI_PROVIDER="groq" \
  DATABASE_URL="postgresql://postgres.[REF]:[MDP]@aws-0-eu-west-3.pooler.supabase.com:6543/postgres"
```

**Moteur IA :** la rédaction (guides, destinations, newsletters) accepte **Groq** ou
**Mistral AI** — au moins une clé suffit. Mistral offre des limites par minute bien plus
larges que le palier gratuit Groq (utile pour les longs guides). Choisissez le moteur
actif dans l'admin (*Dashboard › Moteur de rédaction*) ; `AI_PROVIDER` ne fixe que le
défaut initial. Si le moteur actif échoue (limite atteinte), Groq prend le relais
automatiquement quand sa clé est présente.

**Important Supabase + Scalingo :** n'utilisez pas l'URL directe `db.xxx.supabase.co:5432` (IPv6, crash au boot). Préférez le **pooler** port **6543**, ou laissez l'app convertir automatiquement l'URL directe.

`SITE_URL` est auto-détecté si absent (`https://<app>.<region>.scalingo.io`).

### 3. Déployer

```bash
git push scalingo main
# ou push sur GitHub si l'intégration est activée
```

Le `Procfile` lance Gunicorn : `gunicorn app:app --bind 0.0.0.0:$PORT`

### Fichiers Scalingo

| Fichier | Rôle |
|---------|------|
| `Procfile` | Processus web Gunicorn |
| `requirements.txt` | Dépendances Python |
| `.python-version` | Version Python (3.12.8) |

### Base de données — Supabase (PostgreSQL)

En production, définissez `DATABASE_URL` (URI PostgreSQL Supabase). Sans cette variable, le site utilise des fichiers locaux (dev uniquement).

| Table / store | Contenu |
|---------------|---------|
| `app_kv` | Articles, destinations, settings, affiliés (JSONB) |
| `page_views`, `affiliate_clicks`, `revenue` | Analytics admin |
| `newsletter_subscribers` | Abonnés newsletter |

**Migration initiale** (une fois `DATABASE_URL` dans `.env`) :

```bash
python scripts/migrate_to_supabase.py
```

Schéma SQL de référence : `supabase/schema.sql`

Sur Scalingo :

```bash
scalingo --app insidevietnamtravel env-set DATABASE_URL="postgresql://..."
```

## Admin (`/admin`)

| Section | Fonction |
|---------|----------|
| **Dashboard** | Stats temps réel, revenus, statut + choix du moteur IA |
| **Guides IA** | Génération d'articles via IA (Groq ou Mistral) → publication blog |
| **Destinations** | Guides ville (IA ou manuel) |
| **Newsletter** | Abonnés + envoi email |
| **Affiliation** | IDs Booking, Agoda, GYG… + GA4 |
| **Revenus** | Suivi commissions + estimations par clics |
| **Analytics** | Vues, top pages, graphique 30j |

## Structure

```
app.py                    # Application Flask (WSGI)
Procfile                  # Scalingo / Gunicorn
config.py                 # Config site (SITE_URL)
data/
  store/                  # JSON persisté (articles, destinations, settings)
  affiliates.py           # Liens affiliés
templates/
static/
```

## Pages publiques

| URL | Description |
|-----|-------------|
| `/` | Homepage |
| `/hanoi`, `/ho-chi-minh-city`, `/hoi-an`, `/da-nang` | Guides ville |
| `/itineraries/3-days-vietnam` | Itinéraires |
| `/blog`, `/blog/[slug]` | Blog SEO |
| `/a-propos` | À propos |
| `/sitemap.xml`, `/robots.txt` | SEO |
