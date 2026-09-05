"""Moteur et fabrique de sessions asynchrones."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)

session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Fournisseur pour Depends() : permet aux tests de substituer une
    fabrique liée à la base jetable plutôt qu'à settings.database_url."""
    return session_factory
