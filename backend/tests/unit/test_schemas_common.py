"""Tests des schémas Pydantic génériques partagés."""

from app.schemas.common import CursorPage, Page


def test_page_serializes_with_total() -> None:
    page = Page[int](items=[1, 2, 3], page=1, page_size=50, total=120)

    assert page.model_dump() == {
        "items": [1, 2, 3],
        "page": 1,
        "page_size": 50,
        "total": 120,
    }


def test_cursor_page_defaults_next_cursor_to_none() -> None:
    page = CursorPage[int](items=[1, 2, 3])

    assert page.next_cursor is None
