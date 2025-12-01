from __future__ import annotations

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")

st.title("📥 Import de données")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
DATA_DIR = os.path.abspath(DATA_DIR)

st.markdown(
    """
Cette page permet d'importer les données nécessaires au fonctionnement de l'application.
"""
)

# Section 1: CSV Samsung Health
st.markdown("## 📊 Fichiers CSV Samsung Health")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Poids et composition")
    weight_file = st.file_uploader(
        "Fichier com.samsung.health.weight*.csv",
        type=["csv"],
        key="weight_upload",
        help="Exporter depuis Samsung Health: Paramètres > Télécharger mes données > Poids",
    )

    if weight_file:
        if st.button("💾 Sauvegarder le fichier poids", key="save_weight"):
            # Sauvegarder avec le nom d'origine
            dest_path = os.path.join(DATA_DIR, weight_file.name)
            with open(dest_path, "wb") as f:
                f.write(weight_file.getbuffer())
            st.success(f"✅ Fichier sauvegardé: {weight_file.name}")
            st.rerun()

with col2:
    st.markdown("### Apport alimentaire")
    food_file = st.file_uploader(
        "Fichier com.samsung.health.food_intake*.csv",
        type=["csv"],
        key="food_upload",
        help="Exporter depuis Samsung Health: Paramètres > Télécharger mes données > Nutrition",
    )

    if food_file:
        if st.button("💾 Sauvegarder le fichier alimentation", key="save_food"):
            dest_path = os.path.join(DATA_DIR, food_file.name)
            with open(dest_path, "wb") as f:
                f.write(food_file.getbuffer())
            st.success(f"✅ Fichier sauvegardé: {food_file.name}")
            st.rerun()

# Afficher les fichiers CSV existants
st.markdown("### 📁 Fichiers CSV actuels")
existing_csvs = []
if os.path.exists(DATA_DIR):
    existing_csvs = [f for f in os.listdir(DATA_DIR) if f.endswith(".csv")]

if existing_csvs:
    for csv_file in sorted(existing_csvs):
        st.text(f"• {csv_file}")
else:
    st.info("Aucun fichier CSV trouvé")

st.divider()

# Section 2: Photos
st.markdown("## 📸 Photos mensuelles")

st.markdown(
    """
Importez vos photos organisées par tag. Chaque photo doit avoir un nom de fichier au format **YYYYMMDD_HHMMSS.jpg**.

**Tags disponibles:** face, profil, dos, bras, epaule
"""
)

# Tag selector
tag = st.selectbox(
    "Sélectionner le tag",
    ["face", "profil", "dos", "bras", "epaule"],
    help="Type de photo à importer",
)

# Multiple photos upload
photo_files = st.file_uploader(
    f"Photos pour le tag '{tag}'",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=f"photos_upload_{tag}",
    help="Sélectionnez une ou plusieurs photos. Le mois sera extrait du nom de fichier.",
)

if photo_files:
    st.markdown(f"**{len(photo_files)} photo(s) sélectionnée(s)**")

    if st.button(f"💾 Importer {len(photo_files)} photo(s)", key="save_photos"):
        photos_dir = os.path.join(DATA_DIR, "photos")
        success_count = 0
        error_count = 0

        for photo_file in photo_files:
            # Extraire la date du nom de fichier
            match = re.match(r"(\d{4})(\d{2})(\d{2})", photo_file.name)
            if match:
                year = match.group(1)
                month = match.group(2)
                month_dir = os.path.join(photos_dir, f"{year}-{month}")

                # Créer le dossier si nécessaire
                os.makedirs(month_dir, exist_ok=True)

                # Extension du fichier
                ext = os.path.splitext(photo_file.name)[1]
                dest_path = os.path.join(month_dir, f"{tag}{ext}")

                # Sauvegarder
                with open(dest_path, "wb") as f:
                    f.write(photo_file.getbuffer())

                success_count += 1
                st.text(f"✅ {photo_file.name} → {year}-{month}/{tag}{ext}")
            else:
                error_count += 1
                st.warning(f"⚠️ Impossible d'extraire la date de: {photo_file.name}")

        if success_count > 0:
            st.success(f"✅ {success_count} photo(s) importée(s) avec succès!")
        if error_count > 0:
            st.error(f"❌ {error_count} photo(s) ignorée(s) (format de nom invalide)")

        if success_count > 0:
            st.rerun()

# Afficher les photos existantes par tag
st.markdown("### 📁 Photos actuelles")
photos_dir = os.path.join(DATA_DIR, "photos")

if os.path.exists(photos_dir):
    # Compter les photos par tag
    tag_counts = {}
    for month_dir in sorted(os.listdir(photos_dir)):
        month_path = os.path.join(photos_dir, month_dir)
        if os.path.isdir(month_path):
            for photo_file in os.listdir(month_path):
                if photo_file.lower().endswith((".jpg", ".jpeg", ".png")):
                    tag_name = os.path.splitext(photo_file)[0].lower()
                    if tag_name not in tag_counts:
                        tag_counts[tag_name] = []
                    tag_counts[tag_name].append(month_dir)

    if tag_counts:
        for tag_name, months in sorted(tag_counts.items()):
            st.text(
                f"• {tag_name}: {len(months)} photo(s) ({', '.join(sorted(months))})"
            )
    else:
        st.info("Aucune photo trouvée")
else:
    st.info("Aucun dossier photos trouvé")

st.divider()

# Section 3: Configuration des phases
st.markdown("## ⚙️ Configuration")
st.markdown(
    "Le fichier `data/phases.json` doit être édité manuellement pour définir vos phases."
)

phases_path = os.path.join(DATA_DIR, "phases.json")
if os.path.exists(phases_path):
    st.success("✅ Fichier phases.json trouvé")
    if st.checkbox("Afficher le contenu"):
        with open(phases_path, "r", encoding="utf-8") as f:
            st.code(f.read(), language="json")
else:
    st.warning("⚠️ Fichier phases.json non trouvé")
    st.markdown(
        """
    Créez un fichier `data/phases.json` avec la structure suivante:
    ```json
    [
        {
            "name": "Phase libre",
            "type": "free",
            "start": "2025-01-01",
            "end": "2025-02-28"
        },
        {
            "name": "Première prise de masse",
            "type": "bulk",
            "start": "2025-03-01",
            "end": "2025-05-31"
        }
    ]
    ```
    
    **Types disponibles:** `free`, `bulk`, `cut`, `maintain`
    """
    )
