"""Libellés lisibles pour les codes bruts de l'export nutrition."""

from __future__ import annotations

from types import MappingProxyType

MEAL_TYPE_LABELS = MappingProxyType(
    {
        100001: "Petit-déjeuner",
        100002: "Déjeuner",
        100003: "Dîner",
        100004: "Collation",
        100005: "Collation matin",
        100006: "Collation soir",
    }
)

UNIT_LABELS = MappingProxyType(
    {
        120001: "Grammes",
        120002: "Millilitres",
        120004: "Portion",
        120005: "Unité",
        -1: "Non spécifié",
    }
)


def meal_type_label(code: int | None) -> str:
    if code is None:
        return "Non renseigné"
    return MEAL_TYPE_LABELS.get(code, "Autre")


def unit_label(code: int | None) -> str:
    if code is None:
        return "Non renseigné"
    return UNIT_LABELS.get(code, "Autre")
