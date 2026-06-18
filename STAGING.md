# Environnement de staging

Deux environnements **totalement isolés** (code, base de données, secrets) :

| | Production | Staging |
|---|---|---|
| Branche GitHub | `main` | `staging` |
| App Scalingo | `insidevietnamtravel` | `staginginside` |
| URL | https://www.insidevietnamtravel.fr | https://staginginside.osc-fr1.scalingo.io |
| Base de données | Projet Supabase **prod** | Projet Supabase **staging** (distinct) |
| Auto-deploy | push sur `main` | push sur `staging` |
| Indexation Google | indexée | **noindex** (`SITE_NOINDEX=true`) |
| Stripe | clés **live** | test / désactivé |
| SMTP | actif | désactivé |

## Isolation des bases

Prod et staging utilisent **deux projets Supabase différents** : la `DATABASE_URL`
de chaque app pointe sur son propre projet. Aucune écriture de staging ne touche la
prod, et inversement. Le schéma est créé automatiquement au démarrage de l'app
(`admin/database.ensure_schema()`) — aucune migration manuelle nécessaire.

## Workflow

```
feature → staging (déploie sur staginginside, test) → main (déploie en prod)
```

Le drapeau `SITE_NOINDEX` est piloté par variable d'environnement et reste désactivé
par défaut : aucun impact sur la production. Il est activé uniquement sur l'app
`staginginside` pour empêcher Google d'indexer le double public du site.
