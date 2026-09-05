"""Sommeil : résumé de nuit et détail par phase.

sleep_stage n'a pas de clé étrangère stricte vers sleep_session : 7
segments réels référencent une nuit absente de l'export sleep. sleep_
source_uuid reste un texte indexé, non contraint.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SleepSession(Base, TimestampMixin):
    __tablename__ = "sleep_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_wake_up_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    efficiency: Mapped[float | None] = mapped_column(Double)
    efficiency_with_latency: Mapped[float | None] = mapped_column(Double)
    physical_recovery: Mapped[int | None] = mapped_column(Integer)
    mental_recovery: Mapped[int | None] = mapped_column(Integer)
    deep_score: Mapped[int | None] = mapped_column(Integer)
    rem_score: Mapped[int | None] = mapped_column(Integer)
    wake_score: Mapped[int | None] = mapped_column(Integer)
    nap_score: Mapped[int | None] = mapped_column(Integer)
    latency_score: Mapped[int | None] = mapped_column(Integer)
    sleep_latency: Mapped[int | None] = mapped_column(Integer)
    total_rem_duration: Mapped[int | None] = mapped_column(Integer)
    total_light_duration: Mapped[int | None] = mapped_column(Integer)
    sleep_duration: Mapped[int | None] = mapped_column(Integer)
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    # Code brut Samsung, pas une valeur booléenne fiable : l'export porte
    # 0, -1 et vide, jamais 1/0 propre.
    has_sleep_data: Mapped[int | None] = mapped_column(SmallInteger)
    sleep_type: Mapped[int | None] = mapped_column(SmallInteger)


class SleepStage(Base, TimestampMixin):
    __tablename__ = "sleep_stage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_uuid: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
    )
    sleep_source_uuid: Mapped[str | None] = mapped_column(Text, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stage: Mapped[int | None] = mapped_column(Integer)
