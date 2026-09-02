"""Service photo : upload, dérivés à la demande, suppression.

Fait le pont entre app.storage.minio (octets) et le modèle Photo (métadonnées
en base). Aucune route HTTP ne parle directement à MinIO ou à Pillow.
"""

from __future__ import annotations

from datetime import date

from PIL import UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    ConflictError,
    NotFoundError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.models import Photo
from app.services.photo_image import (
    DERIVATIVE_SIZES,
    make_derivative,
    normalize_orientation,
    sha256_of,
    sniff_content_type,
)
from app.storage.minio import MinioStorage

ALLOWED_TAGS = frozenset({"face", "profil", "dos", "bras", "epaule"})


def _object_key(taken_on: date, tag: str, sha256: str) -> str:
    return f"photos/{taken_on.isoformat()}/{tag}-{sha256[:8]}.jpg"


def _derivative_key(size: str, sha256: str) -> str:
    return f"derived/{size}/{sha256}.jpg"


async def upload_photo(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    taken_on: date,
    tag: str,
    raw_bytes: bytes,
) -> Photo:
    """Enregistre une photo. Un envoi pour un (date, tag) déjà connu
    remplace l'existant ; un envoi identique octet pour octet est un no-op.
    """
    if tag not in ALLOWED_TAGS:
        raise UnsupportedMediaTypeError(
            f"Tag inconnu : {tag}", allowed=sorted(ALLOWED_TAGS)
        )
    if sniff_content_type(raw_bytes) is None:
        raise UnsupportedMediaTypeError(
            "Le contenu envoyé n'est ni un JPEG ni un PNG reconnaissable."
        )

    try:
        normalized = normalize_orientation(raw_bytes)
    except UnidentifiedImageError as error:
        raise UnsupportedMediaTypeError("Image illisible ou corrompue.") from error

    checksum = sha256_of(raw_bytes)
    key = _object_key(taken_on, tag, checksum)

    existing = (
        await session.execute(
            select(Photo).where(Photo.taken_on == taken_on, Photo.tag == tag)
        )
    ).scalar_one_or_none()

    if existing is not None and existing.sha256 == checksum:
        return existing

    old_key = existing.object_key if existing is not None else None
    old_sha = existing.sha256 if existing is not None else None

    storage.put(key, normalized.data, normalized.content_type)

    if existing is not None:
        existing.object_key = key
        existing.sha256 = checksum
        existing.width = normalized.width
        existing.height = normalized.height
        existing.byte_size = len(normalized.data)
        existing.content_type = normalized.content_type
        photo = existing
    else:
        photo = Photo(
            taken_on=taken_on,
            tag=tag,
            object_key=key,
            sha256=checksum,
            width=normalized.width,
            height=normalized.height,
            byte_size=len(normalized.data),
            content_type=normalized.content_type,
        )
        session.add(photo)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        storage.delete(key)
        raise ConflictError(
            "Cette image (sha256 identique) est déjà associée à une autre photo."
        ) from error

    await session.refresh(photo)

    if old_key is not None and old_key != key:
        storage.delete(old_key)
        for size in DERIVATIVE_SIZES:
            storage.delete(_derivative_key(size, old_sha))

    return photo


async def list_photos(session: AsyncSession, *, tag: str | None = None) -> list[Photo]:
    query = select(Photo).order_by(Photo.taken_on.desc(), Photo.tag)
    if tag is not None:
        query = query.where(Photo.tag == tag)
    return list((await session.execute(query)).scalars().all())


async def delete_photo(
    session: AsyncSession, storage: MinioStorage, *, photo_id: int
) -> None:
    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise NotFoundError(f"Photo {photo_id} introuvable")

    storage.delete(photo.object_key)
    for size in DERIVATIVE_SIZES:
        storage.delete(_derivative_key(size, photo.sha256))

    await session.delete(photo)
    await session.commit()


async def get_photo_image(
    session: AsyncSession,
    storage: MinioStorage,
    *,
    photo_id: int,
    size: str,
    blur: bool,
) -> tuple[bytes, str]:
    if size not in DERIVATIVE_SIZES:
        raise ValidationError(
            f"Taille inconnue : {size}", allowed=sorted(DERIVATIVE_SIZES)
        )

    photo = await session.get(Photo, photo_id)
    if photo is None:
        raise NotFoundError(f"Photo {photo_id} introuvable")

    cache_key = _derivative_key(size, photo.sha256)
    if not blur:
        cached = storage.get(cache_key)
        if cached is not None:
            return cached.data, "image/jpeg"

    original = storage.get(photo.object_key)
    if original is None:
        raise NotFoundError(
            f"Fichier de la photo {photo_id} introuvable dans le stockage"
        )

    derivative = make_derivative(
        original.data, max_dimension=DERIVATIVE_SIZES[size], blur=blur
    )
    if not blur:
        storage.put(cache_key, derivative, "image/jpeg")
    return derivative, "image/jpeg"
