# Body Analysis App

Application Streamlit pour le suivi et l'analyse corporelle, phases, photos et import de données Samsung Health.

## Fonctionnalités principales

- **Dashboard** : Vue d'ensemble, graphiques de poids, composition corporelle, calories
- **Phases** : Analyse détaillée par phase (bulk, cut, maintien, libre), métriques mensuelles, variation, pourcentage
- **Photos** : Timeline mensuelle par tag (face, profil, dos, bras, épaule), confidentialité, auto-rotation, affichage uniforme
- **Import** : Upload CSV Samsung Health (poids, alimentation), upload photos, organisation automatique, phases.json

## Installation locale

### Prérequis

- Python 3.11
- [Poetry](https://python-poetry.org/)

### Installation

```bash
poetry install
```

### Lancement

```bash
streamlit run body_analysis/dashboard.py
```

## Déploiement Docker

### Build et lancement local

```bash
# Build l'image
docker-compose build

# Lancer le service
docker-compose up -d

# Accès : http://localhost:8501
```

### Déploiement sur Docker Swarm

```bash
# Initialiser le swarm (si besoin)
docker swarm init

# Déployer le stack
docker stack deploy -c docker-compose.yml body-analysis

# Accès : http://<swarm-manager-ip>:8501
```

### Mise à jour du service

```bash
# Rebuild l'image
docker-compose build

# Mettre à jour le service sur Swarm
docker service update --image body-analysis:latest body-analysis_body-analysis
```

## Configuration

- **Données persistantes** : Le volume `./data` contient les CSV, photos et phases.json
- **Variables d'environnement** : `TZ` (Europe/Paris par défaut)
- **Réseau** : Overlay pour Swarm
- **Ressources** : Limite à 1 CPU / 1GB RAM
- **Health check** : Vérification automatique de Streamlit

## Structure des dossiers

```
body_analysis/
├── body_analysis/
│   ├── dashboard.py
│   ├── pages/
│   └── ...
├── data/
│   ├── com.samsung.health.weight.YYYYMMDD.csv
│   ├── com.samsung.health.food_intake.YYYYMMDD.csv
│   ├── phases.json
│   └── photos/
│       └── YYYY-MM/
│           └── tag.jpg
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── README.md
```

## Utilisation

1. **Importer les données** : Utiliser la page Import pour uploader les CSV et photos
2. **Configurer les phases** : Éditer `data/phases.json` pour définir les périodes
3. **Analyser** : Naviguer entre Dashboard, Phases et Photos pour visualiser l'évolution

## Dépannage

- **Logs Docker Compose** : `docker-compose logs -f`
- **Logs Swarm** : `docker service logs -f body-analysis_body-analysis`
- **Permissions data/** : `chmod -R 755 data/`

## Auteurs

- Sébastien Delpeuch <sebastien@delpeuch.net>

---

Pour toute question ou amélioration, ouvrez une issue sur le dépôt GitHub.
