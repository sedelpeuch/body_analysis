"""Tests de l'estimation de dépense énergétique — spec 5.1.

TDEE ≈ apport moyen − pente(kg/jour) × 7700. Les séries synthétiques sont
construites pour que le résultat se calcule à la main.
"""

from datetime import date, timedelta

import pytest

from app.analytics.energy import (
    KCAL_PER_KG,
    MIN_LOGGED_DAYS,
    MIN_WEIGH_INS,
    DailyBmr,
    DailyIntake,
    WeighIn,
    compute_energy_balance,
    estimate_tdee,
    forward_fill_bmr,
)


def test_estimate_tdee_on_hand_computed_linear_series() -> None:
    """30 jours, poids décroissant de pile 0.1 kg/jour, apport constant à
    2000 kcal. Pente = -0.1 kg/jour, donc TDEE = 2000 - (-0.1 * 7700)
    = 2000 + 770 = 2770 kcal/jour."""
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0) for i in range(30)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0 - 0.1 * i)
        for i in range(30)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is True
    assert result.mean_intake_kcal == pytest.approx(2000.0)
    assert result.weight_slope_kg_per_day == pytest.approx(-0.1, abs=1e-9)
    assert result.tdee_kcal == pytest.approx(2770.0, abs=1e-6)
    assert result.reason is None
    assert "7700" in result.uncertainty_note


def test_estimate_tdee_invalid_below_minimum_logged_days() -> None:
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0)
        for i in range(MIN_LOGGED_DAYS - 1)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0 - 0.1 * i)
        for i in range(MIN_WEIGH_INS + 5)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is False
    assert result.tdee_kcal is None
    assert "journalisé" in result.reason or "pesée" in result.reason


def test_estimate_tdee_invalid_below_minimum_weigh_ins() -> None:
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0)
        for i in range(MIN_LOGGED_DAYS + 5)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0)
        for i in range(MIN_WEIGH_INS - 1)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.is_valid is False
    assert result.tdee_kcal is None


def test_estimate_tdee_ignores_null_intake_days_in_mean() -> None:
    """Un jour non journalisé doit sortir de la moyenne, pas y entrer comme
    zéro calorie — sinon la moyenne s'effondre artificiellement."""
    start = date(2026, 1, 1)
    intakes = [
        DailyIntake(day=start + timedelta(days=i), calories=2000.0 if i % 2 == 0 else None)
        for i in range(40)
    ]
    weigh_ins = [
        WeighIn(day=start + timedelta(days=i), weight_kg=80.0) for i in range(MIN_WEIGH_INS + 2)
    ]

    result = estimate_tdee(intakes, weigh_ins)

    assert result.mean_intake_kcal == pytest.approx(2000.0)


def test_forward_fill_bmr_propagates_last_known_value() -> None:
    points = [
        DailyBmr(day=date(2026, 1, 1), bmr_kcal=1600.0),
        DailyBmr(day=date(2026, 1, 2), bmr_kcal=None),
        DailyBmr(day=date(2026, 1, 3), bmr_kcal=1580.0),
    ]

    filled = forward_fill_bmr(points)

    assert filled[date(2026, 1, 1)] == 1600.0
    assert filled[date(2026, 1, 2)] == 1600.0
    assert filled[date(2026, 1, 3)] == 1580.0


def test_forward_fill_bmr_is_none_before_first_known_value() -> None:
    points = [
        DailyBmr(day=date(2026, 1, 1), bmr_kcal=None),
        DailyBmr(day=date(2026, 1, 2), bmr_kcal=1600.0),
    ]

    filled = forward_fill_bmr(points)

    assert filled[date(2026, 1, 1)] is None
    assert filled[date(2026, 1, 2)] == 1600.0


def test_compute_energy_balance_combines_intake_bmr_and_workout_calories() -> None:
    day = date(2026, 1, 1)
    intakes = [DailyIntake(day=day, calories=2200.0)]
    bmr_points = [DailyBmr(day=day, bmr_kcal=1600.0)]
    workout_kcal_by_day = {day: 400.0}

    balance = compute_energy_balance(intakes, bmr_points, workout_kcal_by_day)

    assert len(balance) == 1
    assert balance[0].intake_kcal == 2200.0
    assert balance[0].expenditure_kcal == 2000.0
    assert balance[0].balance_kcal == 200.0


def test_compute_energy_balance_defaults_missing_workout_calories_to_zero() -> None:
    """L'absence de séance un jour donné vaut 0 kcal d'exercice ce jour-là,
    ce n'est pas une mesure manquante — cf. contrainte globale du plan."""
    day = date(2026, 1, 1)
    balance = compute_energy_balance(
        [DailyIntake(day=day, calories=2000.0)], [DailyBmr(day=day, bmr_kcal=1500.0)], {}
    )

    assert balance[0].expenditure_kcal == 1500.0


def test_compute_energy_balance_expenditure_is_none_without_bmr() -> None:
    """Sans BMR connu (avant la première mesure exploitable), la dépense ne
    doit jamais être devinée : elle reste None."""
    day = date(2026, 1, 1)
    balance = compute_energy_balance(
        [DailyIntake(day=day, calories=2000.0)], [DailyBmr(day=day, bmr_kcal=None)], {}
    )

    assert balance[0].expenditure_kcal is None
    assert balance[0].balance_kcal is None
