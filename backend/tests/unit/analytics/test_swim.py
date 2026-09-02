"""Tests du SWOLF agrégé par type de nage — spec section 5."""

import pytest

from app.analytics.swim import SwimLengthInput, compute_swolf


def test_compute_swolf_groups_by_stroke_type() -> None:
    lengths = [
        SwimLengthInput(idx=0, duration_ms=30000, stroke_count=18, stroke_type="Crawl"),
        SwimLengthInput(idx=1, duration_ms=32000, stroke_count=20, stroke_type="Crawl"),
        SwimLengthInput(idx=2, duration_ms=40000, stroke_count=14, stroke_type="Brasse"),
    ]

    result = {r.stroke_type: r for r in compute_swolf(lengths)}

    assert result["Crawl"].length_count == 2
    assert result["Crawl"].mean_swolf == pytest.approx(50.0)
    assert result["Crawl"].mean_duration_s == pytest.approx(31.0)

    assert result["Brasse"].length_count == 1
    assert result["Brasse"].mean_swolf == pytest.approx(54.0)


def test_compute_swolf_skips_lengths_missing_duration_or_strokes() -> None:
    lengths = [
        SwimLengthInput(idx=0, duration_ms=30000, stroke_count=None, stroke_type="Crawl"),
        SwimLengthInput(idx=1, duration_ms=None, stroke_count=20, stroke_type="Crawl"),
        SwimLengthInput(idx=2, duration_ms=30000, stroke_count=18, stroke_type="Crawl"),
    ]

    result = {r.stroke_type: r for r in compute_swolf(lengths)}

    assert result["Crawl"].length_count == 1
    assert result["Crawl"].mean_swolf == pytest.approx(48.0)


def test_compute_swolf_labels_missing_stroke_type_explicitly() -> None:
    lengths = [SwimLengthInput(idx=0, duration_ms=30000, stroke_count=18, stroke_type=None)]

    result = compute_swolf(lengths)

    assert result[0].stroke_type == "Inconnu"


def test_compute_swolf_on_empty_lengths_returns_empty_list() -> None:
    assert compute_swolf([]) == []
