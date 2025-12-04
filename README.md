# 🎮 Steam Arena

Une plateforme sociale Steam complète pour analyser et comparer les profils de joueurs, avec des fonctionnalités ML avancées.

## ✨ Fonctionnalités

### 📊 Dashboard Social
- Comparer le temps de jeu entre utilisateurs
- Suivre les achievements et la progression
- Analyser le backlog de jeux
- Visualiser les genres préférés

### 👥 Analyse de Groupe d'Amis
- Créer des groupes d'utilisateurs Steam
- Trouver les jeux que tous les membres possèdent
- Comparer les statistiques de groupe
- Identifier les jeux avec la plus grande intersection

### 🤖 Machine Learning
- **Clusters de joueurs** : Segmentation KMeans basée sur le comportement
- **Extraction de features** : Temps de jeu, taux de complétion, diversité de genres
- **Recommandations** : Collaborative, content-based, et hybride
- **Export dataset** : JSON ou CSV pour analyse externe

### ⚡ Pipeline Airflow
- DAG de synchronisation automatique (toutes les 6h)
- Synchronisation batch de multiples Steam IDs
- Synchronisation de groupe sur demande

## 🏗️ Architecture

```
steam-arena/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database connection
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── users.py         # User endpoints
│   │   │   ├── groups.py        # Group endpoints
│   │   │   ├── games.py         # Game endpoints
│   │   │   ├── dashboard.py     # Dashboard/stats endpoints
│   │   │   └── ml.py            # ML endpoints
│   │   └── services/
│   │       ├── steam_api.py     # Steam API client
│   │       ├── data_service.py  # Data sync service
│   │       └── ml_service.py    # ML service
│   ├── db/
│   │   └── init.sql             # Database schema
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/
│   │       └── api.ts           # API client
│   ├── Dockerfile
│   └── package.json
├── airflow/
│   └── dags/
│       └── steam_sync_dag.py    # Airflow DAGs
├── docker-compose.yml
└── .env.example
```

## 🚀 Démarrage

### Prérequis
- Docker et Docker Compose
- Une clé API Steam (obtenir sur https://steamcommunity.com/dev/apikey)

### Installation

1. **Cloner le projet**
```bash
git clone <repo-url>
cd steam-arena
```

2. **Configurer l'environnement**
```bash
cp .env.example .env
# Éditer .env et ajouter votre STEAM_API_KEY
```

3. **Lancer les services**
```bash
docker-compose up -d
```

4. **Accéder aux interfaces**
- Frontend: http://localhost:3000
- API Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Airflow: http://localhost:8080 (admin/admin)

## 📡 API Endpoints

### Users
- `GET /api/v1/users` - Liste des utilisateurs
- `POST /api/v1/users` - Ajouter un utilisateur
- `GET /api/v1/users/{id}` - Détails utilisateur
- `POST /api/v1/users/{id}/sync/profile` - Sync profil
- `POST /api/v1/users/{id}/sync/games` - Sync jeux
- `POST /api/v1/users/{id}/sync/achievements` - Sync achievements

### Groups
- `GET /api/v1/groups` - Liste des groupes
- `POST /api/v1/groups` - Créer un groupe
- `GET /api/v1/groups/{id}` - Détails groupe
- `POST /api/v1/groups/{id}/members` - Ajouter membres
- `GET /api/v1/groups/{id}/comparison` - Comparer membres
- `GET /api/v1/groups/{id}/game-intersection` - Jeux en commun

### Dashboard
- `GET /api/v1/dashboard/stats` - Statistiques globales
- `GET /api/v1/dashboard/user/{id}` - Dashboard utilisateur
- `GET /api/v1/dashboard/user/{id}/playtime-by-genre` - Temps par genre
- `GET /api/v1/dashboard/compare` - Comparer utilisateurs

### ML
- `POST /api/v1/ml/extract-all-features` - Extraire features
- `POST /api/v1/ml/cluster` - Clustering des joueurs
- `GET /api/v1/ml/clusters` - Voir les clusters
- `GET /api/v1/ml/users/{id}/recommendations` - Recommandations
- `GET /api/v1/ml/export-dataset` - Exporter dataset

## 🛠️ Technologies

### Backend
- **FastAPI** - Framework API moderne
- **SQLAlchemy** - ORM Python
- **PostgreSQL** - Base de données
- **Redis** - Cache
- **Airflow** - Orchestration de pipelines

### Frontend
- **Next.js 14** - Framework React
- **TailwindCSS** - Styling
- **Recharts** - Visualisations
- **TypeScript** - Type safety

### ML
- **scikit-learn** - KMeans clustering
- **pandas** - Manipulation de données
- **numpy** - Calculs numériques

## 📊 Modèle de Données

### Tables principales
- `steam_users` - Profils Steam
- `games` - Catalogue de jeux
- `genres` - Genres de jeux
- `user_games` - Jeux possédés par utilisateur
- `achievements` / `user_achievements` - Système d'achievements
- `user_groups` / `group_members` - Groupes d'amis
- `ml_player_features` - Features ML extraites
- `recommendations` - Recommandations générées

## 🔧 Configuration

Variables d'environnement (`.env`):
```env
# Database
POSTGRES_USER=steam_arena
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=steam_arena

# Redis
REDIS_URL=redis://redis:6379

# Steam API
STEAM_API_KEY=your_steam_api_key

# Backend
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://steam_arena:password@postgres:5432/steam_arena

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📈 Utilisation ML

### 1. Extraire les features
```bash
curl -X POST http://localhost:8000/api/v1/ml/extract-all-features
```

### 2. Lancer le clustering
```bash
curl -X POST "http://localhost:8000/api/v1/ml/cluster?n_clusters=5"
```

### 3. Obtenir des recommandations
```bash
curl http://localhost:8000/api/v1/ml/users/{user_id}/recommendations?recommendation_type=hybrid
```

### 4. Exporter le dataset
```bash
curl "http://localhost:8000/api/v1/ml/export-dataset?format=csv" > dataset.csv
```

## 🎯 Airflow DAGs

### steam_user_sync
- **Schedule**: Toutes les 6 heures
- **Action**: Synchronise tous les utilisateurs enregistrés

### steam_batch_sync (Manuel)
- **Config**: Liste de Steam IDs en paramètre
- **Action**: Synchronise une liste spécifique d'utilisateurs

### steam_group_sync (Manuel)
- **Config**: Group ID en paramètre
- **Action**: Synchronise tous les membres d'un groupe

## 📝 License

MIT

## 🤝 Contribution

Les contributions sont les bienvenues ! Ouvrez une issue ou une PR
