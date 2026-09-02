"""Endpoints photo : liste, envoi, suppression, service de l'image."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import PayloadTooLargeError, ValidationError
from app.schemas.photos import PhotoOut
from app.services import photos as photos_service
from app.services.photo_image import DERIVATIVE_SIZES
from app.storage.minio import MinioStorage, get_storage

router = APIRouter(prefix="/api/photos", tags=["photos"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("", response_model=list[PhotoOut])
async def list_photos(
    tag: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[PhotoOut]:
    photos = await photos_service.list_photos(session, tag=tag)
    return [PhotoOut.model_validate(photo) for photo in photos]


@router.post("", response_model=PhotoOut, status_code=201)
async def upload_photo(
    taken_on: Annotated[date, Form()],
    tag: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> PhotoOut:
    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError(
            f"Photo trop volumineuse (maximum {MAX_UPLOAD_BYTES} octets)."
        )
    photo = await photos_service.upload_photo(
        session, storage, taken_on=taken_on, tag=tag, raw_bytes=raw_bytes
    )
    return PhotoOut.model_validate(photo)


@router.delete("/{photo_id}", status_code=204)
async def delete_photo(
    photo_id: int,
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> Response:
    await photos_service.delete_photo(session, storage, photo_id=photo_id)
    return Response(status_code=204)


@router.get("/{photo_id}/image")
async def get_photo_image(
    photo_id: int,
    size: str = Query("medium"),
    blur: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    storage: MinioStorage = Depends(get_storage),
) -> Response:
    if size not in DERIVATIVE_SIZES:
        raise ValidationError(
            f"Taille inconnue : {size}", allowed=sorted(DERIVATIVE_SIZES)
        )
    data, content_type = await photos_service.get_photo_image(
        session, storage, photo_id=photo_id, size=size, blur=blur
    )
    return Response(content=data, media_type=content_type)
