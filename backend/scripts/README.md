# Scripts

## migrate_legacy.py

Charge un export Samsung Health et un `phases.json` existants dans la base.
Jetable : conservé pour pouvoir rejouer la migration initiale, pas destiné à
évoluer. L'ingestion courante passe par l'API.

```bash
cd backend
uv run python -m scripts.migrate_legacy /home/sedelpeuch/migration_body-analysis
```

Le script est idempotent : le relancer met à jour sans dupliquer.

## seed_photos.py

Envoie les photos de suivi historiques dans MinIO via le même service que
l'endpoint POST /api/photos. Jetable, comme migrate_legacy.py : l'envoi
courant de photos passe par l'API.

```bash
cd backend
uv run python -m scripts.seed_photos /home/sedelpeuch/migration_body-analysis/photos
```

Idempotent : le relancer ne duplique aucune photo, et un fichier modifié
depuis le dernier passage remplace l'ancien pour son (date, tag).
