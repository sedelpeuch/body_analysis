# Body Analysis App

Application de suivi et d'analyse corporelle : phases, photos et import de données Samsung Health.

## Fonctionnalités principales

- **Dashboard** : Vue d'ensemble, graphiques de poids, composition corporelle, calories
- **Phases** : Analyse détaillée par phase (bulk, cut, maintien, libre), métriques mensuelles, variation, pourcentage
- **Photos** : Timeline mensuelle par tag (face, profil, dos, bras, épaule), confidentialité, auto-rotation, affichage uniforme
- **Import** : Upload CSV Samsung Health (poids, alimentation), upload photos, organisation automatique, phases.json

## Architecture

- **backend/** : API FastAPI (Python), persistance PostgreSQL, stockage des photos sur MinIO (S3)
- **frontend/** : SPA React + TypeScript + Vite, servie en production par nginx (reverse proxy `/api/` vers le backend)

## Installation locale

### Prérequis

- Docker et Docker Compose

### Lancement (dev)

```bash
cp backend/.env.example backend/.env   # renseigner les valeurs
cp frontend/.env.example frontend/.env
docker compose up -d
```

- Frontend (Vite, hot reload) : http://localhost:5173
- API : http://localhost:8000
- Console MinIO : http://localhost:9001

### Image de production du frontend

```bash
docker compose --profile prod up -d web-prod
```

## Tests

```bash
cd backend && uv sync --frozen && uv run pytest tests/unit
```

## CI/CD

Le workflow `.github/workflows/docker_build.yml` build et publie sur GHCR, à chaque push sur `master` :

- `ghcr.io/sedelpeuch/body-analysis-api` (depuis `backend/Dockerfile`)
- `ghcr.io/sedelpeuch/body-analysis-web` (depuis `frontend/Dockerfile`)

## Auteurs

- Sébastien Delpeuch <sebastien@delpeuch.net>
