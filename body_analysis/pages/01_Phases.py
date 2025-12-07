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

# CSS moderne
st.markdown(
    """
<style>
    .phase-selector-card {
        background: rgba(102, 126, 234, 0.05);
        padding: 20px;
        border-radius: 12px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    .phase-selector-card:hover {
        border-color: rgba(102, 126, 234, 0.5);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(102, 126, 234, 0.2);
        text-align: center;
        margin: 10px 0;
        min-height: 280px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label {
        font-size: 14px;
        color: #999;
        margin-top: 5px;
    }
    .sub-metric {
        font-size: 13px;
        color: #666;
        margin-top: 8px;
        padding: 5px 10px;
        background: rgba(102, 126, 234, 0.05);
        border-radius: 8px;
        display: inline-block;
    }
</style>
""",
    unsafe_allow_html=True,
)

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

# Afficher les objectifs si la phase en a
if hasattr(phase, "objectives") and phase.objectives:
    st.markdown("**🎯 Objectifs de la phase**")

    obj = phase.objectives
    obj_col1, obj_col2, obj_col3, obj_col4 = st.columns(4)

    with obj_col1:
        st.markdown("**⚖️ Poids**")
        weight_target = obj.get("weight_target")
        weight_achieved = summary.get("weight_end")
        if weight_target and weight_achieved:
            gap = weight_achieved - weight_target
            success = abs(gap) <= 2
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(44, 160, 44, 0.1); border-radius: 10px; border: 1px solid rgba(44, 160, 44, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #2ca02c;">{weight_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {weight_target:.1f} kg</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} kg</div>
                <div style="background: {'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' if success else 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)'}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; display: inline-block; margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with obj_col2:
        st.markdown("**🔥 Grasse**")
        bf_target = obj.get("body_fat_target")
        bf_achieved = summary.get("body_fat_end")
        if bf_target and bf_achieved:
            gap = bf_achieved - bf_target
            success = abs(gap) <= 2
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(255, 140, 0, 0.1); border-radius: 10px; border: 1px solid rgba(255, 140, 0, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #FF8C00;">{bf_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {bf_target:.1f} %</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} %</div>
                <div style="background: {'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' if success else 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)'}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; display: inline-block; margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with obj_col3:
        st.markdown("**💪 Musculaire**")
        muscle_target = obj.get("muscle_target")
        muscle_achieved = summary.get("skeletal_muscle_end")
        if muscle_target and muscle_achieved:
            gap = muscle_achieved - muscle_target
            success = abs(gap) <= 1
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(31, 119, 180, 0.1); border-radius: 10px; border: 1px solid rgba(31, 119, 180, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #1f77b4;">{muscle_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {muscle_target:.1f} kg</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} kg</div>
                <div style="background: {'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' if success else 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)'}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; display: inline-block; margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with obj_col4:
        st.markdown("**🍽️ Calories moyennes**")
        cal_target = obj.get("calories_target")
        cal_achieved = summary.get("avg_daily_calories")
        if cal_target and cal_achieved:
            gap = cal_achieved - cal_target
            success = abs(gap) <= 200
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 10px; border: 1px solid rgba(102, 126, 234, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #667eea;">{cal_achieved:.0f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {cal_target:.0f} kcal</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.0f} kcal</div>
                <div style="background: {'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)' if success else 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)'}; padding: 5px 15px; border-radius: 20px; color: white; font-weight: bold; display: inline-block; margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    st.divider()

# Métriques avec design moderne
col1, col2, col3, col4 = st.columns(4)

with col1:
    weight_delta = summary.get("weight_delta")
    weight_start = summary.get("weight_start")
    weight_end = summary.get("weight_end")
    weight_monthly = summary.get("weight_monthly")
    weight_pct = summary.get("weight_pct")

    delta_color = "#2ca02c" if weight_delta and weight_delta < 0 else "#667eea"

    if weight_delta is not None:
        st.markdown(
            f"""
        <div class="metric-card" style="border-left: 4px solid {delta_color};">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">⚖️ POIDS</div>
            <div class="metric-value" style="color: {delta_color};">{weight_delta:+.1f}</div>
            <div class="metric-label">kg</div>
            {"<div class='sub-metric'>🔄 " + f"{weight_start:.1f} → {weight_end:.1f} kg</div>" if weight_start and weight_end else ""}
            {"<div class='sub-metric'>📈 " + f"{weight_monthly:+.2f} kg/mois</div>" if weight_monthly else ""}
            {"<div class='sub-metric'>📊 " + f"{weight_pct:+.1f}%</div>" if weight_pct else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div style="color: #999;">Pas de données</div></div>',
            unsafe_allow_html=True,
        )

with col2:
    bf_delta = summary.get("body_fat_delta")
    bf_start = summary.get("body_fat_start")
    bf_end = summary.get("body_fat_end")
    bf_monthly = summary.get("body_fat_monthly")
    bf_pct = summary.get("body_fat_pct")

    delta_color = "#FF8C00"

    if bf_delta is not None:
        st.markdown(
            f"""
        <div class="metric-card" style="border-left: 4px solid {delta_color};">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">🔥 GRASSE</div>
            <div class="metric-value" style="color: {delta_color};">{bf_delta:+.1f}</div>
            <div class="metric-label">%</div>
            {"<div class='sub-metric'>🔄 " + f"{bf_start:.1f} → {bf_end:.1f}%</div>" if bf_start and bf_end else ""}
            {"<div class='sub-metric'>📈 " + f"{bf_monthly:+.2f}%/mois</div>" if bf_monthly else ""}
            {"<div class='sub-metric'>📊 " + f"{bf_pct:+.1f}%</div>" if bf_pct else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div style="color: #999;">Pas de données</div></div>',
            unsafe_allow_html=True,
        )

with col3:
    muscle_delta = summary.get("skeletal_muscle_delta")
    muscle_start = summary.get("skeletal_muscle_start")
    muscle_end = summary.get("skeletal_muscle_end")
    muscle_monthly = summary.get("skeletal_muscle_monthly")
    muscle_pct = summary.get("skeletal_muscle_pct")

    delta_color = "#1f77b4"

    if muscle_delta is not None:
        st.markdown(
            f"""
        <div class="metric-card" style="border-left: 4px solid {delta_color};">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">💪 MUSCULAIRE</div>
            <div class="metric-value" style="color: {delta_color};">{muscle_delta:+.1f}</div>
            <div class="metric-label">kg</div>
            {"<div class='sub-metric'>🔄 " + f"{muscle_start:.1f} → {muscle_end:.1f} kg</div>" if muscle_start and muscle_end else ""}
            {"<div class='sub-metric'>📈 " + f"{muscle_monthly:+.2f} kg/mois</div>" if muscle_monthly else ""}
            {"<div class='sub-metric'>📊 " + f"{muscle_pct:+.1f}%</div>" if muscle_pct else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div style="color: #999;">Pas de données</div></div>',
            unsafe_allow_html=True,
        )

with col4:
    avg_cal = summary.get("avg_daily_calories")
    min_cal = summary.get("min_daily_calories")
    max_cal = summary.get("max_daily_calories")

    if avg_cal is not None:
        st.markdown(
            f"""
        <div class="metric-card" style="border-left: 4px solid #667eea;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">🍽️ CALORIES</div>
            <div class="metric-value" style="color: #667eea;">{avg_cal:.0f}</div>
            <div class="metric-label">kcal/jour</div>
            {"<div class='sub-metric'>📉 Min: " + f"{min_cal:.0f} kcal</div>" if min_cal else ""}
            {"<div class='sub-metric'>📈 Max: " + f"{max_cal:.0f} kcal</div>" if max_cal else ""}
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="metric-card"><div style="color: #999;">Pas de données</div></div>',
            unsafe_allow_html=True,
        )

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
    st.markdown("---")
    st.markdown("### 📸 Galerie photos")

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

    # Filtrer les photos par période de la phase
    phase_photos = {}
    first_photo_after = {}

    for tag, tag_photos in photos_by_tag.items():
        phase_photos[tag] = []
        photos_after = []

        for date, img_path in tag_photos.items():
            # Convertir YYYY-MM-DD en date
            try:
                photo_date = datetime.strptime(date, "%Y-%m-%d")
                # Vérifier si dans la période de la phase
                if phase.start <= photo_date <= phase.end:
                    phase_photos[tag].append((date, img_path))
                # Vérifier si c'est après la fin de la phase
                elif photo_date > phase.end:
                    photos_after.append((date, img_path))
            except (ValueError, TypeError):
                continue

        # Trier par date décroissante (plus récentes en premier)
        phase_photos[tag] = sorted(phase_photos[tag], key=lambda x: x[0], reverse=True)

        # Trouver la première photo après la phase
        if photos_after:
            # Trier les photos après par date
            photos_after.sort(key=lambda x: x[0])
            # Prendre la première (la plus proche de la fin de phase)
            first_photo_after[tag] = photos_after[0]

    # Afficher chaque tag sur une ligne dans l'ordre spécifié
    tag_order = ["face", "profil", "dos", "bras", "epaule"]
    for tag in tag_order:
        # Vérifier s'il y a des photos pour ce tag (dans la phase ou juste après)
        has_phase_photos = tag in phase_photos and phase_photos[tag]
        has_after_photo = tag in first_photo_after

        if has_phase_photos or has_after_photo:
            tag_style = tag_colors.get(tag, tag_colors["face"])
            st.markdown(
                f"""
            <div style="margin: 20px 0 10px 0; padding: 8px 15px; background: {tag_style['rgba']}, 0.15); border-left: 4px solid {tag_style['color']}; border-radius: 8px;">
                <span style="font-size: 16px; font-weight: bold; color: {tag_style['color']};">📷 {tag.upper()}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

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

                for idx, (date, img_path) in enumerate(photos_to_display):
                    if idx < 5:  # Limiter à 5 photos
                        with cols[idx]:
                            # Charger et encoder l'image
                            img = load_image(img_path, blur=confidential)
                            buffered = BytesIO()
                            img.save(buffered, format="JPEG")
                            img_base64 = base64.b64encode(buffered.getvalue()).decode()

                            # Convertir YYYY-MM-DD en "JJ Mois Année"
                            date_obj = datetime.strptime(date, "%Y-%m-%d")
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
                            date_display = (
                                f"{date_obj.day} {month_names[date_obj.month]} {date_obj.year}"
                            )

                            st.markdown(
                                f"""
                                <div style='margin: 5px;'>
                                    <div style='
                                        background: {tag_style["rgba"]}, 0.08);
                                        border-radius: 12px;
                                        padding: 12px;
                                        border: 2px solid {tag_style["rgba"]}, 0.3);
                                        transition: all 0.3s ease;
                                    ' onmouseover="this.style.boxShadow='0 6px 12px {tag_style["rgba"]}, 0.4)'; this.style.transform='translateY(-3px)'" onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)'; this.style.transform='translateY(0)'">
                                        <div style='text-align: center; padding: 8px; background: {tag_style["gradient"]}; border-radius: 8px 8px 0 0; margin: -12px -12px 8px -12px;'>
                                            <span style='color: white; font-weight: bold; font-size: 14px;'>{date_display}</span>
                                        </div>
                                        <div style='
                                            width: 100%;
                                            aspect-ratio: 3/4;
                                            height: {img_height}px;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            overflow: hidden;
                                            border-radius: 8px;
                                            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                                        '>
                                            <img src='data:image/jpeg;base64,{img_base64}' style='
                                                width: auto;
                                                height: 100%;
                                                object-fit: cover;
                                                border-radius: 8px;
                                            '>
                                        </div>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
