"""Dépendances communes aux routers de lecture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


@dataclass(frozen=True, slots=True)
class DateRange:
    start: date | None
    end: date | None


def date_range(
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = Query(default=None),
) -> DateRange:
    return DateRange(start=from_, end=to)


DbSession = Annotated[AsyncSession, Depends(get_session)]
DateRangeDep = Annotated[DateRange, Depends(date_range)]
