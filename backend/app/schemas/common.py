"""Schémas Pydantic génériques, réutilisés par toutes les familles."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Pagination par numéro de page."""

    items: list[T]
    page: int
    page_size: int
    total: int


class CursorPage(BaseModel, Generic[T]):
    """Pagination par curseur opaque."""

    items: list[T]
    next_cursor: str | None = None
