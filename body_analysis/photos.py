from __future__ import annotations

import glob
import os
from typing import Dict, List, Tuple

from PIL import Image, ImageFilter

DATA_DIR_DEFAULT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PHOTOS_DIR_DEFAULT = os.path.join(DATA_DIR_DEFAULT, "photos")


def list_monthly_photo_sets(photos_dir: str | None = None) -> Dict[str, List[str]]:
    """Return mapping YYYY-MM -> list of image file paths."""
    photos_dir = photos_dir or PHOTOS_DIR_DEFAULT
    if not os.path.isdir(photos_dir):
        return {}
    month_dirs = sorted([d for d in glob.glob(os.path.join(photos_dir, "*")) if os.path.isdir(d)])
    out: Dict[str, List[str]] = {}
    for md in month_dirs:
        month_key = os.path.basename(md)
        images = sorted(glob.glob(os.path.join(md, "*.jpg")) + glob.glob(os.path.join(md, "*.png")))
        if images:
            out[month_key] = images
    return out


def load_image(image_path: str, blur: bool = False) -> Image.Image:
    """Load an image and optionally apply a blur filter for confidentiality."""
    img = Image.open(image_path)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=12))
    return img


def month_sequence(months: List[str]) -> List[Tuple[str, str | None]]:
    """Return list of (current, previous) month pairs for comparison UI."""
    seq: List[Tuple[str, str | None]] = []
    prev: str | None = None
    for m in sorted(months):
        seq.append((m, prev))
        prev = m
    return seq
