# Steam Arena - Documentation Technique

## Vue d'ensemble du projet

Steam Arena est une plateforme d'analyse de données Steam permettant de comparer des utilisateurs, analyser des bibliothèques de jeux, et visualiser des statistiques avec Machine Learning.

### Stack Technique

**Backend:**
- FastAPI 0.104.1
- PostgreSQL 15
- SQLAlchemy (ORM)
- Intégration Steam API (Store API)

**Frontend:**
- Next.js 14.0.4
- TypeScript
- Recharts (visualisation de données)
- Tailwind CSS

**Infrastructure:**
- Docker & Docker Compose
- Conteneurs: frontend, backend, database

## Structure du Projet

```
steam-arena/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── dashboard.py      # Stats utilisateur, genres
│   │   │   ├── games.py          # Gestion jeux, sync genres
│   │   │   ├── users.py          # Gestion utilisateurs
│   │   │   └── ml.py             # Clustering ML
│   │   ├── services/
│   │   │   └── data_service.py   # Sync Steam API
│   │   └── models/               # Models SQLAlchemy
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── admin/            # Interface admin
│       │   ├── users/[id]/       # Profils utilisateurs
│       │   ├── games/[id]/       # Détails jeux
│       │   ├── compare/          # Comparaison users
│       │   └── ml/               # ML Analytics
│       └── lib/
│           └── api.ts            # Client API centralisé
└── docker-compose.yml
```

## Fonctionnalités Principales

### 1. Gestion des Utilisateurs
- Sync profils Steam via Steam Web API
- Affichage stats: total jeux, playtime, achievements
- Graphique "Playtime by Genre" (PieChart)
- Modal interactive d'équivalences de temps de jeu

### 2. Gestion des Jeux
- Liste complète des jeux avec filtres
- Pages détails par jeu (header, stats, liste propriétaires)
- Sync automatique des genres via Steam Store API
- Catégorisation par genres et catégories

### 3. Synchronisation des Genres
**Endpoints:**
- `POST /api/v1/games/sync-popular-genres?limit=100` - Sync top N jeux populaires
- `POST /api/v1/games/sync-all-genres?delay_seconds=1.5` - Sync tous les jeux (batch)

**Stratégie:**
- Utilise Steam Store API pour récupérer détails jeux
- Délai configurable entre requêtes (anti-throttling)
- Gestion erreurs avec rollback
- Merge strategy pour éviter duplications

### 4. ML Analytics
- Clustering K-Means des utilisateurs
- Visualisation PCA (2 composantes principales)
- Analyse par clusters (taille, playtime moyen, jeux favoris)

### 5. Comparaison Utilisateurs
- Jeux communs entre 2+ utilisateurs
- Différences de playtime
- Jeux uniques par utilisateur

### 6. Interface Admin
- Bouton "Sync 100 Jeux Populaires" (~2-3 min)
- Bouton "Sync Tous les Jeux" (heures pour milliers de jeux)
- Affichage résultats: synced/skipped/failed/total
- Gestion erreurs avec messages détaillés

## Schéma Base de Données

### Tables Principales

**users**
- id (PK)
- steam_id (unique)
- persona_name
- avatar_url, avatar_full_url
- profile_url
- country_code
- created_at, updated_at

**games**
- id (PK)
- app_id (unique)
- name
- header_image
- short_description
- developer, publisher
- metacritic_score
- is_free
- created_at

**user_games** (many-to-many)
- user_id (FK)
- game_id (FK)
- playtime_forever
- playtime_2weeks
- rtime_last_played

**genres**
- id (PK)
- name (unique)

**game_genres** (many-to-many)
- game_id (FK)
- genre_id (FK)

**categories**
- id (PK)
- name (unique)

**game_categories** (many-to-many)
- game_id (FK)
- category_id (FK)

## Endpoints API Importants

### Utilisateurs
- `GET /api/v1/users/` - Liste utilisateurs
- `GET /api/v1/users/{steam_id}` - Détails utilisateur
- `POST /api/v1/users/{steam_id}/sync` - Sync profil Steam
- `GET /api/v1/users/{steam_id}/games` - Jeux utilisateur
- `GET /api/v1/dashboard/users/{steam_id}` - Dashboard stats
- `GET /api/v1/dashboard/users/{steam_id}/playtime-by-genre` - Stats genres

### Jeux
- `GET /api/v1/games/` - Liste jeux (avec filtres optionnels)
- `GET /api/v1/games/{game_id}` - Détails jeu
- `GET /api/v1/games/{game_id}/owners` - Propriétaires
- `POST /api/v1/games/sync-popular-genres?limit=100` - Sync genres populaires
- `POST /api/v1/games/sync-all-genres?delay_seconds=1.5` - Sync tous genres

### ML & Comparaison
- `GET /api/v1/ml/cluster-users` - Clustering utilisateurs
- `POST /api/v1/users/compare` - Comparer utilisateurs

## Problèmes Résolus Récemment

### 1. Crash page Compare
**Problème:** `can't access property persona_name, u.user is undefined`
**Cause:** Backend retourne structure plate mais frontend attendait objet imbriqué
**Solution:** Mise à jour interface TypeScript, suppression références `u.user.*`

### 2. ML Analytics "No clusters yet"
**Problème:** Données non affichées malgré clustering réussi
**Cause:** Backend retourne `{cluster_analysis: [...]}` mais frontend attendait array direct
**Solution:** Extraction `clustersRes.data?.cluster_analysis`

### 3. Genres manquants en base
**Problème:** "No genre data available" partout
**Cause:** Genres jamais synchronisés depuis Steam Store API
**Solution:** Création endpoints batch sync avec admin UI

### 4. UniqueViolation lors sync genres
**Problème:** Erreur `duplicate key game_genres_pkey`
**Cause:** Insertions concurrentes/répétées de relations many-to-many
**Solution:** Remplacement `db.add()` par `db.merge()` + `db.expire_all()` + try/except avec rollback

### 5. Graphique "Playtime by Genre" vide
**Problème:** PieChart n'affiche rien après sync genres
**Cause:** Interface utilisait `playtime_hours` mais backend renvoie `total_playtime_hours`
**Solution:** Mise à jour interface GenrePlaytime + dataKey du PieChart

## Améliorations UX Récentes

### Modal Équivalences Temps de Jeu
Clic sur carte "Playtime" → pop-up avec 6 catégories d'équivalences créatives:
- 📚 Études (langues, certifications, livres)
- 🌍 Voyages (tours du monde, Paris-Marseille)
- 💪 Sport (km courus, calories, pompes)
- 🎬 Divertissement (films, séries, Beethoven)
- 😴 Sommeil (nuits, jours, années de vie)
- ✨ Message positif

### Palette Couleurs Graphique Genres
Remplacement 8 nuances de bleu par 12 couleurs variées:
- Rouge corail, Turquoise, Jaune doré
- Vert menthe, Rose saumon, Violet pastel
- Orange ambré, Vert émeraude, Bleu océan
- Rose vif, Orange lumineux, Violet profond

### Nettoyage Fiche Jeu
- Suppression affichage App ID (information technique non nécessaire)
- Conservation: Developer, Publisher, Metacritic Score

## Configuration & Déploiement

### Variables d'environnement
```env
# Backend
STEAM_API_KEY=<votre_clé_steam>
DATABASE_URL=postgresql://postgres:postgres@db:5432/steam_arena

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Lancement
```bash
# Build et démarrage
docker compose up -d --build

# Rebuild frontend uniquement
docker compose up -d --build frontend

# Rebuild backend uniquement
docker compose up -d --build backend

# Logs
docker compose logs -f frontend
docker compose logs -f backend
```

### Accès
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Workflow Sync Genres Recommandé

1. Aller sur page Admin (/admin)
2. Cliquer "Sync 100 Jeux Populaires" pour démarrage rapide
3. Attendre 2-3 minutes (délai 1.5s entre requêtes)
4. Vérifier résultats affichés (synced/skipped/failed)
5. Optionnel: "Sync Tous les Jeux" pour couverture complète (plusieurs heures)
6. Genres apparaissent dans:
   - Graphique "Playtime by Genre" (profils users)
   - Filtres page Games (à implémenter)
   - Stats ML Analytics

## Notes Importantes

- **Rate Limiting Steam API:** Délai 1.5s entre requêtes recommandé
- **Taille Base:** Peut atteindre plusieurs GB avec tous les jeux synchronisés
- **Performance:** Utiliser indexes sur steam_id, app_id, genre_id, category_id
- **Erreurs TypeScript:** Erreurs génériques JSX normales dans ce projet
- **Données manquantes:** Tous les jeux Steam n'ont pas header_image/metacritic_score

## Roadmap Potentiel

- [ ] Filtres par genre sur page Games
- [ ] Export données utilisateur (CSV/JSON)
- [ ] Système de recommendations basé sur ML
- [ ] Graphiques tendances temporelles
- [ ] Comparaison groupes d'utilisateurs
- [ ] Badges/achievements personnalisés
- [ ] Mode sombre/clair
- [ ] Responsive mobile optimisé
