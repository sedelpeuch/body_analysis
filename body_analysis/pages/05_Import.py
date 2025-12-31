from __future__ import annotations

import os
import re

import streamlit as st

st.set_page_config(page_title="Import", page_icon="📥", layout="wide")

st.title("📥 Import de données")

ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
        ),
    )

st.markdown(
    """
Cette page permet d'importer les données nécessaires au fonctionnement de l'application.
""",
)

# Section 1: CSV Samsung Health
st.markdown("## 📊 Fichiers CSV Samsung Health")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### Poids")
    weight_file = st.file_uploader(
        "Fichier com.samsung.health.weight*.csv",
        type=["csv"],
        key="weight_upload",
        help="Exporter depuis Samsung Health: Paramètres > Télécharger mes données > Poids",
    )

    if weight_file:
        if st.button("💾 Sauvegarder le fichier poids", key="save_weight"):
            try:
                # Créer le dossier data si nécessaire
                os.makedirs(DATA_DIR, exist_ok=True)

                # Sauvegarder avec le nom d'origine
                dest_path = os.path.join(DATA_DIR, weight_file.name)
                with open(dest_path, "wb") as f:
                    f.write(weight_file.getbuffer())
                st.success(f"✅ Fichier sauvegardé dans: {dest_path}")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Erreur lors de la sauvegarde: {e!s}")
                st.info(f"DATA_DIR: {DATA_DIR}")

with col2:
    st.markdown("### Alimentation")
    food_file = st.file_uploader(
        "Fichier com.samsung.health.food_intake*.csv",
        type=["csv"],
        key="food_upload",
        help="Exporter depuis Samsung Health: Paramètres > Télécharger mes données > Nutrition",
    )

    if food_file:
        if st.button("💾 Sauvegarder le fichier alimentation", key="save_food"):
            try:
                # Créer le dossier data si nécessaire
                os.makedirs(DATA_DIR, exist_ok=True)

                dest_path = os.path.join(DATA_DIR, food_file.name)
                with open(dest_path, "wb") as f:
                    f.write(food_file.getbuffer())
                st.success(f"✅ Fichier sauvegardé dans: {dest_path}")
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"❌ Erreur lors de la sauvegarde: {e!s}")
                st.info(f"DATA_DIR: {DATA_DIR}")

with col3:
    st.markdown("### Exercice")
    exercise_file = st.file_uploader(
        "Fichier com.samsung.shealth.exercise*.csv",
        type=["csv"],
        key="exercise_upload",
        help="Exporter depuis Samsung Health: Paramètres > Télécharger mes données > Exercice",
    )

    if exercise_file:
        if st.button("💾 Sauvegarder le fichier exercice", key="save_exercise"):
            try:
                os.makedirs(DATA_DIR, exist_ok=True)
                dest_path = os.path.join(DATA_DIR, exercise_file.name)
                with open(dest_path, "wb") as f:
                    f.write(exercise_file.getbuffer())
                st.success(f"✅ Fichier sauvegardé dans: {dest_path}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur lors de la sauvegarde: {e!s}")
                st.info(f"DATA_DIR: {DATA_DIR}")
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

Les photos seront organisées dans des dossiers **YYYY-MM-DD** (un dossier par date), permettant d'avoir plusieurs photos le même mois.

**Tags disponibles:** face, profil, dos, bras, epaule
""",
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
        try:
            photos_dir = os.path.join(DATA_DIR, "photos")
            # Créer le dossier photos si nécessaire
            os.makedirs(photos_dir, exist_ok=True)

            success_count = 0
            error_count = 0

            for photo_file in photo_files:
                # Extraire la date du nom de fichier
                match = re.match(r"(\d{4})(\d{2})(\d{2})", photo_file.name)
                if match:
                    year = match.group(1)
                    month = match.group(2)
                    day = match.group(3)
                    date_dir = os.path.join(photos_dir, f"{year}-{month}-{day}")

                    # Créer le dossier si nécessaire
                    os.makedirs(date_dir, exist_ok=True)

                    # Extension du fichier
                    ext = os.path.splitext(photo_file.name)[1]
                    dest_path = os.path.join(date_dir, f"{tag}{ext}")

                    # Sauvegarder
                    with open(dest_path, "wb") as f:
                        f.write(photo_file.getbuffer())

                    success_count += 1
                    st.text(f"✅ {photo_file.name} → {year}-{month}-{day}/{tag}{ext}")
                else:
                    error_count += 1
                    st.warning(f"⚠️ Impossible d'extraire la date de: {photo_file.name}")

            if success_count > 0:
                st.success(f"✅ {success_count} photo(s) importée(s) avec succès!")
            if error_count > 0:
                st.error(
                    f"❌ {error_count} photo(s) ignorée(s) (format de nom invalide)",
                )

            if success_count > 0:
                st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"❌ Erreur lors de l'import: {e!s}")
            st.info(f"DATA_DIR: {DATA_DIR}")

# Afficher les photos existantes par tag
st.markdown("### 📁 Photos actuelles")
photos_dir = os.path.join(DATA_DIR, "photos")

if os.path.exists(photos_dir):
    # Compter les photos par tag
    tag_counts = {}
    for date_dir in sorted(os.listdir(photos_dir)):
        date_path = os.path.join(photos_dir, date_dir)
        if os.path.isdir(date_path):
            for photo_file in os.listdir(date_path):
                if photo_file.lower().endswith((".jpg", ".jpeg", ".png")):
                    tag_name = os.path.splitext(photo_file)[0].lower()
                    if tag_name not in tag_counts:
                        tag_counts[tag_name] = []
                    tag_counts[tag_name].append(date_dir)

    if tag_counts:
        for tag_name, dates in sorted(tag_counts.items()):
            st.text(
                f"• {tag_name}: {len(dates)} photo(s) ({', '.join(sorted(dates))})",
            )
    else:
        st.info("Aucune photo trouvée")
else:
    st.info("Aucun dossier photos trouvé")

st.divider()

# Section 3: Configuration des phases
st.markdown("## ⚙️ Configuration")
st.markdown(
    "Le fichier `data/phases.json` doit être édité manuellement pour définir vos phases.",
)

phases_path = os.path.join(DATA_DIR, "phases.json")
if os.path.exists(phases_path):
    st.success("✅ Fichier phases.json trouvé")
    if st.checkbox("Afficher le contenu"):
        with open(phases_path, encoding="utf-8") as f:
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
    """,
    )
