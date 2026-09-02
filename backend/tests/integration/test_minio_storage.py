"""Tests d'intégration du client MinIO contre le service réel de compose."""

import pytest

from app.storage.minio import MinioStorage

TEST_PREFIX = "tests/minio-storage"


@pytest.fixture(autouse=True)
def _clean(minio_storage: MinioStorage):
    minio_storage.delete_prefix(TEST_PREFIX)
    yield
    minio_storage.delete_prefix(TEST_PREFIX)


def test_put_then_get_roundtrips_bytes_and_content_type(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/roundtrip.jpg"

    minio_storage.put(key, b"donnees-binaires", "image/jpeg")
    stored = minio_storage.get(key)

    assert stored is not None
    assert stored.data == b"donnees-binaires"
    assert stored.content_type == "image/jpeg"


def test_get_missing_key_returns_none(minio_storage: MinioStorage) -> None:
    assert minio_storage.get(f"{TEST_PREFIX}/absent.jpg") is None


def test_exists_reflects_presence(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/exists.jpg"
    assert minio_storage.exists(key) is False

    minio_storage.put(key, b"x", "image/jpeg")

    assert minio_storage.exists(key) is True


def test_delete_removes_the_object(minio_storage: MinioStorage) -> None:
    key = f"{TEST_PREFIX}/to-delete.jpg"
    minio_storage.put(key, b"x", "image/jpeg")

    minio_storage.delete(key)

    assert minio_storage.exists(key) is False


def test_delete_missing_key_does_not_raise(minio_storage: MinioStorage) -> None:
    minio_storage.delete(f"{TEST_PREFIX}/jamais-cree.jpg")


def test_delete_prefix_removes_every_matching_object(minio_storage: MinioStorage) -> None:
    minio_storage.put(f"{TEST_PREFIX}/derived/thumb/a.jpg", b"1", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/derived/thumb/b.jpg", b"2", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/derived/full/a.jpg", b"3", "image/jpeg")

    minio_storage.delete_prefix(f"{TEST_PREFIX}/derived/thumb/")

    assert minio_storage.exists(f"{TEST_PREFIX}/derived/thumb/a.jpg") is False
    assert minio_storage.exists(f"{TEST_PREFIX}/derived/thumb/b.jpg") is False
    assert minio_storage.exists(f"{TEST_PREFIX}/derived/full/a.jpg") is True


def test_is_reachable_is_true_against_the_real_service(minio_storage: MinioStorage) -> None:
    assert minio_storage.is_reachable() is True


def test_bucket_is_created_on_first_use_if_absent(minio_storage: MinioStorage) -> None:
    """Le bucket configuré existe déjà dans un compose qui tourne depuis un
    moment ; ce test vérifie seulement que _ensure_bucket ne lève pas quand
    on l'appelle plusieurs fois de suite."""
    minio_storage.put(f"{TEST_PREFIX}/bucket-check.jpg", b"x", "image/jpeg")
    minio_storage.put(f"{TEST_PREFIX}/bucket-check-2.jpg", b"y", "image/jpeg")

    assert minio_storage.exists(f"{TEST_PREFIX}/bucket-check.jpg") is True
