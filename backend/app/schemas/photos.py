"""Schémas Pydantic exposés par l'API photos."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    taken_on: date
    tag: str
    width: int | None
    height: int | None
    byte_size: int | None
    content_type: str | None
    created_at: datetime
