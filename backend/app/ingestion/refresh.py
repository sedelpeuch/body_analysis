"""Rafraîchissement des vues matérialisées quotidiennes."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DAILY_VIEWS = (
    "mv_daily_body",
    "mv_daily_nutrition",
    "mv_daily_nutrition_detail",
    "mv_daily_sleep",
    "mv_daily_vitals",
    "mv_daily_training",
)


async def refresh_materialized_views(
    session: AsyncSession,
    *,
    concurrently: bool = True,
) -> None:
    """Rafraîchit les trois vues quotidiennes.

    concurrently=False est nécessaire au premier peuplement : PostgreSQL
    refuse un rafraîchissement concurrent sur une vue jamais peuplée.
    """
    mode = "CONCURRENTLY " if concurrently else ""
    for view in DAILY_VIEWS:
        await session.execute(text(f"REFRESH MATERIALIZED VIEW {mode}{view}"))
    await session.commit()
