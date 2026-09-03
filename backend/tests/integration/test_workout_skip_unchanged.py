"""Un ré-import complet ne doit pas retraiter les séances inchangées.

Le CSV Samsung Health exporté par le téléphone contient toujours
l'intégralité de l'historique, jamais un delta. Sans comparaison à
l'update_time déjà en base, chaque ré-import referait le travail coûteux
(lecture des JSON, reconstruction des échantillons) pour des milliers de
séances qui n'ont pas changé depuis le dernier import.
"""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.samsung.pipeline import _ingest_workouts
from app.models import Workout

P = "com.samsung.health.exercise."
FIELDNAMES = [
    f"{P}datauuid",
    f"{P}start_time",
    f"{P}end_time",
    f"{P}time_offset",
    f"{P}exercise_type",
    f"{P}update_time",
    f"{P}duration",
    f"{P}live_data",
    f"{P}location_data",
    f"{P}additional",
    "sensing_status",
    "subset_data",
    "start_latitude",
    "start_longitude",
]

UUID = "aaaaaaaa-1111-2222-3333-444444444444"


def _write_csv(path: Path, update_time: str) -> None:
    import csv

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        handle.write("com.samsung.shealth.exercise,7006003,6\n")
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(
            {
                f"{P}datauuid": UUID,
                f"{P}start_time": "2022-02-05 20:27:00.000",
                f"{P}end_time": "2022-02-05 21:00:00.000",
                f"{P}time_offset": "UTC+0100",
                f"{P}exercise_type": "1002",
                f"{P}update_time": update_time,
                f"{P}duration": "1980000",
                f"{P}live_data": "",
                f"{P}location_data": "",
                f"{P}additional": "",
                "sensing_status": "",
                "subset_data": "",
                "start_latitude": "",
                "start_longitude": "",
            }
        )


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession):
    await session.execute(Workout.__table__.delete())
    await session.commit()
    yield


async def test_second_pass_over_the_same_export_skips_the_unchanged_workout(
    session: AsyncSession, tmp_path: Path
) -> None:
    csv_path = tmp_path / "exercise.csv"
    _write_csv(csv_path, "2022-02-05 21:05:00.000")

    first = await _ingest_workouts(session, csv_path, tmp_path)
    await session.commit()
    second = await _ingest_workouts(session, csv_path, tmp_path)

    assert first["workouts"] == 1
    assert first["workouts_skipped"] == 0
    assert second["workouts"] == 0
    assert second["workouts_skipped"] == 1
    stored = (await session.execute(select(Workout))).scalars().all()
    assert len(stored) == 1


async def test_a_changed_update_time_forces_reprocessing(
    session: AsyncSession, tmp_path: Path
) -> None:
    csv_path = tmp_path / "exercise.csv"
    _write_csv(csv_path, "2022-02-05 21:05:00.000")
    await _ingest_workouts(session, csv_path, tmp_path)
    await session.commit()

    _write_csv(csv_path, "2022-02-06 08:00:00.000")
    second = await _ingest_workouts(session, csv_path, tmp_path)

    assert second["workouts"] == 1
    assert second["workouts_skipped"] == 0
