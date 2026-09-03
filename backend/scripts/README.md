# Scripts

Ces scripts jetables tournent dans l'image `api` de `docker compose`, avec
un montage supplémentaire en lecture seule vers les données source (qui ne
font pas partie de l'image ni du dépôt) et en rejoignant le réseau de la
stack pour parler à `db` et `minio` par leur nom de service.

## migrate_legacy.py

Charge un export Samsung Health et un `phases.json` existants dans la base.
Jetable : conservé pour pouvoir rejouer la migration initiale, pas destiné à
évoluer. L'ingestion courante passe par l'API.

```bash
docker compose up -d db test-db minio
docker run --rm \
  --network body-analysis_default \
  -v /home/sedelpeuch/migration_body-analysis:/data:ro \
  -e BA_DATABASE_URL="postgresql+asyncpg://body:${POSTGRES_PASSWORD:-bodypass}@db:5432/body_analysis" \
  -e BA_MINIO_ENDPOINT=minio:9000 \
  -e BA_MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}" \
  -e BA_MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}" \
  -e BA_MINIO_BUCKET=body-analysis-photos \
  -e BA_MINIO_SECURE=false \
  body-analysis-api \
  uv run python -m scripts.migrate_legacy /data
```

Le script est idempotent : le relancer met à jour sans dupliquer.

## seed_photos.py

Envoie les photos de suivi historiques dans MinIO via le même service que
l'endpoint POST /api/photos. Jetable, comme migrate_legacy.py : l'envoi
courant de photos passe par l'API.

```bash
docker compose up -d db test-db minio
docker run --rm \
  --network body-analysis_default \
  -v /home/sedelpeuch/migration_body-analysis/photos:/photos:ro \
  -e BA_DATABASE_URL="postgresql+asyncpg://body:${POSTGRES_PASSWORD:-bodypass}@db:5432/body_analysis" \
  -e BA_MINIO_ENDPOINT=minio:9000 \
  -e BA_MINIO_ACCESS_KEY="${MINIO_ROOT_USER:-minioadmin}" \
  -e BA_MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD:-minioadmin}" \
  -e BA_MINIO_BUCKET=body-analysis-photos \
  -e BA_MINIO_SECURE=false \
  body-analysis-api \
  uv run python -m scripts.seed_photos /photos
```

Idempotent : le relancer ne duplique aucune photo, et un fichier modifié
depuis le dernier passage remplace l'ancien pour son (date, tag). Une
photo dont le contenu (sha256) est déjà associé à un autre (date, tag) est
signalée et ignorée plutôt que de faire échouer tout le run.
