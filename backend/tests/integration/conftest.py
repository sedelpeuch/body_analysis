"""Base de données jetable pour les tests d'intégration.

Nécessite le service db de compose. Le schéma est créé depuis les métadonnées
plutôt que par Alembic : c'est plus rapide, et la conformité de la migration
au modèle est vérifiée séparément par la tâche 4.

L'URL de la base de test n'a volontairement aucun défaut en dur (contrainte
globale « aucun identifiant en dur ») : elle doit venir de l'environnement,
par exemple depuis `backend/.env`. Si elle est absente, les tests
d'intégration sont marqués skip plutôt que d'échouer.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models import Base

TEST_DATABASE_URL = os.environ.get("BA_TEST_DATABASE_URL")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    if not TEST_DATABASE_URL:
        pytest.skip(
            "BA_TEST_DATABASE_URL n'est pas défini : tests d'intégration ignorés"
        )
    created = create_async_engine(TEST_DATABASE_URL)
    async with created.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield created
    await created.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as opened:
        yield opened
