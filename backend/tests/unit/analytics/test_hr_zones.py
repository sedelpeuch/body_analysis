"""Tests des zones cardiaques calculées — spec 4.4 et 6.

Modèle à cinq zones par pourcentage de FC max, standard d'entraînement.
max_hr=180 donne des bornes rondes : 108, 126, 144, 162.
"""

from datetime import UTC, datetime, timedelta

from app.analytics.hr_zones import compute_hr_zone_times, hr_zone_boundaries

T0 = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)


def test_hr_zone_boundaries_for_max_180() -> None:
    boundaries = hr_zone_boundaries(180)

    assert [b.lower_bpm for b in boundaries] == [0, 108, 126, 144, 162]
    assert [b.upper_bpm for b in boundaries] == [108, 126, 144, 162, None]
    assert boundaries[0].label == "Récupération"
    assert boundaries[-1].label == "Maximal"


def test_compute_hr_zone_times_attributes_interval_to_starting_zone() -> None:
    """Quatre échantillons espacés de 60 s : 100 (zone 1), 115 (zone 2),
    135 (zone 3), 155 (zone 4). Chaque intervalle de 60 s est attribué à la
    zone de l'échantillon de départ ; le dernier échantillon ne clôt aucun
    intervalle."""
    samples = [
        (T0, 100),
        (T0 + timedelta(seconds=60), 115),
        (T0 + timedelta(seconds=120), 135),
        (T0 + timedelta(seconds=180), 155),
    ]

    zones = compute_hr_zone_times(samples, max_hr=180)
    seconds_by_zone = {z.zone: z.seconds for z in zones}

    assert seconds_by_zone[1] == 60.0
    assert seconds_by_zone[2] == 60.0
    assert seconds_by_zone[3] == 60.0
    assert seconds_by_zone[4] == 0.0
    assert seconds_by_zone[5] == 0.0


def test_compute_hr_zone_times_skips_samples_without_heart_rate() -> None:
    samples = [(T0, None), (T0 + timedelta(seconds=60), None)]

    zones = compute_hr_zone_times(samples, max_hr=180)

    assert all(z.seconds == 0.0 for z in zones)


def test_compute_hr_zone_times_returns_all_five_zones_even_when_unused() -> None:
    zones = compute_hr_zone_times([], max_hr=180)

    assert [z.zone for z in zones] == [1, 2, 3, 4, 5]
