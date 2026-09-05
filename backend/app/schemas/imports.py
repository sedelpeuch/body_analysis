"""Schémas Pydantic exposés par l'API imports."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models import IngestionStatus


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    source_name: str
    status: IngestionStatus
    started_at: datetime
    finished_at: datetime | None
    counts: dict[str, Any] | None
    error: str | None
