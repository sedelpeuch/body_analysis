from __future__ import annotations

import os
import base64
from io import BytesIO
from datetime import datetime
import streamlit as st
import pandas as pd

from body_analysis.photos import list_photos_by_tag, load_image
from body_analysis.data_ingestion import load_all

st.set_page_config(page_title="Photos", page_icon="🖼️", layout="wide")

st.title("Évolution photos par tag")

ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.abspath(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
    ))
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")

# Charger les données de mesures
weight_data, _ = load_all(DATA_DIR)
weight_df = pd.DataFrame(weight_data)

photos_by_tag = list_photos_by_tag(PHOTOS_DIR)

if not photos_by_tag:
    st.info(
        "Aucune photo trouvée. Placez vos photos dans data/photos/YYYY-MM/ avec les noms: face.png, profil.png, dos.png, bras.png, epaule.png"
    )
    st.stop()

# Options (dans la sidebar pour être discret)
with st.sidebar:
    confidential = st.toggle(
        "🔒 Mode confidentiel",
        value=True,
        help="Flouter les photos pour la confidentialité",
    )

# Tags disponibles
available_tags = sorted(photos_by_tag.keys())
st.markdown("### Sélectionner un tag")

# Initialiser le tag sélectionné
if "selected_tag" not in st.session_state:
    st.session_state.selected_tag = available_tags[0] if available_tags else None

# Afficher les boutons de sélection de tags
cols = st.columns(len(available_tags) if len(available_tags) <= 5 else 5)
for idx, tag in enumerate(available_tags):
    with cols[idx % 5]:
        if st.button(
            tag.capitalize(),
            key=f"tag_{tag}",
            type="primary" if st.session_state.selected_tag == tag else "secondary",
            use_container_width=True,
        ):
            st.session_state.selected_tag = tag
            st.rerun()

st.divider()

# Afficher la timeline pour le tag sélectionné
if st.session_state.selected_tag:
    tag = st.session_state.selected_tag
    st.markdown(f"## 📸 Timeline : {tag.capitalize()}")

    tag_photos = photos_by_tag[tag]
    months = sorted(tag_photos.keys(), reverse=True)

    if not months:
        st.info(f"Aucune photo pour le tag '{tag}'")
    else:
        # Affichage adapté au format 3:4 (portrait)
        num_cols = 5
        img_height = 480  # 3:4 ratio, largeur auto

        def first_sunday(year, month):
            """Trouve le premier dimanche du mois donné."""
            d = datetime(year, month, 1)
            while d.weekday() != 6:  # 6 = dimanche
                d = d.replace(day=d.day + 1)
            return d

        for idx in range(0, len(months), num_cols):
            cols = st.columns(num_cols)
            for col_idx in range(num_cols):
                month_idx = idx + col_idx
                if month_idx < len(months):
                    month = months[month_idx]
                    img_path = tag_photos[month]

                    # Charger et encoder l'image en base64
                    img = load_image(img_path, blur=confidential)
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode()

                    with cols[col_idx]:
                        # Convertir YYYY-MM en "Mois Année"
                        date_obj = datetime.strptime(month, "%Y-%m")
                        month_names = {
                            1: "Janvier",
                            2: "Février",
                            3: "Mars",
                            4: "Avril",
                            5: "Mai",
                            6: "Juin",
                            7: "Juillet",
                            8: "Août",
                            9: "Septembre",
                            10: "Octobre",
                            11: "Novembre",
                            12: "Décembre",
                        }
                        month_display = f"{month_names[date_obj.month]} {date_obj.year}"

                        # Calculer la date de la photo (premier dimanche du mois)
                        photo_date = first_sunday(date_obj.year, date_obj.month)
                        
                        # Trouver la mesure la plus proche de cette date
                        measures_html = ""
                        if not weight_df.empty:
                            weight_df_copy = weight_df.copy()
                            weight_df_copy["date_delta"] = weight_df_copy["date"].apply(
                                lambda d: abs((d - photo_date).days)
                            )
                            closest_idx = weight_df_copy["date_delta"].idxmin()
                            closest = weight_df_copy.loc[closest_idx]
                            
                            # Construire le HTML des mesures
                            measures_html = "<div style='font-size:0.75em; color:#888; text-align:center; margin-bottom:8px; display:flex; justify-content:center; gap:8px;'>"
                            if pd.notnull(closest["weight"]):
                                measures_html += f"<span>⚖️ {closest['weight']:.1f}kg</span>"
                            if pd.notnull(closest["body_fat"]):
                                measures_html += f"<span>📊 {closest['body_fat']:.1f}%</span>"
                            if pd.notnull(closest["skeletal_muscle_mass"]):
                                measures_html += f"<span>💪 {closest['skeletal_muscle_mass']:.1f}kg</span>"
                            measures_html += "</div>"

                        st.markdown(
                            f"""
                            <p style='text-align: center; font-weight: bold; margin-bottom: 4px;'>{month_display}</p>
                            {measures_html}
                            <div style='
                                width: 100%;
                                aspect-ratio: 3/4;
                                height: {img_height}px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                overflow: hidden;
                                background-color: transparent;
                                border: 1px solid #ddd;
                                border-radius: 8px;
                            '>
                                <img src='data:image/jpeg;base64,{img_base64}' style='
                                    width: auto;
                                    height: 100%;
                                    object-fit: cover;
                                    border-radius: 4px;
                                '>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
