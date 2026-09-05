"""Signaux continus ou nocturnes dont l'agrégat vit déjà dans la ligne CSV.

Seul hrv_reading dérive ses valeurs d'un fichier JSON annexe (avg_sdnn,
avg_rmssd) : la ligne CSV de com.samsung.health.hrv ne porte aucune mesure,
seulement une référence de fichier.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Double, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class HrvReading(Base, TimestampMixin):
    __tablename__ = "hrv_reading"

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
    avg_sdnn: Mapped[float | None] = mapped_column(Double)
    avg_rmssd: Mapped[float | None] = mapped_column(Double)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class HeartRateReading(Base, TimestampMixin):
    __tablename__ = "heart_rate_reading"

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
    mean_heart_rate: Mapped[float | None] = mapped_column(Double)
    min_heart_rate: Mapped[float | None] = mapped_column(Double)
    max_heart_rate: Mapped[float | None] = mapped_column(Double)
    heart_beat_count: Mapped[int | None] = mapped_column(Integer)
    tag_id: Mapped[int | None] = mapped_column(Integer)


class StressReading(Base, TimestampMixin):
    __tablename__ = "stress_reading"

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
    score: Mapped[float | None] = mapped_column(Double)
    min_score: Mapped[float | None] = mapped_column(Double)
    max_score: Mapped[float | None] = mapped_column(Double)
    tag_id: Mapped[int | None] = mapped_column(Integer)


class RespiratoryRateReading(Base, TimestampMixin):
    __tablename__ = "respiratory_rate_reading"

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
    average: Mapped[float | None] = mapped_column(Double)
    lower_limit: Mapped[float | None] = mapped_column(Double)
    upper_limit: Mapped[float | None] = mapped_column(Double)


class SkinTemperatureReading(Base, TimestampMixin):
    __tablename__ = "skin_temperature_reading"

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
    temperature: Mapped[float | None] = mapped_column(Double)
    min_temperature: Mapped[float | None] = mapped_column(Double)
    max_temperature: Mapped[float | None] = mapped_column(Double)
    baseline: Mapped[float | None] = mapped_column(Double)


class OxygenSaturationReading(Base, TimestampMixin):
    __tablename__ = "oxygen_saturation_reading"

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
    spo2: Mapped[float | None] = mapped_column(Double)
    heart_rate: Mapped[float | None] = mapped_column(Double)
    tag_id: Mapped[int | None] = mapped_column(SmallInteger)
