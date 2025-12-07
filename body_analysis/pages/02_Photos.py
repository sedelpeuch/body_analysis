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

# Couleurs par tag
tag_colors = {
    "face": {
        "color": "#1f77b4",
        "rgba": "rgba(31, 119, 180",
        "gradient": "linear-gradient(135deg, #1f77b4 0%, #4a9fd8 100%)",
    },
    "profil": {
        "color": "#2ca02c",
        "rgba": "rgba(44, 160, 44",
        "gradient": "linear-gradient(135deg, #2ca02c 0%, #5cd65c 100%)",
    },
    "dos": {
        "color": "#FF8C00",
        "rgba": "rgba(255, 140, 0",
        "gradient": "linear-gradient(135deg, #FF8C00 0%, #ffb347 100%)",
    },
    "bras": {
        "color": "#d62728",
        "rgba": "rgba(214, 39, 40",
        "gradient": "linear-gradient(135deg, #d62728 0%, #ff6b6b 100%)",
    },
    "epaule": {
        "color": "#17becf",
        "rgba": "rgba(23, 190, 207",
        "gradient": "linear-gradient(135deg, #17becf 0%, #5edce6 100%)",
    },
}

ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )
    )
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

# Afficher les boutons de sélection de tags avec couleurs
cols = st.columns(len(available_tags) if len(available_tags) <= 5 else 5)
for idx, tag in enumerate(available_tags):
    tag_style = tag_colors.get(tag, tag_colors["face"])
    with cols[idx % 5]:
        is_selected = st.session_state.selected_tag == tag
        button_style = f"""
        <style>
        div[data-testid="stButton"] > button[kind="secondary"]#{tag}_btn {{
            background: {tag_style['rgba']}, 0.15) !important;
            border: 2px solid {tag_style['color']} !important;
            color: {tag_style['color']} !important;
            font-weight: bold !important;
        }}
        div[data-testid="stButton"] > button[kind="primary"]#{tag}_btn {{
            background: {tag_style['gradient']} !important;
            border: none !important;
            color: white !important;
            font-weight: bold !important;
        }}
        </style>
        """
        if st.button(
            tag.capitalize(),
            key=f"tag_{tag}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
        ):
            st.session_state.selected_tag = tag
            st.rerun()

st.divider()

# Afficher la timeline pour le tag sélectionné
if st.session_state.selected_tag:
    tag = st.session_state.selected_tag
    tag_style = tag_colors.get(tag, tag_colors["face"])
    st.markdown(
        f"""
    <div style="margin: 20px 0; padding: 12px 20px; background: {tag_style['rgba']}, 0.15); border-left: 4px solid {tag_style['color']}; border-radius: 8px;">
        <h2 style="margin: 0; color: {tag_style['color']};">📸 Timeline : {tag.capitalize()}</h2>
    </div>
    """,
        unsafe_allow_html=True,
    )

    tag_photos = photos_by_tag[tag]
    dates = sorted(tag_photos.keys(), reverse=True)

    if not dates:
        st.info(f"Aucune photo pour le tag '{tag}'")
    else:
        # Affichage adapté au format 3:4 (portrait)
        num_cols = 5
        img_height = 480  # 3:4 ratio, largeur auto

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

        for idx in range(0, len(dates), num_cols):
            cols = st.columns(num_cols)
            for col_idx in range(num_cols):
                date_idx = idx + col_idx
                if date_idx < len(dates):
                    date = dates[date_idx]
                    img_path = tag_photos[date]

                    # Charger et encoder l'image en base64
                    img = load_image(img_path, blur=confidential)
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode()

                    with cols[col_idx]:
                        # Convertir YYYY-MM-DD en "JJ Mois Année"
                        date_obj = datetime.strptime(date, "%Y-%m-%d")
                        date_display = f"{date_obj.day} {month_names[date_obj.month]} {date_obj.year}"

                        # Utiliser la date exacte de la photo
                        photo_date = date_obj

                        # Trouver la mesure la plus proche de cette date
                        measures_html = ""
                        if not weight_df.empty:
                            weight_df_copy = weight_df.copy()
                            weight_df_copy["date_delta"] = weight_df_copy["date"].apply(
                                lambda d: abs((d - photo_date).days)
                            )
                            closest_idx = weight_df_copy["date_delta"].idxmin()
                            closest = weight_df_copy.loc[closest_idx]

                            # Construire le HTML des mesures pour l'en-tête
                            measures_html = ""
                            if pd.notnull(closest["weight"]):
                                measures_html += f"<span style='margin: 0 8px;'>⚖️ {closest['weight']:.1f}kg</span>"
                            if pd.notnull(closest["body_fat"]):
                                measures_html += f"<span style='margin: 0 8px;'>📊 {closest['body_fat']:.1f}%</span>"
                            if pd.notnull(closest["skeletal_muscle_mass"]):
                                measures_html += f"<span style='margin: 0 8px;'>💪 {closest['skeletal_muscle_mass']:.1f}kg</span>"

                        st.markdown(
                            f"""
                            <div style='margin: 0; padding-top: 15px;'>
                                <div style='
                                    border-radius: 12px;
                                    border: 2px solid {tag_style["rgba"]}, 0.3);
                                    overflow: hidden;
                                    transition: all 0.3s ease;
                                ' onmouseover="this.style.boxShadow='0 6px 12px {tag_style["rgba"]}, 0.4)'; this.style.transform='translateY(-3px)'" onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)'; this.style.transform='translateY(0)'">
                                    <div style='text-align: center; padding: 10px; background: {tag_style["gradient"]};'>
                                        <div style='color: white; font-weight: bold; font-size: 16px; margin-bottom: 5px;'>{date_display}</div>
                                        <div style='font-size: 13px; color: rgba(255,255,255,0.9);'>{measures_html}</div>
                                    </div>
                                    <div style='
                                        width: 100%;
                                        aspect-ratio: 3/4;
                                        height: {img_height}px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        overflow: hidden;
                                    '>
                                        <img src='data:image/jpeg;base64,{img_base64}' style='
                                            width: 100%;
                                            height: 100%;
                                            object-fit: cover;
                                        '>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
