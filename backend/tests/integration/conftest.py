"""Base de données jetable pour les tests d'intégration.

Nécessite le service db de compose. Le schéma est créé en passant par
Alembic plutôt que par `Base.metadata` : ce dernier ne connaît pas les vues
matérialisées introduites par la tâche 12, alors que la conformité de la
migration au modèle est déjà vérifiée séparément par la tâche 4.

L'URL de la base de test n'a volontairement aucun défaut en dur (contrainte
globale « aucun identifiant en dur ») : elle doit venir de l'environnement,
par exemple depuis `backend/.env`. Si elle est absente, les tests
d'intégration sont marqués skip plutôt que d'échouer.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.storage.minio import MinioStorage

TEST_DATABASE_URL = os.environ.get("BA_TEST_DATABASE_URL")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    if not TEST_DATABASE_URL:
        pytest.skip(
            "BA_TEST_DATABASE_URL n'est pas défini : tests d'intégration ignorés",
        )

    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    await asyncio.to_thread(command.downgrade, config, "base")
    await asyncio.to_thread(command.upgrade, config, "head")

    created = create_async_engine(TEST_DATABASE_URL)
    yield created
    await created.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as opened:
        yield opened


@pytest_asyncio.fixture(loop_scope="session")
async def test_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Fabrique liée à la base jetable, pour surcharger
    app.db.get_session_factory dans les tests d'API qui déclenchent une
    tâche de fond utilisant sa propre session."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def minio_storage() -> MinioStorage:
    """MinIO réel de compose. Sauté proprement s'il est injoignable."""
    storage = MinioStorage()
    if not storage.is_reachable():
        pytest.skip("MinIO indisponible : lancer `docker compose up -d minio`")
    return storage
