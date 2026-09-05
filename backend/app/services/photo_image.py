"""Traitement d'image pur : octets en, octets out.

Ce module ne connaît ni la base ni MinIO — c'est ce qui le rend testable
sans infrastructure, sur le même principe que analytics/ dans la spec.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

_CONTENT_TYPE_BY_MAGIC: tuple[tuple[bytes, str], ...] = (
    (_JPEG_MAGIC, "image/jpeg"),
    (_PNG_MAGIC, "image/png"),
)

DERIVATIVE_SIZES: dict[str, int] = {"thumb": 320, "medium": 800, "full": 1600}
_BLUR_RADIUS = 25
_JPEG_QUALITY = 90


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    """Image dont l'orientation EXIF a été appliquée aux pixels."""

    data: bytes
    width: int
    height: int
    content_type: str


def sniff_content_type(data: bytes) -> str | None:
    """Détecte le vrai type d'image en inspectant les octets.

    Ne fait jamais confiance au Content-Type déclaré par le client ni à
    l'extension du fichier envoyé.
    """
    for magic, content_type in _CONTENT_TYPE_BY_MAGIC:
        if data.startswith(magic):
            return content_type
    return None


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_orientation(data: bytes) -> NormalizedImage:
    """Corrige la rotation selon l'orientation EXIF, jamais selon la forme.

    Bug corrigé : l'application historique tournait l'image dès que
    largeur > hauteur, ce qui inversait à tort toute photo réellement prise
    en paysage. ImageOps.exif_transpose lit le tag d'orientation EXIF et
    applique exactement la rotation qu'il décrit, ou aucune s'il est absent
    ou vaut 1 (normal).
    """
    with Image.open(io.BytesIO(data)) as opened:
        transposed = ImageOps.exif_transpose(opened) or opened
        rgb = transposed.convert("RGB")
        buffer = io.BytesIO()
        rgb.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        return NormalizedImage(
            data=buffer.getvalue(),
            width=rgb.width,
            height=rgb.height,
            content_type="image/jpeg",
        )


def make_derivative(
    normalized: bytes, *, max_dimension: int, blur: bool = False
) -> bytes:
    """Redimensionne sans jamais agrandir, et floute optionnellement.

    Le flou n'est jamais mis en cache par l'appelant : c'est un rendu à la
    demande du mode confidentiel, recalculé à chaque requête.
    """
    with Image.open(io.BytesIO(normalized)) as image:
        if image.mode not in {"RGB", "RGBA", "L"}:
            image = image.convert("RGB")
        width, height = image.size
        if max(width, height) <= max_dimension:
            resized = image.copy()
        else:
            scale = max_dimension / max(width, height)
            resized = image.resize(
                (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
                Image.Resampling.LANCZOS,
            )
        if blur:
            resized = resized.filter(ImageFilter.GaussianBlur(radius=_BLUR_RADIUS))
        buffer = io.BytesIO()
        resized.save(buffer, format="JPEG", quality=_JPEG_QUALITY)
        return buffer.getvalue()
