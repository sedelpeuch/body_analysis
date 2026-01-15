from __future__ import annotations

import os
import re
import shutil
import zipfile

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


def _cleanup_old_csv_files(data_dir: str) -> None:
    """Garder seulement le fichier le plus récent pour chaque type."""
    csv_patterns = {
        "weight": "com.samsung.health.weight",
        "food": "com.samsung.health.food_intake",
        "exercise": "com.samsung.shealth.exercise",
    }

    for csv_type, pattern in csv_patterns.items():
        # Trouver tous les fichiers correspondant au pattern
        matching_files = []
        for file in os.listdir(data_dir):
            if file.endswith(".csv") and pattern in file:
                # Pour l'exercice, valider que c'est le bon format
                if csv_type == "exercise":
                    # Doit être: com.samsung.shealth.exercise.YYYYMMDDHHMMSS.csv
                    if not re.match(r"com\.samsung\.shealth\.exercise\.\d{14}\.csv$", file):
                        continue

                file_path = os.path.join(data_dir, file)
                matching_files.append((file, file_path))

        # Si plusieurs fichiers, garder que le plus récent
        if len(matching_files) > 1:
            # Trier par date de modification (plus récent en dernier)
            matching_files.sort(key=lambda x: os.path.getmtime(x[1]))

            # Supprimer tous sauf le dernier
            for file_to_delete, file_path in matching_files[:-1]:
                os.remove(file_path)
                st.info(f"🗑️ Supprimé ancien fichier: {file_to_delete}")


st.markdown(
    """
Cette page permet d'importer les données nécessaires au fonctionnement de l'application.
""",
)

# Section 0: Import ZIP Samsung Health
st.markdown("## 📦 Import depuis ZIP Samsung Health")

st.markdown(
    """
Importez directement le ZIP exporté depuis Samsung Health. 
L'application extraira automatiquement les fichiers pertinents (CSV et JSON).
""",
)

zip_file = st.file_uploader(
    "Fichier ZIP Samsung Health",
    type=["zip"],
    key="samsung_zip_upload",
    help="Téléchargez le fichier samsunghealth_*.zip depuis Samsung Health",
)

if zip_file:
    if st.button("📥 Importer le ZIP Samsung Health", key="import_zip"):
        try:
            with st.spinner("Extraction du ZIP..."):
                # Créer le dossier data si nécessaire
                os.makedirs(DATA_DIR, exist_ok=True)

                # Extraire le ZIP
                with zipfile.ZipFile(zip_file, "r") as zip_ref:
                    # Créer un dossier temporaire
                    temp_dir = os.path.join(DATA_DIR, ".temp_samsung_import")
                    os.makedirs(temp_dir, exist_ok=True)

                    # Extraire tout
                    zip_ref.extractall(temp_dir)

                    # Chercher le dossier root (premier niveau du ZIP)
                    root_dir = temp_dir
                    items_in_temp = os.listdir(temp_dir)
                    if len(items_in_temp) == 1:
                        first_item = os.path.join(temp_dir, items_in_temp[0])
                        if os.path.isdir(first_item):
                            # C'est un dossier unique, on rentre dedans
                            root_dir = first_item

                    extracted_files = []

                    # Copier les fichiers CSV pertinents
                    csv_patterns = [
                        "com.samsung.health.weight",
                        "com.samsung.health.food_intake",
                        "com.samsung.shealth.exercise",
                    ]

                    for file in os.listdir(root_dir):
                        file_path = os.path.join(root_dir, file)
                        if os.path.isfile(file_path) and file.endswith(".csv"):
                            # Vérifier si c'est un fichier pertinent
                            for pattern in csv_patterns:
                                if pattern in file:
                                    # Pour l'exercice, valider le format exact
                                    if pattern == "com.samsung.shealth.exercise":
                                        if not re.match(
                                            r"com\.samsung\.shealth\.exercise\.\d{14}\.csv$",
                                            file,
                                        ):
                                            break

                                    dest_path = os.path.join(DATA_DIR, file)
                                    shutil.copy2(file_path, dest_path)
                                    extracted_files.append(file)
                                    st.success(f"✅ Importé: {file}")
                                    break

                    # Copier les dossiers JSON pertinents
                    json_dir = os.path.join(root_dir, "jsons")
                    if os.path.exists(json_dir):
                        dest_json_dir = os.path.join(
                            DATA_DIR,
                            "com.samsung.shealth.exercise",
                        )
                        json_folders = [
                            "com.samsung.shealth.exercise",
                        ]

                        for json_folder in json_folders:
                            src_path = os.path.join(json_dir, json_folder)
                            if os.path.exists(src_path):
                                # Supprimer le dossier existant s'il existe
                                if os.path.exists(dest_json_dir):
                                    shutil.rmtree(dest_json_dir)
                                # Copier le nouveau
                                shutil.copytree(src_path, dest_json_dir)
                                extracted_files.append(f"jsons/{json_folder}")
                                st.success(f"✅ Importé: jsons/{json_folder}")

                    # Nettoyer le dossier temporaire
                    shutil.rmtree(temp_dir)

                # Garder seulement les fichiers les plus récents
                _cleanup_old_csv_files(DATA_DIR)

                if extracted_files:
                    st.success(
                        f"✅ Import réussi! {len(extracted_files)} élément(s) importé(s)",
                    )
                    st.rerun()
                else:
                    st.warning("⚠️ Aucun fichier pertinent trouvé dans le ZIP")

        except zipfile.BadZipFile:
            st.error("❌ Le fichier n'est pas un ZIP valide")
        except Exception as e:  # noqa: BLE001
            st.error(f"❌ Erreur lors de l'import: {e!s}")
            st.info(f"DATA_DIR: {DATA_DIR}")


st.divider()

# Section: Photos
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
