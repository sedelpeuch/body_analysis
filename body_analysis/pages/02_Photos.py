from __future__ import annotations

import os
import base64
from io import BytesIO
import streamlit as st

from body_analysis.photos import list_photos_by_tag, load_image

st.set_page_config(page_title="Photos", page_icon="🖼️", layout="wide")

st.title("Évolution photos par tag")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
DATA_DIR = os.path.abspath(DATA_DIR)
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")

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
        # Afficher en grille avec des conteneurs de taille fixe
        num_cols = 4

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
                        st.markdown(f"**{month}**")
                        st.markdown(
                            f"""
                            <div style="
                                width: 100%;
                                height: 600px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                overflow: hidden;
                                background-color: transparent;
                                border: 1px solid #ddd;
                                border-radius: 8px;
                            ">
                                <img src="data:image/jpeg;base64,{img_base64}" style="
                                    max-width: 100%;
                                    max-height: 100%;
                                    object-fit: contain;
                                ">
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
