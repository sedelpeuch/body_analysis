from __future__ import annotations

import base64
import os
from datetime import datetime
from io import BytesIO

import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import load_all
from body_analysis.phases import load_phases, summarize_phase
from body_analysis.photos import list_photos_by_tag, load_image

st.set_page_config(page_title="Phases", page_icon="🗓️", layout="wide")

st.title("Phases — Timeline et détails")

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

weight_data, daily_cal_data = load_all(DATA_DIR)

# Charger les photos
photos_by_tag = list_photos_by_tag(PHOTOS_DIR)

# Option mode confidentiel dans la sidebar
with st.sidebar:
    confidential = st.toggle(
        "🔒 Mode confidentiel",
        value=True,
        help="Flouter les photos pour la confidentialité",
    )

# Convert to DataFrames for Altair
weight_df = pd.DataFrame(weight_data)
daily_cal_df = pd.DataFrame(daily_cal_data)

fallback = None
if weight_data:
    dates = [r["date"] for r in weight_data]
    fallback = (min(dates), max(dates))
phases = load_phases(fallback_range=fallback)

if not phases:
    st.info("Aucune phase définie")
    st.stop()

# Sélection de phase via cartes cliquables
st.markdown("### Sélectionner une phase")

# Initialiser la phase sélectionnée
if "selected_phase_idx" not in st.session_state:
    st.session_state.selected_phase_idx = 0

# Emoji par type
type_emoji = {"bulk": "🔵", "cut": "🟠", "maintain": "🟢", "free": "⚪"}

# Créer les cartes en colonnes
num_phases = len(phases)
cols_per_row = 3
rows = (num_phases + cols_per_row - 1) // cols_per_row

# Afficher les cartes
for row in range(rows):
    cols = st.columns(cols_per_row)
    for col_idx in range(cols_per_row):
        phase_idx = row * cols_per_row + col_idx
        if phase_idx < num_phases:
            p = phases[phase_idx]
            with cols[col_idx]:
                # Carte cliquable
                is_selected = st.session_state.selected_phase_idx == phase_idx
                border_color = "#FF8C00" if is_selected else "#ddd"

                emoji = type_emoji.get(p.type, "⚪")

                # Utiliser st.container et st.button pour rendre toute la carte cliquable
                container = st.container()
                with container:
                    if st.button(
                        f"**{p.name}**\n\n{emoji} {p.type.capitalize()}\n\n📅 {p.start.strftime('%d/%m/%Y')} → {p.end.strftime('%d/%m/%Y')}",
                        key=f"card_{phase_idx}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary",
                    ):
                        st.session_state.selected_phase_idx = phase_idx
                        st.rerun()

st.divider()

phase = phases[st.session_state.selected_phase_idx]

# Calculer la durée de la phase
phase_duration = (phase.end - phase.start).days
months = phase_duration // 30
days = phase_duration % 30
duration_text = f"{months} mois" if months > 0 else ""
if days > 0:
    duration_text += f" {days} jours" if duration_text else f"{days} jours"

st.markdown(f"## {phase.name} — *{duration_text}*")

# Summary
summary = summarize_phase(weight_data, daily_cal_data, phase)

# Poids
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**⚖️ Poids**")
    weight_delta = summary.get("weight_delta")
    weight_start = summary.get("weight_start")
    weight_end = summary.get("weight_end")
    st.metric("", f"{weight_delta:+.1f} kg" if weight_delta is not None else "N/A")
    if weight_start is not None and weight_end is not None:
        st.caption(f"🔄 {weight_start:.1f} → {weight_end:.1f} kg")
with col2:
    st.markdown("**🟠 Masse grasse**")
    bf_delta = summary.get("body_fat_delta")
    bf_start = summary.get("body_fat_start")
    bf_end = summary.get("body_fat_end")
    st.metric("", f"{bf_delta:+.1f}%" if bf_delta is not None else "N/A")
    if bf_start is not None and bf_end is not None:
        st.caption(f"🔄 {bf_start:.1f} → {bf_end:.1f}%")
with col3:
    st.markdown("**💪 Masse musculaire**")
    muscle_delta = summary.get("skeletal_muscle_delta")
    muscle_start = summary.get("skeletal_muscle_start")
    muscle_end = summary.get("skeletal_muscle_end")
    st.metric("", f"{muscle_delta:+.1f} kg" if muscle_delta is not None else "N/A")
    if muscle_start is not None and muscle_end is not None:
        st.caption(f"🔄 {muscle_start:.1f} → {muscle_end:.1f} kg")
with col4:
    st.markdown("**🍽️ Calories**")
    avg_cal = summary.get("avg_daily_calories")
    st.metric("", f"{avg_cal:.0f} kcal/j" if avg_cal is not None else "N/A")

# Détails supplémentaires en dessous
col1, col2, col3, col4 = st.columns(4)
with col1:
    weight_monthly = summary.get("weight_monthly")
    weight_pct = summary.get("weight_pct")
    if weight_monthly is not None:
        st.caption(f"📈 {weight_monthly:+.2f} kg/mois")
        st.caption(f"📊 {weight_pct:+.1f}%")
with col2:
    bf_monthly = summary.get("body_fat_monthly")
    bf_pct = summary.get("body_fat_pct")
    if bf_monthly is not None:
        st.caption(f"📈 {bf_monthly:+.2f}%/mois")
        st.caption(f"📊 {bf_pct:+.1f}%")
with col3:
    muscle_monthly = summary.get("skeletal_muscle_monthly")
    muscle_pct = summary.get("skeletal_muscle_pct")
    if muscle_monthly is not None:
        st.caption(f"📈 {muscle_monthly:+.2f} kg/mois")
        st.caption(f"📊 {muscle_pct:+.1f}%")

st.markdown("---")

# Charts for the selected phase
mask_w = (weight_df["date"] >= phase.start) & (weight_df["date"] <= phase.end)
mask_c = (daily_cal_df["date"] >= phase.start) & (daily_cal_df["date"] <= phase.end)

w = weight_df.loc[mask_w]
cals = daily_cal_df.loc[mask_c]

# Graphiques
col1, col2 = st.columns(2)
with col1:
    if not w.empty and "weight" in w.columns:
        st.markdown("**Poids**")
        w_clean = w.dropna(subset=["weight"])
        if not w_clean.empty:
            x_domain = [w_clean["date"].min(), w_clean["date"].max()]
            # Ligne des données
            line = (
                alt.Chart(w_clean)
                .mark_line(
                    color="#2ca02c", point=alt.OverlayMarkDef(size=20, color="#2ca02c")
                )
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y=alt.Y("weight:Q", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("weight:Q", title="Poids (kg)", format=".2f"),
                    ],
                )
            )
            # Ligne de tendance
            trend = (
                alt.Chart(w_clean)
                .mark_line(color="#2ca02c", strokeDash=[5, 5], size=2, opacity=0.6)
                .transform_regression("date", "weight", method="linear")
                .encode(
                    x="date:T",
                    y="weight:Q",
                )
            )
            chart = line + trend
            st.altair_chart(chart.properties(height=180), use_container_width=True)

with col2:
    st.markdown("**Calories**")
    if not cals.empty:
        cals_clean = cals.dropna(subset=["calories"])
        if not cals_clean.empty:
            x_domain = [cals_clean["date"].min(), cals_clean["date"].max()]
            cal_chart = (
                alt.Chart(cals)
                .mark_bar(color="#2ca02c")
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y="calories:Q",
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("calories:Q", title="Calories", format=".0f"),
                    ],
                )
            )
            st.altair_chart(cal_chart.properties(height=180), use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    if not w.empty and "body_fat" in w.columns:
        st.markdown("**Masse grasse**")
        bf_clean = w.dropna(subset=["body_fat"])
        if not bf_clean.empty:
            x_domain = [bf_clean["date"].min(), bf_clean["date"].max()]
            # Ligne des données
            line_bf = (
                alt.Chart(bf_clean)
                .mark_line(
                    color="#FF8C00", point=alt.OverlayMarkDef(size=20, color="#FF8C00")
                )
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y=alt.Y("body_fat:Q", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip(
                            "body_fat:Q", title="Masse grasse (%)", format=".2f"
                        ),
                    ],
                )
            )
            # Ligne de tendance
            trend_bf = (
                alt.Chart(bf_clean)
                .mark_line(color="#ff7f0e", strokeDash=[5, 5], size=2, opacity=0.6)
                .transform_regression("date", "body_fat", method="linear")
                .encode(
                    x="date:T",
                    y="body_fat:Q",
                )
            )
            chart_bf = line_bf + trend_bf
            st.altair_chart(chart_bf.properties(height=180), use_container_width=True)

with col2:
    if not w.empty and "skeletal_muscle_mass" in w.columns:
        st.markdown("**Masse musculaire**")
        muscle_clean = w.dropna(subset=["skeletal_muscle_mass"])
        if not muscle_clean.empty:
            x_domain = [muscle_clean["date"].min(), muscle_clean["date"].max()]
            # Ligne des données
            line_muscle = (
                alt.Chart(muscle_clean)
                .mark_line(
                    color="#4ECDC4", point=alt.OverlayMarkDef(size=20, color="#4ECDC4")
                )
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y=alt.Y("skeletal_muscle_mass:Q", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip(
                            "skeletal_muscle_mass:Q",
                            title="Masse musculaire (kg)",
                            format=".2f",
                        ),
                    ],
                )
            )
            # Ligne de tendance
            trend_muscle = (
                alt.Chart(muscle_clean)
                .mark_line(color="#1f77b4", strokeDash=[5, 5], size=2, opacity=0.6)
                .transform_regression("date", "skeletal_muscle_mass", method="linear")
                .encode(
                    x="date:T",
                    y="skeletal_muscle_mass:Q",
                )
            )
            chart_muscle = line_muscle + trend_muscle
            st.altair_chart(
                chart_muscle.properties(height=180), use_container_width=True
            )

# Afficher les photos de la phase
if photos_by_tag:
    st.markdown("**📸 Photos**")

    # Filtrer les photos par période de la phase
    phase_photos = {}
    first_photo_after = {}

    for tag, tag_photos in photos_by_tag.items():
        phase_photos[tag] = []
        photos_after = []

        for month, img_path in tag_photos.items():
            # Convertir YYYY-MM en date
            try:
                month_date = datetime.strptime(month, "%Y-%m")
                # Vérifier si dans la période de la phase
                if phase.start <= month_date <= phase.end:
                    phase_photos[tag].append((month, img_path))
                # Vérifier si c'est après la fin de la phase
                elif month_date > phase.end:
                    photos_after.append((month, img_path))
            except (ValueError, TypeError):
                continue

        # Trier par date décroissante (plus récentes en premier)
        phase_photos[tag] = sorted(phase_photos[tag], key=lambda x: x[0], reverse=True)

        # Trouver la première photo du mois suivant immédiatement la phase
        if photos_after:
            # Calculer le mois suivant la fin de la phase
            year = phase.end.year
            month = phase.end.month + 1
            if month > 12:
                month = 1
                year += 1
            next_month_str = f"{year:04d}-{month:02d}"

            # Chercher uniquement la photo du mois suivant exact
            for month_key, img_path in photos_after:
                if month_key == next_month_str:
                    first_photo_after[tag] = (month_key, img_path)
                    break

    # Afficher chaque tag sur une ligne dans l'ordre spécifié
    tag_order = ["face", "profil", "dos", "bras", "epaule"]
    for tag in tag_order:
        # Vérifier s'il y a des photos pour ce tag (dans la phase ou juste après)
        has_phase_photos = tag in phase_photos and phase_photos[tag]
        has_after_photo = tag in first_photo_after

        if has_phase_photos or has_after_photo:
            st.markdown(f"**{tag.capitalize()}**")

            # Combiner les photos de la phase avec la première photo après
            # La photo après la phase vient en premier (plus récente)
            all_photos = []
            if has_after_photo:
                all_photos.append(first_photo_after[tag])
            if has_phase_photos:
                all_photos.extend(phase_photos[tag])

            # Garder uniquement les 5 plus récentes si besoin
            photos_to_display = all_photos[:5]

            # Créer des colonnes pour afficher les photos côte à côte (format 3:4)
            num_photos = len(photos_to_display)
            if num_photos > 0:
                num_cols = min(
                    num_photos, 5
                )  # Max 5 photos par ligne comme dans Photos.py
                cols = st.columns(num_cols)
                img_height = 280  # Hauteur réduite pour compression

                for idx, (month, img_path) in enumerate(photos_to_display):
                    if idx < 5:  # Limiter à 5 photos
                        with cols[idx]:
                            # Charger et encoder l'image
                            img = load_image(img_path, blur=confidential)
                            buffered = BytesIO()
                            img.save(buffered, format="JPEG")
                            img_base64 = base64.b64encode(buffered.getvalue()).decode()

                            # Convertir YYYY-MM en "Mois Année"
                            date_obj = datetime.strptime(month, "%Y-%m")
                            month_names = {
                                1: "Jan",
                                2: "Fév",
                                3: "Mars",
                                4: "Avr",
                                5: "Mai",
                                6: "Juin",
                                7: "Juil",
                                8: "Août",
                                9: "Sep",
                                10: "Oct",
                                11: "Nov",
                                12: "Déc",
                            }
                            month_display = (
                                f"{month_names[date_obj.month]} {date_obj.year}"
                            )

                            st.markdown(
                                f"""
                                <p style='text-align: center; font-weight: bold; margin-bottom: 2px; font-size:0.75em;'>{month_display}</p>
                                <div style='
                                    width: 100%;
                                    aspect-ratio: 3/4;
                                    height: {img_height}px;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    overflow: hidden;
                                    background-color: transparent;
                                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
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
