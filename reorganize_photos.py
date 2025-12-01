#!/usr/bin/env python3
"""Script pour réorganiser les photos de Corps/ vers data/photos/YYYY-MM/"""

import os
import shutil
import re
from pathlib import Path

# Chemins
CORPS_DIR = Path("/home/sedelpeuch/PERSO-SDE/body_analysis/Corps")
PHOTOS_DIR = Path("/home/sedelpeuch/PERSO-SDE/body_analysis/data/photos")

# Mapping des dossiers vers les tags
TAG_MAPPING = {
    "Face": "face",
    "Profil": "profil",
    "Dos": "dos",
    "Bras": "bras",
    "Épaule": "epaule"
}

def extract_date_from_filename(filename: str) -> tuple[str, str] | None:
    """Extrait la date au format YYYY-MM du nom de fichier YYYYMMDD_*.jpg"""
    match = re.match(r'(\d{4})(\d{2})(\d{2})', filename)
    if match:
        year = match.group(1)
        month = match.group(2)
        return year, month
    return None

def reorganize_photos():
    """Réorganise les photos de Corps/ vers data/photos/YYYY-MM/tag.ext"""
    
    if not CORPS_DIR.exists():
        print(f"Le dossier {CORPS_DIR} n'existe pas")
        return
    
    # Créer data/photos si nécessaire
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Parcourir chaque dossier de tag
    for tag_folder, tag_name in TAG_MAPPING.items():
        tag_path = CORPS_DIR / tag_folder
        
        if not tag_path.exists():
            print(f"Dossier {tag_folder} non trouvé, ignoré")
            continue
        
        print(f"\nTraitement de {tag_folder} -> {tag_name}")
        
        # Parcourir toutes les images dans ce dossier
        for img_file in tag_path.glob("*"):
            if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                continue
            
            # Extraire la date
            date_info = extract_date_from_filename(img_file.name)
            if not date_info:
                print(f"  Impossible d'extraire la date de: {img_file.name}")
                continue
            
            year, month = date_info
            month_dir = PHOTOS_DIR / f"{year}-{month}"
            month_dir.mkdir(parents=True, exist_ok=True)
            
            # Nom de destination: tag.ext
            dest_file = month_dir / f"{tag_name}{img_file.suffix}"
            
            # Copier le fichier
            if dest_file.exists():
                print(f"  ⚠️  {dest_file.name} existe déjà dans {month_dir.name}, ignoré")
            else:
                shutil.copy2(img_file, dest_file)
                print(f"  ✓ {img_file.name} -> {month_dir.name}/{dest_file.name}")

if __name__ == "__main__":
    print("Réorganisation des photos...")
    reorganize_photos()
    print("\n✅ Terminé!")
