from __future__ import annotations

import os
import streamlit as st

from body_analysis.photos import list_monthly_photo_sets, load_image, month_sequence

st.set_page_config(page_title="Photos", page_icon="🖼️", layout="wide")

st.title("Comparaison photos — mois à mois")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
DATA_DIR = os.path.abspath(DATA_DIR)
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")

photos_by_month = list_monthly_photo_sets(PHOTOS_DIR)

if not photos_by_month:
    st.info("Aucun dossier de photos trouvé. Placez vos photos dans data/photos/YYYY-MM/")
    st.stop()

months = sorted(photos_by_month.keys())
confidential = st.checkbox("Mode confidentiel (flouter les photos)", value=True)

for current, previous in month_sequence(months):
    st.subheader(f"{current} — comparaison")
    cols = st.columns(2)

    with cols[0]:
        st.caption(f"{previous or 'Aucun mois précédent'}")
        if previous and photos_by_month.get(previous):
            for p in photos_by_month[previous][:5]:
                st.image(load_image(p, blur=confidential), use_column_width=True)
        else:
            st.write("—")

    with cols[1]:
        st.caption(current)
        for p in photos_by_month[current][:5]:
            st.image(load_image(p, blur=confidential), use_column_width=True)

    st.divider()
