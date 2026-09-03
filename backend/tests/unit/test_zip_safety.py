"""Tests des garde-fous d'extraction ZIP : zip-slip et bombe de décompression.

L'archive d'import est une entrée non fiable ; ces tests construisent des
archives réellement malveillantes plutôt que de simuler leur détection.
"""

import zipfile
from pathlib import Path

import pytest

from app.errors import ValidationError
from app.ingestion.zip_safety import safe_extract


def _make_zip(path: Path, entries: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


def test_extracts_a_well_formed_archive(tmp_path: Path) -> None:
    zip_path = _make_zip(
        tmp_path / "export.zip",
        {
            "com.samsung.health.weight.csv": b"start_time,weight\n",
            "com.samsung.shealth.exercise/1/a.json": b"{}",
        },
    )
    destination = tmp_path / "extracted"

    safe_extract(zip_path, destination)

    assert (destination / "com.samsung.health.weight.csv").read_bytes() == (
        b"start_time,weight\n"
    )
    assert (destination / "com.samsung.shealth.exercise" / "1" / "a.json").exists()


def test_rejects_an_entry_that_escapes_the_destination_with_dotdot(
    tmp_path: Path,
) -> None:
    zip_path = _make_zip(tmp_path / "evil.zip", {"../../etc/evil.txt": b"charge utile"})
    destination = tmp_path / "extracted"
    destination.mkdir()

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination)

    assert not (tmp_path.parent / "etc" / "evil.txt").exists()
    assert list(destination.iterdir()) == []


def test_rejects_an_entry_with_an_absolute_path(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path / "evil.zip", {"/etc/evil.txt": b"charge utile"})
    destination = tmp_path / "extracted"
    destination.mkdir()

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination)

    assert not Path("/etc/evil.txt").exists()


def test_rejects_an_archive_with_too_many_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "many.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for i in range(10):
            archive.writestr(f"file-{i}.txt", b"x")
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_entries=5)


def test_rejects_a_decompression_bomb_by_streamed_size(tmp_path: Path) -> None:
    """Une bombe classique : peu d'octets compressés, énormément une fois
    décompressés. La vérification porte sur les octets réellement produits
    pendant la décompression, pas seulement sur la taille déclarée dans les
    métadonnées de l'archive, qu'un attaquant contrôle entièrement."""
    zip_path = tmp_path / "bomb.zip"
    huge_but_compressible = b"\x00" * (5 * 1024 * 1024)  # 5 Mo de zéros
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.bin", huge_but_compressible)
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_total_bytes=1024)


def test_does_not_leave_a_completed_forbidden_file_after_bomb_rejection(
    tmp_path: Path,
) -> None:
    zip_path = tmp_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.bin", b"\x00" * (2 * 1024 * 1024))
    destination = tmp_path / "extracted"

    with pytest.raises(ValidationError):
        safe_extract(zip_path, destination, max_total_bytes=1024)

    written = destination / "bomb.bin"
    if written.exists():
        assert written.stat().st_size <= 1024 + (1024 * 1024)  # au plus un bloc de plus
