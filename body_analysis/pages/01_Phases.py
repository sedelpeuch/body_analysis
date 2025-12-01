from __future__ import annotations

import os
import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import load_all
from body_analysis.phases import load_phases, summarize_phase

st.set_page_config(page_title="Phases", page_icon="🗓️", layout="wide")

st.title("Phases — Timeline et détails")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
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

phase_labels = [p.label for p in phases]
sel = st.selectbox("Sélectionner une phase", phase_labels)
phase = next(p for p in phases if p.label == sel)

st.subheader(phase.label)

# Summary
summary = summarize_phase(weight_data, daily_cal_data, phase)
left, right = st.columns(2)
with left:
    st.metric("Poids Δ (kg)", summary.get("weight_delta"))
    st.metric("Masse grasse Δ (%)", summary.get("body_fat_delta"))
with right:
    st.metric("Masse musculaire Δ (kg)", summary.get("skeletal_muscle_delta"))
    st.metric("Calories moyennes", summary.get("avg_daily_calories"))

# Charts for the selected phase
mask_w = (weight_df["date"] >= phase.start) & (weight_df["date"] <= phase.end)
mask_c = (daily_cal_df["date"] >= phase.start) & (daily_cal_df["date"] <= phase.end)

w = weight_df.loc[mask_w]
cals = daily_cal_df.loc[mask_c]

col1, col2 = st.columns(2)
with col1:
    if not w.empty and "weight" in w.columns:
        st.subheader("Poids")
        chart = alt.Chart(w).mark_line(color="#1f77b4").encode(x="date:T", y="weight:Q")
        st.altair_chart(chart.properties(height=300), use_container_width=True)
    if not w.empty:
        metrics_cols = [c for c in ["body_fat", "skeletal_muscle_mass"] if c in w.columns]
        if metrics_cols:
            st.subheader("Composition")
            melt = w.melt(id_vars=["date"], value_vars=metrics_cols, var_name="metric", value_name="value")
            chart2 = alt.Chart(melt).mark_line().encode(x="date:T", y="value:Q", color="metric:N")
            st.altair_chart(chart2.properties(height=300), use_container_width=True)

with col2:
    st.subheader("Calories par jour")
    if not cals.empty:
        cal_chart = alt.Chart(cals).mark_bar(color="#2ca02c").encode(x="date:T", y="calories:Q")
        st.altair_chart(cal_chart.properties(height=300), use_container_width=True)
