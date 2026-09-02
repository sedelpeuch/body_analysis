"""Tests d'intégration du service photo : base réelle + MinIO réel."""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError, UnsupportedMediaTypeError
from app.models import Photo
from app.services.photo_image import DERIVATIVE_SIZES
from app.services.photos import delete_photo, get_photo_image, list_photos, upload_photo
from app.storage.minio import MinioStorage


def _jpeg(color: str = "red", size: tuple[int, int] = (200, 100)) -> bytes:
    import io

    from PIL import Image

    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
async def _clean(session: AsyncSession, minio_storage: MinioStorage):
    minio_storage.delete_prefix("photos/")
    minio_storage.delete_prefix("derived/")
    await session.execute(Photo.__table__.delete())
    await session.commit()
    yield
    minio_storage.delete_prefix("photos/")
    minio_storage.delete_prefix("derived/")
    await session.execute(Photo.__table__.delete())
    await session.commit()


async def test_upload_creates_a_photo_with_derived_metadata(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    assert photo.id is not None
    assert photo.tag == "face"
    assert photo.taken_on == date(2026, 8, 31)
    assert photo.content_type == "image/jpeg"
    assert photo.width == 200
    assert photo.height == 100
    assert minio_storage.exists(photo.object_key) is True


async def test_upload_rejects_an_unknown_tag(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await upload_photo(
            session,
            minio_storage,
            taken_on=date(2026, 8, 31),
            tag="genou",
            raw_bytes=_jpeg(),
        )


async def test_upload_rejects_content_that_is_not_an_image(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        await upload_photo(
            session,
            minio_storage,
            taken_on=date(2026, 8, 31),
            tag="face",
            raw_bytes=b"pas une image",
        )


async def test_second_upload_for_same_date_and_tag_replaces_the_first(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    first = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("red")
    )
    old_key = first.object_key

    replaced = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("blue")
    )

    assert replaced.id == first.id
    photos = await list_photos(session, tag="face")
    assert len(photos) == 1
    assert minio_storage.exists(old_key) is False
    assert minio_storage.exists(replaced.object_key) is True


async def test_uploading_the_same_bytes_twice_is_a_no_op(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    data = _jpeg()
    first = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )
    second = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )

    assert first.id == second.id
    assert first.sha256 == second.sha256


async def test_upload_rejects_a_sha256_already_used_by_another_photo(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    data = _jpeg()
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=data
    )

    with pytest.raises(ConflictError):
        await upload_photo(
            session, minio_storage, taken_on=date(2026, 9, 1), tag="dos", raw_bytes=data
        )


async def test_list_photos_filters_by_tag(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg("red")
    )
    await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="dos", raw_bytes=_jpeg("blue")
    )

    assert len(await list_photos(session)) == 2
    assert len(await list_photos(session, tag="face")) == 1


async def test_delete_photo_removes_row_and_object(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    await delete_photo(session, minio_storage, photo_id=photo.id)

    assert (await session.execute(select(Photo))).scalars().all() == []
    assert minio_storage.exists(photo.object_key) is False


async def test_delete_unknown_photo_raises_not_found(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    with pytest.raises(NotFoundError):
        await delete_photo(session, minio_storage, photo_id=999999)


async def test_get_photo_image_generates_and_caches_the_derivative(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session,
        minio_storage,
        taken_on=date(2026, 8, 31),
        tag="face",
        raw_bytes=_jpeg(size=(2000, 1000)),
    )
    cache_key = f"derived/thumb/{photo.sha256}.jpg"
    assert minio_storage.exists(cache_key) is False

    data, content_type = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="thumb", blur=False
    )

    assert content_type == "image/jpeg"
    assert minio_storage.exists(cache_key) is True

    import io

    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        assert max(image.size) <= DERIVATIVE_SIZES["thumb"]


async def test_get_photo_image_blur_is_never_cached(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    import io

    from PIL import Image, ImageColor

    image = Image.new("RGB", (200, 200), "white")
    for x in range(0, 200, 20):
        for y in range(0, 200, 20):
            color = "black" if (x // 20 + y // 20) % 2 == 0 else "gray"
            for dx in range(10):
                for dy in range(10):
                    image.putpixel((x + dx, y + dy), ImageColor.getrgb(color))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")

    photo = await upload_photo(
        session,
        minio_storage,
        taken_on=date(2026, 8, 31),
        tag="face",
        raw_bytes=buffer.getvalue(),
    )

    sharp, _ = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="medium", blur=False
    )
    blurred, _ = await get_photo_image(
        session, minio_storage, photo_id=photo.id, size="medium", blur=True
    )

    assert sharp != blurred
    assert minio_storage.exists(f"derived/medium/{photo.sha256}.jpg") is True


async def test_get_photo_image_rejects_an_unknown_size(
    session: AsyncSession, minio_storage: MinioStorage
) -> None:
    photo = await upload_photo(
        session, minio_storage, taken_on=date(2026, 8, 31), tag="face", raw_bytes=_jpeg()
    )

    with pytest.raises(Exception):
        await get_photo_image(
            session, minio_storage, photo_id=photo.id, size="xxl", blur=False
        )
