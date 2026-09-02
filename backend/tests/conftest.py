"""Configuration commune aux tests.

Les secrets sont obligatoires dans Settings ; on les fournit ici avec des
valeurs de test pour que l'import de app.config n'échoue pas.
"""

import os

os.environ.setdefault(
    "BA_DATABASE_URL",
    "postgresql+asyncpg://body:test@localhost:5432/body_analysis_test",
)
os.environ.setdefault("BA_MINIO_ACCESS_KEY", "test-access-key")
os.environ.setdefault("BA_MINIO_SECRET_KEY", "test-secret-key")
