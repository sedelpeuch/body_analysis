"""Activité et pas quotidiens.

day est une date calendaire : ni activity.day_summary ni step_daily_trend
n'ont de colonne time_offset, day_time est déjà une minuit locale.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class DailyActivity(Base, TimestampMixin):
    __tablename__ = "daily_activity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    step_count: Mapped[int | None] = mapped_column(Integer)
    active_time_ms: Mapped[int | None] = mapped_column(Integer)
    calorie: Mapped[float | None] = mapped_column(Double)
    distance_m: Mapped[float | None] = mapped_column(Double)
    floor_count: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer)
    exercise_time_ms: Mapped[int | None] = mapped_column(Integer)
    run_time_ms: Mapped[int | None] = mapped_column(Integer)
    walk_time_ms: Mapped[int | None] = mapped_column(Integer)
    longest_active_time_ms: Mapped[int | None] = mapped_column(Integer)
    move_hourly_count: Mapped[int | None] = mapped_column(Integer)


class StepDailyTrend(Base, TimestampMixin):
    __tablename__ = "step_daily_trend"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    count: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[float | None] = mapped_column(Double)
    calorie: Mapped[float | None] = mapped_column(Double)
    speed: Mapped[float | None] = mapped_column(Double)
    source_type: Mapped[int | None] = mapped_column(SmallInteger)
