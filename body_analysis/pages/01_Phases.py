from __future__ import annotations

import os
import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import load_all
from body_analysis.phases import load_phases, summarize_phase

st.set_page_config(page_title="Phases", page_icon="🗓️", layout="wide")

st.title("Phases — Timeline et détails")

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
)
DATA_DIR = os.path.abspath(DATA_DIR)
weight_data, daily_cal_data = load_all(DATA_DIR)

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
st.subheader(phase.name)

# Summary
summary = summarize_phase(weight_data, daily_cal_data, phase)

# Métriques organisées par catégorie
st.markdown("### 📊 Métriques de la phase")

# Poids
st.markdown("#### ⚖️ Poids")
col1, col2, col3 = st.columns(3)
with col1:
    weight_delta = summary.get("weight_delta")
    st.metric(
        "Variation totale",
        f"{weight_delta:.2f} kg" if weight_delta is not None else "N/A",
    )
with col2:
    weight_monthly = summary.get("weight_monthly")
    st.metric(
        "Variation / mois",
        f"{weight_monthly:.2f} kg/mois" if weight_monthly is not None else "N/A",
    )
with col3:
    weight_pct = summary.get("weight_pct")
    st.metric("Changement", f"{weight_pct:.1f}%" if weight_pct is not None else "N/A")

st.divider()

# Masse grasse
st.markdown("#### 🟠 Masse grasse")
col1, col2, col3 = st.columns(3)
with col1:
    bf_delta = summary.get("body_fat_delta")
    st.metric("Variation totale", f"{bf_delta:.2f}%" if bf_delta is not None else "N/A")
with col2:
    bf_monthly = summary.get("body_fat_monthly")
    st.metric(
        "Variation / mois",
        f"{bf_monthly:.2f}%/mois" if bf_monthly is not None else "N/A",
    )
with col3:
    bf_pct = summary.get("body_fat_pct")
    st.metric("Changement", f"{bf_pct:.1f}%" if bf_pct is not None else "N/A")

st.divider()

# Masse musculaire
st.markdown("#### 💪 Masse musculaire")
col1, col2, col3 = st.columns(3)
with col1:
    muscle_delta = summary.get("skeletal_muscle_delta")
    st.metric(
        "Variation totale",
        f"{muscle_delta:.2f} kg" if muscle_delta is not None else "N/A",
    )
with col2:
    muscle_monthly = summary.get("skeletal_muscle_monthly")
    st.metric(
        "Variation / mois",
        f"{muscle_monthly:.2f} kg/mois" if muscle_monthly is not None else "N/A",
    )
with col3:
    muscle_pct = summary.get("skeletal_muscle_pct")
    st.metric("Changement", f"{muscle_pct:.1f}%" if muscle_pct is not None else "N/A")

st.divider()

# Calories
st.markdown("#### 🍽️ Apport calorique")
avg_cal = summary.get("avg_daily_calories")
st.metric(
    "Moyenne journalière", f"{avg_cal:.0f} kcal" if avg_cal is not None else "N/A"
)

st.divider()

# Charts for the selected phase
mask_w = (weight_df["date"] >= phase.start) & (weight_df["date"] <= phase.end)
mask_c = (daily_cal_df["date"] >= phase.start) & (daily_cal_df["date"] <= phase.end)

w = weight_df.loc[mask_w]
cals = daily_cal_df.loc[mask_c]

# Poids et Calories côte à côte
col1, col2 = st.columns(2)
with col1:
    if not w.empty and "weight" in w.columns:
        st.subheader("Poids")
        w_clean = w.dropna(subset=["weight"])
        if not w_clean.empty:
            x_domain = [w_clean["date"].min(), w_clean["date"].max()]
            chart = (
                alt.Chart(w)
                .mark_line(color="#1f77b4", point=alt.OverlayMarkDef(size=30))
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y=alt.Y("weight:Q", scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("weight:Q", title="Poids (kg)", format=".2f"),
                    ],
                )
            )
            st.altair_chart(chart.properties(height=300), use_container_width=True)

with col2:
    st.subheader("Calories par jour")
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
            st.altair_chart(cal_chart.properties(height=300), use_container_width=True)

# Composition (pleine largeur)
if not w.empty:
    metrics_cols = [c for c in ["body_fat", "skeletal_muscle_mass"] if c in w.columns]
    if metrics_cols:
        st.subheader("Composition")
        melt = w.melt(
            id_vars=["date"],
            value_vars=metrics_cols,
            var_name="metric",
            value_name="value",
        )
        melt_clean = melt.dropna(subset=["value"])
        if not melt_clean.empty:
            x_domain = [melt_clean["date"].min(), melt_clean["date"].max()]
            chart2 = (
                alt.Chart(melt)
                .mark_line(point=alt.OverlayMarkDef(size=30))
                .encode(
                    x=alt.X("date:T", scale=alt.Scale(domain=x_domain)),
                    y=alt.Y("value:Q", scale=alt.Scale(zero=False)),
                    color=alt.Color(
                        "metric:N",
                        legend=alt.Legend(orient="bottom"),
                        scale=alt.Scale(
                            domain=["body_fat", "skeletal_muscle_mass"],
                            range=["#FF8C00", "#4ECDC4"],
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("value:Q", title="Valeur", format=".2f"),
                        alt.Tooltip("metric:N", title="Métrique"),
                    ],
                )
            )
            st.altair_chart(chart2.properties(height=300), use_container_width=True)
