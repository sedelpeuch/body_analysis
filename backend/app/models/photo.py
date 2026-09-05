"""Photos de suivi. La logique de stockage arrive au plan 3."""

from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Date, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Photo(Base, TimestampMixin):
    """Une photo par tag et par date.

    Reproduit la sémantique de l'arborescence actuelle ({date}/{tag}.jpg) et
    simplifie le front : un nouvel envoi remplace.
    """

    __tablename__ = "photo"
    __table_args__ = (UniqueConstraint("taken_on", "tag", name="uq_photo_date_tag"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    taken_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tag: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    byte_size: Mapped[int | None] = mapped_column(BigInteger)
    content_type: Mapped[str | None] = mapped_column(Text)
