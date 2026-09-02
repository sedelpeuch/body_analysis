"""Tests du traitement d'image pur : aucune base, aucun MinIO."""

import io

import pytest
from PIL import Image, ImageColor

from app.services.photo_image import (
    DERIVATIVE_SIZES,
    make_derivative,
    normalize_orientation,
    sha256_of,
    sniff_content_type,
)


def _jpeg_bytes(size: tuple[int, int], *, orientation: int | None = None) -> bytes:
    image = Image.new("RGB", size, "red")
    buffer = io.BytesIO()
    if orientation is not None:
        exif = image.getexif()
        exif[0x0112] = orientation
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size, "blue")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_sniff_content_type_recognizes_jpeg() -> None:
    assert sniff_content_type(_jpeg_bytes((10, 10))) == "image/jpeg"


def test_sniff_content_type_recognizes_png() -> None:
    assert sniff_content_type(_png_bytes((10, 10))) == "image/png"


def test_sniff_content_type_rejects_anything_else() -> None:
    assert sniff_content_type(b"pas une image, juste du texte") is None


def test_sniff_content_type_ignores_a_forged_extension_or_header() -> None:
    """Ne fait jamais confiance à ce qui accompagne les octets, seulement
    aux octets eux-mêmes."""
    fake_jpeg_named_file_content = b"<html>ceci n'est pas une image</html>"
    assert sniff_content_type(fake_jpeg_named_file_content) is None


def test_sha256_of_is_deterministic() -> None:
    data = b"same bytes"
    assert sha256_of(data) == sha256_of(data)
    assert sha256_of(data) != sha256_of(b"different bytes")


def test_normalize_orientation_does_not_rotate_a_true_landscape_photo() -> None:
    """Verrou de non-régression du bug corrigé : l'ancienne heuristique
    tournait toute image dont la largeur dépassait la hauteur, y compris une
    photo réellement prise en paysage sans besoin de rotation (orientation
    EXIF normale)."""
    landscape = _jpeg_bytes((120, 60), orientation=1)

    normalized = normalize_orientation(landscape)

    assert normalized.width == 120
    assert normalized.height == 60


def test_normalize_orientation_rotates_according_to_exif_tag() -> None:
    """Orientation 6 (rotation 90° horaire nécessaire) doit inverser les
    dimensions, indépendamment du fait que largeur > hauteur ou non."""
    tagged = _jpeg_bytes((120, 60), orientation=6)

    normalized = normalize_orientation(tagged)

    assert normalized.width == 60
    assert normalized.height == 120


def test_normalize_orientation_without_exif_leaves_dimensions_untouched() -> None:
    plain = _jpeg_bytes((60, 120))

    normalized = normalize_orientation(plain)

    assert normalized.width == 60
    assert normalized.height == 120


def test_normalize_orientation_always_returns_jpeg() -> None:
    normalized = normalize_orientation(_png_bytes((40, 40)))

    assert normalized.content_type == "image/jpeg"
    with Image.open(io.BytesIO(normalized.data)) as reopened:
        assert reopened.format == "JPEG"


@pytest.mark.parametrize("size_name", list(DERIVATIVE_SIZES))
def test_make_derivative_never_exceeds_its_target_dimension(size_name: str) -> None:
    source = _jpeg_bytes((3000, 1500))

    derivative = make_derivative(source, max_dimension=DERIVATIVE_SIZES[size_name])

    with Image.open(io.BytesIO(derivative)) as image:
        assert max(image.size) <= DERIVATIVE_SIZES[size_name]


def test_make_derivative_never_upscales() -> None:
    source = _jpeg_bytes((100, 50))

    derivative = make_derivative(source, max_dimension=DERIVATIVE_SIZES["full"])

    with Image.open(io.BytesIO(derivative)) as image:
        assert image.size == (100, 50)


def test_make_derivative_blur_changes_the_bytes() -> None:
    image = Image.new("RGB", (200, 200), "white")
    for x in range(0, 200, 20):
        for y in range(0, 200, 20):
            color = "black" if (x // 20 + y // 20) % 2 == 0 else "gray"
            for dx in range(10):
                for dy in range(10):
                    image.putpixel((x + dx, y + dy), ImageColor.getrgb(color))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    source = buffer.getvalue()

    sharp = make_derivative(source, max_dimension=200, blur=False)
    blurred = make_derivative(source, max_dimension=200, blur=True)

    assert sharp != blurred
