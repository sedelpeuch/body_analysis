"""Client MinIO fin, unique point de contact avec le SDK MinIO.

Toute opération de stockage objet passe par MinioStorage : le reste de
l'application (services, routes) ne connaît jamais le SDK directement, ce
qui rend le stockage mockable dans les tests unitaires. Le bucket est créé
au premier usage s'il n'existe pas encore.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from minio import Minio
from minio.error import S3Error

from app.config import Settings, settings


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str | None


class MinioStorage:
    def __init__(self, config: Settings = settings) -> None:
        self._bucket = config.minio_bucket
        self._client = Minio(
            config.minio_endpoint,
            access_key=config.minio_access_key,
            secret_key=config.minio_secret_key,
            secure=config.minio_secure,
        )
        self._bucket_ready = False

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
        self._bucket_ready = True

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._ensure_bucket()
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get(self, key: str) -> StoredObject | None:
        self._ensure_bucket()
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as error:
            if error.code == "NoSuchKey":
                return None
            raise
        try:
            return StoredObject(
                data=response.read(),
                content_type=response.headers.get("Content-Type"),
            )
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        self._ensure_bucket()
        try:
            self._client.stat_object(self._bucket, key)
        except S3Error as error:
            if error.code == "NoSuchKey":
                return False
            raise
        return True

    def delete(self, key: str) -> None:
        """Idempotent : supprimer une clé absente ne lève pas, comme S3."""
        self._ensure_bucket()
        self._client.remove_object(self._bucket, key)

    def delete_prefix(self, prefix: str) -> None:
        self._ensure_bucket()
        for obj in self._client.list_objects(
            self._bucket,
            prefix=prefix,
            recursive=True,
        ):
            self._client.remove_object(self._bucket, obj.object_name)

    def is_reachable(self) -> bool:
        try:
            self._client.bucket_exists(self._bucket)
        except Exception:
            return False
        return True


_storage: MinioStorage | None = None


def get_storage() -> MinioStorage:
    """Fournisseur singleton pour Depends(). Surchargé dans les tests par
    app.dependency_overrides[get_storage]."""
    global _storage
    if _storage is None:
        _storage = MinioStorage()
    return _storage
