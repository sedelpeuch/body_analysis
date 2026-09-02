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
