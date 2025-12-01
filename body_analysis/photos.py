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


def list_photos_by_tag(photos_dir: str | None = None) -> Dict[str, Dict[str, str]]:
    """Return mapping tag -> {YYYY-MM: filepath}.
    
    Expects filenames like: YYYY-MM/face.png, YYYY-MM/profil.png, etc.
    Tags: face, profil, dos, bras, epaule
    """
    photos_dir = photos_dir or PHOTOS_DIR_DEFAULT
    if not os.path.isdir(photos_dir):
        return {}
    
    tags_data: Dict[str, Dict[str, str]] = {}
    month_dirs = sorted([d for d in glob.glob(os.path.join(photos_dir, "*")) if os.path.isdir(d)])
    
    for md in month_dirs:
        month_key = os.path.basename(md)
        # Chercher tous les fichiers images
        images = glob.glob(os.path.join(md, "*.jpg")) + glob.glob(os.path.join(md, "*.png"))
        
        for img_path in images:
            # Extraire le tag du nom de fichier (sans extension)
            filename = os.path.basename(img_path)
            tag = os.path.splitext(filename)[0].lower()
            
            if tag not in tags_data:
                tags_data[tag] = {}
            tags_data[tag][month_key] = img_path
    
    return tags_data


def load_image(image_path: str, blur: bool = False, target_height: int | None = None) -> Image.Image:
    """Load an image and optionally apply a blur filter for confidentiality."""
    img = Image.open(image_path)
    
    # Rotation automatique si l'image est plus large que haute (mode paysage)
    if img.width > img.height:
        img = img.rotate(-90, expand=True)
    
    # Redimensionner à une hauteur fixe si spécifié
    if target_height:
        aspect_ratio = img.width / img.height
        new_width = int(target_height * aspect_ratio)
        img = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
    
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=500))
    return img


def month_sequence(months: List[str]) -> List[Tuple[str, str | None]]:
    """Return list of (current, previous) month pairs for comparison UI."""
    seq: List[Tuple[str, str | None]] = []
    prev: str | None = None
    for m in sorted(months):
        seq.append((m, prev))
        prev = m
    return seq
