from __future__ import annotations

import os
import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import load_all
from body_analysis.phases import load_phases, phase_boundaries, summarize_phase

st.set_page_config(page_title="Body Analysis", page_icon="📈", layout="wide")

st.title("Body Analysis — Tableau de bord")

# Load data
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
weight_data, daily_cal_data = load_all(DATA_DIR)

# Convert to DataFrames for Altair
weight_df = pd.DataFrame(weight_data)
daily_cal_df = pd.DataFrame(daily_cal_data)

# Load phases (fallback spanning the data)
fallback = None
if weight_data:
    dates = [r["date"] for r in weight_data]
    fallback = (min(dates), max(dates))
phases = load_phases(fallback_range=fallback)

# Phase summaries - Timeline (déplacé en premier)
st.subheader("Récapitulatif des phases")
if phases:
    summaries = [summarize_phase(weight_data, daily_cal_data, p) for p in phases]

    # Style CSS pour la timeline
    st.markdown(
        """
    <style>
    .timeline {
        position: relative;
        padding: 20px 0;
    }
    .timeline-item {
        position: relative;
        padding-left: 40px;
        padding-bottom: 30px;
        border-left: 2px solid #e0e0e0;
    }
    .timeline-item:last-child {
        border-left: none;
    }
    .timeline-dot {
        display: none;
    }
    .timeline-content {
        background-color: rgba(255, 255, 255, 0.03);
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #666;
        color: #ffffff;
    }
    .timeline-content strong {
        color: #ffffff;
        font-size: 1.6em;
    }
    .timeline-content small {
        color: #cccccc;
        font-size: 1.05em;
    }
    .timeline-metrics {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-top: 15px;
        color: #ffffff;
    }
    .metric-box {
        text-align: left;
    }
    .metric-label {
        font-size: 1em;
        color: #aaaaaa;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 1.4em;
        font-weight: bold;
        color: #ffffff;
    }
    .metric-range {
        font-size: 0.85em;
        color: #999999;
        margin-top: 3px;
    }
    .phase-bulk { border-left-color: #2196F3; }
    .phase-cut { border-left-color: #FF9800; }
    .phase-maintain { border-left-color: #4CAF50; }
    .phase-free { border-left-color: #9E9E9E; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="timeline">', unsafe_allow_html=True)

    for summary in summaries:
        # Extraire le nom et le type de phase
        label_parts = summary["label"].split("(")
        phase_name = label_parts[0].strip()
        phase_type = label_parts[1].strip(")") if len(label_parts) > 1 else "free"
        phase_class = f"phase-{phase_type}"

        # Emoji selon le type
        if phase_type == "bulk":
            emoji = "📈"
        elif phase_type == "cut":
            emoji = "📉"
        elif phase_type == "maintain":
            emoji = "➡️"
        else:
            emoji = "🆓"

        # Période
        start_str = summary["start"].strftime("%d/%m/%Y")
        end_str = summary["end"].strftime("%d/%m/%Y")
        
        # Durée en format lisible
        total_days = summary["days"]
        years = total_days // 365
        remaining = total_days % 365
        months = remaining // 30
        days = remaining % 30
        
        duration_parts = []
        if years > 0:
            duration_parts.append(f"{years} an{'s' if years > 1 else ''}")
        if months > 0:
            duration_parts.append(f"{months} mois")
        if days > 0 or not duration_parts:
            duration_parts.append(f"{days} jour{'s' if days > 1 else ''}")
        duration_str = " ".join(duration_parts)

        # Métriques
        weight_delta = summary.get("weight_delta")
        weight_start = summary.get("weight_start")
        weight_end = summary.get("weight_end")
        weight_str = f"{weight_delta:+.1f} kg" if weight_delta is not None else "N/A"
        weight_range = f"{weight_start:.1f} → {weight_end:.1f} kg" if weight_start is not None and weight_end is not None else ""

        bf_delta = summary.get("body_fat_delta")
        bf_start = summary.get("body_fat_start")
        bf_end = summary.get("body_fat_end")
        bf_str = f"{bf_delta:+.1f}%" if bf_delta is not None else "N/A"
        bf_range = f"{bf_start:.1f} → {bf_end:.1f}%" if bf_start is not None and bf_end is not None else ""

        muscle_delta = summary.get("skeletal_muscle_delta")
        muscle_start = summary.get("skeletal_muscle_start")
        muscle_end = summary.get("skeletal_muscle_end")
        muscle_str = f"{muscle_delta:+.1f} kg" if muscle_delta is not None else "N/A"
        muscle_range = f"{muscle_start:.1f} → {muscle_end:.1f} kg" if muscle_start is not None and muscle_end is not None else ""

        avg_cal = summary.get("avg_daily_calories")
        cal_str = f"{avg_cal:.0f} kcal" if avg_cal is not None else "N/A"

        st.markdown(
            f"""
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content {phase_class}">
                <strong>{emoji} {phase_name}</strong><br>
                <small>📅 {start_str} → {end_str} ({duration_str})</small>
                <div class="timeline-metrics">
                    <div class="metric-box">
                        <div class="metric-label">Poids</div>
                        <div class="metric-value">{weight_str}</div>
                        <div class="metric-range">{weight_range}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Masse grasse</div>
                        <div class="metric-value">{bf_str}</div>
                        <div class="metric-range">{bf_range}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Masse musculaire</div>
                        <div class="metric-value">{muscle_str}</div>
                        <div class="metric-range">{muscle_range}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Calories moy.</div>
                        <div class="metric-value">{cal_str}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info(
        "Aucune phase définie. Ajoutez un fichier data/phases.json pour tracer les changements de phase."
    )

# Charts
st.subheader("Évolution du poids")
if weight_df.empty or "weight" not in weight_df.columns:
    st.info("Aucune donnée de poids disponible.")
else:
    base = alt.Chart(weight_df).encode(x="date:T")
    line = base.mark_line(color="#1f77b4").encode(
        y=alt.Y("weight:Q", title="Poids (kg)")
    )
    data_range = (weight_df["date"].min(), weight_df["date"].max())
    boundaries = phase_boundaries(phases, data_range)
    rules = (
        alt.Chart(boundaries)
        .mark_rule(color="red", strokeDash=[4, 4])
        .encode(x="date:T")
        if phases and not boundaries.empty
        else None
    )
    chart = line if rules is None else line + rules
    st.altair_chart(chart.properties(height=400), use_container_width=True)

st.subheader("Masse grasse et musculaire")
if not weight_df.empty:
    metrics_cols = [
        c for c in ["body_fat", "skeletal_muscle_mass"] if c in weight_df.columns
    ]
    if metrics_cols:
        melt = weight_df.melt(
            id_vars=["date"],
            value_vars=metrics_cols,
            var_name="metric",
            value_name="value",
        )
        # Filtrer les valeurs NaN pour ne garder que les données valides
        melt = melt.dropna(subset=["value"])
        chart2 = (
            alt.Chart(melt)
            .mark_line()
            .encode(
                x="date:T",
                y="value:Q",
                color=alt.Color("metric:N", 
                    legend=alt.Legend(orient="bottom"),
                    scale=alt.Scale(
                        domain=["body_fat", "skeletal_muscle_mass"],
                        range=["#FF8C00", "#4ECDC4"]
                    )
                ),
            )
            .properties(height=400)
        )
        if phases and not melt.empty:
            data_range = (melt["date"].min(), melt["date"].max())
            boundaries = phase_boundaries(phases, data_range)
            if not boundaries.empty:
                chart2 = chart2 + alt.Chart(boundaries).mark_rule(
                    color="red", strokeDash=[4, 4]
                ).encode(x="date:T")
        st.altair_chart(chart2, use_container_width=True)

st.subheader("Apport calorique quotidien")
if daily_cal_df.empty:
    st.info("Aucune donnée d'alimentation disponible.")
else:
    cal_chart = (
        alt.Chart(daily_cal_df)
        .mark_bar(color="#2ca02c")
        .encode(x="date:T", y=alt.Y("calories:Q", title="Calories"))
    )
    if phases:
        data_range = (daily_cal_df["date"].min(), daily_cal_df["date"].max())
        boundaries = phase_boundaries(phases, data_range)
        if not boundaries.empty:
            cal_chart = cal_chart + alt.Chart(boundaries).mark_rule(
                color="red", strokeDash=[4, 4]
            ).encode(x="date:T")
    st.altair_chart(cal_chart.properties(height=400), use_container_width=True)
