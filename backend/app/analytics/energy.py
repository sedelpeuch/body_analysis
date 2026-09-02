"""Dépense énergétique estimée et bilan quotidien — spec section 5.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence

KCAL_PER_KG = 7700
MIN_LOGGED_DAYS = 21
MIN_WEIGH_INS = 10
UNCERTAINTY_NOTE = (
    "Estimation approximative : le facteur 7700 kcal/kg est une simplification, "
    "et les variations d'hydratation dominent le signal sur les fenêtres courtes."
)


@dataclass(frozen=True, slots=True)
class DailyIntake:
    day: date
    calories: float | None


@dataclass(frozen=True, slots=True)
class WeighIn:
    day: date
    weight_kg: float | None


@dataclass(frozen=True, slots=True)
class TdeeEstimate:
    tdee_kcal: float | None
    mean_intake_kcal: float | None
    weight_slope_kg_per_day: float | None
    is_valid: bool
    reason: str | None
    uncertainty_note: str


def _linear_regression_slope(points: Sequence[tuple[date, float]]) -> float:
    xs = [point[0].toordinal() for point in points]
    ys = [point[1] for point in points]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    return numerator / denominator if denominator else 0.0


def estimate_tdee(
    intakes: Sequence[DailyIntake], weigh_ins: Sequence[WeighIn]
) -> TdeeEstimate:
    logged = [entry for entry in intakes if entry.calories is not None]
    weighed = [weigh_in for weigh_in in weigh_ins if weigh_in.weight_kg is not None]

    if len(intakes) < MIN_LOGGED_DAYS or len(weighed) < MIN_WEIGH_INS:
        reason = (
            f"fenêtre insuffisante : {len(intakes)} jours journalisés "
            f"(minimum {MIN_LOGGED_DAYS}) et {len(weighed)} pesées "
            f"(minimum {MIN_WEIGH_INS})"
        )
        return TdeeEstimate(
            tdee_kcal=None,
            mean_intake_kcal=None,
            weight_slope_kg_per_day=None,
            is_valid=False,
            reason=reason,
            uncertainty_note=UNCERTAINTY_NOTE,
        )

    mean_intake = sum(entry.calories for entry in logged) / len(logged)
    slope = _linear_regression_slope(
        [(weigh_in.day, weigh_in.weight_kg) for weigh_in in weighed]
    )
    tdee = mean_intake - slope * KCAL_PER_KG
    return TdeeEstimate(
        tdee_kcal=tdee,
        mean_intake_kcal=mean_intake,
        weight_slope_kg_per_day=slope,
        is_valid=True,
        reason=None,
        uncertainty_note=UNCERTAINTY_NOTE,
    )


@dataclass(frozen=True, slots=True)
class DailyBmr:
    day: date
    bmr_kcal: float | None


def forward_fill_bmr(points: Sequence[DailyBmr]) -> dict[date, float | None]:
    ordered = sorted(points, key=lambda point: point.day)
    filled: dict[date, float | None] = {}
    last_known: float | None = None
    for point in ordered:
        if point.bmr_kcal is not None:
            last_known = point.bmr_kcal
        filled[point.day] = last_known
    return filled


@dataclass(frozen=True, slots=True)
class EnergyBalanceDay:
    day: date
    intake_kcal: float | None
    expenditure_kcal: float | None
    balance_kcal: float | None


def compute_energy_balance(
    intakes: Sequence[DailyIntake],
    bmr_points: Sequence[DailyBmr],
    workout_kcal_by_day: Mapping[date, float],
) -> list[EnergyBalanceDay]:
    bmr_by_day = forward_fill_bmr(bmr_points)
    result: list[EnergyBalanceDay] = []
    for intake in intakes:
        bmr = bmr_by_day.get(intake.day)
        expenditure = None
        if bmr is not None:
            expenditure = bmr + workout_kcal_by_day.get(intake.day, 0.0)
        balance = None
        if intake.calories is not None and expenditure is not None:
            balance = intake.calories - expenditure
        result.append(
            EnergyBalanceDay(
                day=intake.day,
                intake_kcal=intake.calories,
                expenditure_kcal=expenditure,
                balance_kcal=balance,
            )
        )
    return result
