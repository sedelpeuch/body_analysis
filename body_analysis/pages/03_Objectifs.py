from __future__ import annotations

import os
from datetime import datetime
import math

import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import load_all
from body_analysis.phases import load_phases, summarize_phase

st.set_page_config(page_title="Objectifs", page_icon="🎯", layout="wide")

# CSS personnalisé pour moderniser l'interface
st.markdown(
    """
<style>
    .success-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .progress-ring {
        transform: rotate(-90deg);
    }
    .phase-card {
        background: rgba(102, 126, 234, 0.05);
        padding: 25px;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 20px 0;
        box-shadow: 0 2px 4px rgba(102, 126, 234, 0.1);
    }
    .badge-success {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    .badge-warning {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
        padding: 5px 15px;
        border-radius: 20px;
        color: white;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🎯 Objectifs — Bilan et analyse")

# Load data
ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR = "/app/data"
else:
    DATA_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data"
        )
    )
weight_data, daily_cal_data = load_all(DATA_DIR)

# Convert to DataFrames
weight_df = pd.DataFrame(weight_data)
daily_cal_df = pd.DataFrame(daily_cal_data)

# Load phases
fallback = None
if weight_data:
    dates = [r["date"] for r in weight_data]
    fallback = (min(dates), max(dates))
phases = load_phases(fallback_range=fallback)

if not phases:
    st.info("Aucune phase définie.")
    st.stop()

# Filtrer les phases avec objectifs
phases_with_objectives = [
    p for p in phases if hasattr(p, "objectives") and p.objectives
]

if not phases_with_objectives:
    st.info(
        "Aucune phase avec objectifs définis. Ajoutez des objectifs dans le fichier `phases.json` :\n\n"
        "```json\n"
        "{\n"
        '  "name": "Phase 1",\n'
        '  "start": "2025-01-01",\n'
        '  "end": "2025-02-01",\n'
        '  "type": "diet",\n'
        '  "objectives": {\n'
        '    "weight_target": 75.0,\n'
        '    "body_fat_target": 15.0,\n'
        '    "muscle_target": 32.0,\n'
        '    "calories_target": 1800\n'
        "  }\n"
        "}\n"
        "```"
    )
    st.stop()

# === Vue d'ensemble ===
st.header("📊 Vue d'ensemble")

overview_data = []
for phase in phases_with_objectives:
    summary = summarize_phase(weight_data, daily_cal_data, phase)
    obj = phase.objectives

    # Calculer les écarts
    weight_achieved = summary.get("weight_end")
    weight_target = obj.get("weight_target")
    weight_gap = (
        (weight_achieved - weight_target)
        if (weight_achieved and weight_target)
        else None
    )

    body_fat_achieved = summary.get("body_fat_end")
    body_fat_target = obj.get("body_fat_target")
    body_fat_gap = (
        (body_fat_achieved - body_fat_target)
        if (body_fat_achieved and body_fat_target)
        else None
    )

    muscle_achieved = summary.get("skeletal_muscle_end")
    muscle_target = obj.get("muscle_target")
    muscle_gap = (
        (muscle_achieved - muscle_target)
        if (muscle_achieved and muscle_target)
        else None
    )

    calories_achieved = summary.get("avg_daily_calories")
    calories_target = obj.get("calories_target")
    calories_gap = (
        (calories_achieved - calories_target)
        if (calories_achieved and calories_target)
        else None
    )

    overview_data.append(
        {
            "Phase": phase.name,
            "Type": phase.type,
            "Poids cible": weight_target,
            "Poids atteint": weight_achieved,
            "Écart poids": weight_gap,
            "MG cible": body_fat_target,
            "MG atteinte": body_fat_achieved,
            "Écart MG": body_fat_gap,
            "Muscle cible": muscle_target,
            "Muscle atteint": muscle_achieved,
            "Écart muscle": muscle_gap,
            "Cal cible": calories_target,
            "Cal atteintes": calories_achieved,
            "Écart cal": calories_gap,
        }
    )

overview_df = pd.DataFrame(overview_data)


# Fonction pour créer un cercle de progression SVG
def create_progress_circle(percentage, size=120, stroke_width=10):
    radius = (size - stroke_width) / 2
    circumference = 2 * math.pi * radius
    offset = circumference - (percentage / 100) * circumference

    # Couleur basée sur le pourcentage
    if percentage >= 80:
        color = "#38ef7d"
    elif percentage >= 60:
        color = "#4facfe"
    else:
        color = "#ff6b6b"

    svg = f"""
    <svg width="{size}" height="{size}">
        <circle cx="{size/2}" cy="{size/2}" r="{radius}" 
                fill="none" stroke="#e0e0e0" stroke-width="{stroke_width}"/>
        <circle cx="{size/2}" cy="{size/2}" r="{radius}" 
                fill="none" stroke="{color}" stroke-width="{stroke_width}"
                stroke-dasharray="{circumference}" stroke-dashoffset="{offset}"
                transform="rotate(-90 {size/2} {size/2})"
                stroke-linecap="round"/>
        <text x="50%" y="50%" text-anchor="middle" dy=".3em" 
              font-size="24" font-weight="bold" fill="{color}">
            {percentage:.0f}%
        </text>
    </svg>
    """
    return svg


# Métriques globales avec cercles de progression
col1, col2, col3, col4 = st.columns(4)

with col1:
    weight_success = overview_df[
        overview_df["Écart poids"].notna() & (overview_df["Écart poids"].abs() <= 2)
    ].shape[0]
    weight_total = overview_df["Écart poids"].notna().sum()
    weight_rate = (weight_success / weight_total * 100) if weight_total > 0 else 0
    st.markdown("**⚖️ Poids**")
    st.markdown(create_progress_circle(weight_rate, 100, 8), unsafe_allow_html=True)
    st.caption(f"{weight_success}/{weight_total} objectifs atteints")

with col2:
    bf_success = overview_df[
        overview_df["Écart MG"].notna() & (overview_df["Écart MG"].abs() <= 2)
    ].shape[0]
    bf_total = overview_df["Écart MG"].notna().sum()
    bf_rate = (bf_success / bf_total * 100) if bf_total > 0 else 0
    st.markdown("**🔥 Masse grasse**")
    st.markdown(create_progress_circle(bf_rate, 100, 8), unsafe_allow_html=True)
    st.caption(f"{bf_success}/{bf_total} objectifs atteints")

with col3:
    muscle_success = overview_df[
        overview_df["Écart muscle"].notna() & (overview_df["Écart muscle"].abs() <= 1)
    ].shape[0]
    muscle_total = overview_df["Écart muscle"].notna().sum()
    muscle_rate = (muscle_success / muscle_total * 100) if muscle_total > 0 else 0
    st.markdown("**💪 Muscle**")
    st.markdown(create_progress_circle(muscle_rate, 100, 8), unsafe_allow_html=True)
    st.caption(f"{muscle_success}/{muscle_total} objectifs atteints")

with col4:
    cal_success = overview_df[
        overview_df["Écart cal"].notna() & (overview_df["Écart cal"].abs() <= 200)
    ].shape[0]
    cal_total = overview_df["Écart cal"].notna().sum()
    cal_rate = (cal_success / cal_total * 100) if cal_total > 0 else 0
    st.markdown("**🍽️ Calories**")
    st.markdown(create_progress_circle(cal_rate, 100, 8), unsafe_allow_html=True)
    st.caption(f"{cal_success}/{cal_total} objectifs atteints")

st.divider()

# === Détail par phase ===
st.header("📋 Détail par phase")

for phase in phases_with_objectives:
    summary = summarize_phase(weight_data, daily_cal_data, phase)
    obj = phase.objectives

    # Titre avec émoji selon le type
    type_emoji = {"cut": "✂️", "bulk": "💪", "maintain": "➖", "free": "🆓"}.get(
        phase.type, "📌"
    )

    # Card avec style moderne
    st.markdown(
        f"""
    <div class="phase-card">
        <h3>{type_emoji} {phase.name}</h3>
        <p>📅 {phase.start.strftime('%d/%m/%Y')} → {phase.end.strftime('%d/%m/%Y')} • {summary.get('days', 0)} jours</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # === Métriques avec badges ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("**⚖️ Poids**")
        weight_target = obj.get("weight_target")
        weight_achieved = summary.get("weight_end")
        if weight_target and weight_achieved:
            gap = weight_achieved - weight_target
            success = abs(gap) <= 2
            badge = "badge-success" if success else "badge-warning"
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(44, 160, 44, 0.1); border-radius: 10px; border: 1px solid rgba(44, 160, 44, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #2ca02c;">{weight_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {weight_target:.1f} kg</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} kg</div>
                <div class="{badge}" style="margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        elif weight_target:
            st.metric("Objectif", f"{weight_target:.1f} kg", "— kg")
        else:
            st.caption("Pas d'objectif")

    with col2:
        st.markdown("**🔥 Masse grasse**")
        bf_target = obj.get("body_fat_target")
        bf_achieved = summary.get("body_fat_end")
        if bf_target and bf_achieved:
            gap = bf_achieved - bf_target
            success = abs(gap) <= 2
            badge = "badge-success" if success else "badge-warning"
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(255, 140, 0, 0.1); border-radius: 10px; border: 1px solid rgba(255, 140, 0, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #FF8C00;">{bf_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {bf_target:.1f} %</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} %</div>
                <div class="{badge}" style="margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        elif bf_target:
            st.metric("Objectif", f"{bf_target:.1f} %", "— %")
        else:
            st.caption("Pas d'objectif")

    with col3:
        st.markdown("**💪 Masse musculaire**")
        muscle_target = obj.get("muscle_target")
        muscle_achieved = summary.get("skeletal_muscle_end")
        if muscle_target and muscle_achieved:
            gap = muscle_achieved - muscle_target
            success = abs(gap) <= 1
            badge = "badge-success" if success else "badge-warning"
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(31, 119, 180, 0.1); border-radius: 10px; border: 1px solid rgba(31, 119, 180, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #1f77b4;">{muscle_achieved:.1f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {muscle_target:.1f} kg</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.1f} kg</div>
                <div class="{badge}" style="margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        elif muscle_target:
            st.metric("Objectif", f"{muscle_target:.1f} kg", "— kg")
        else:
            st.caption("Pas d'objectif")

    with col4:
        st.markdown("**🍽️ Calories moyennes**")
        cal_target = obj.get("calories_target")
        cal_achieved = summary.get("avg_daily_calories")
        if cal_target and cal_achieved:
            gap = cal_achieved - cal_target
            success = abs(gap) <= 200
            badge = "badge-success" if success else "badge-warning"
            badge_text = "✅ Atteint" if success else "⚠️ Écart"

            st.markdown(
                f"""
            <div style="text-align: center; padding: 15px; background: rgba(102, 126, 234, 0.1); border-radius: 10px; border: 1px solid rgba(102, 126, 234, 0.3);">
                <div style="font-size: 28px; font-weight: bold; color: #667eea;">{cal_achieved:.0f}</div>
                <div style="font-size: 14px; color: #999;">Objectif: {cal_target:.0f} kcal</div>
                <div style="font-size: 16px; margin-top: 5px; color: {'#38ef7d' if success else '#ff6b6b'};">{gap:+.0f} kcal</div>
                <div class="{badge}" style="margin-top: 10px;">{badge_text}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        elif cal_target:
            st.metric("Objectif", f"{cal_target:.0f} kcal", "— kcal")
        else:
            st.caption("Pas d'objectif")

    # === Graphiques avec objectifs ===
    phase_weight = weight_df[
        (weight_df["date"] >= phase.start) & (weight_df["date"] <= phase.end)
    ].copy()

    if not phase_weight.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("")
            st.markdown(
                "<p style='text-align: center; font-weight: bold;'>Poids</p>",
                unsafe_allow_html=True,
            )
            # Ligne de données
            base = (
                alt.Chart(phase_weight)
                .mark_line(color="#2ca02c", size=2)
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("weight:Q", title=None, scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("weight:Q", title="Poids", format=".2f"),
                    ],
                )
            )

            # Ligne d'objectif et zone
            if weight_target:
                target_line = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "target": [weight_target, weight_target],
                            }
                        )
                    )
                    .mark_line(color="#667eea", strokeDash=[5, 5], size=3, opacity=0.8)
                    .encode(
                        x="date:T",
                        y=alt.Y("target:Q", title=None),
                    )
                )

                # Zone autour de l'objectif (±2kg)
                zone = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "lower": [weight_target - 2, weight_target - 2],
                                "upper": [weight_target + 2, weight_target + 2],
                            }
                        )
                    )
                    .mark_area(opacity=0.15, color="#667eea")
                    .encode(x="date:T", y="lower:Q", y2="upper:Q")
                )

                chart = zone + base + target_line
            else:
                chart = base

            st.altair_chart(chart.properties(height=200), use_container_width=True)

        with col2:
            st.markdown("")
            st.markdown(
                "<p style='text-align: center; font-weight: bold;'>Masse grasse</p>",
                unsafe_allow_html=True,
            )
            # Ligne de données
            base = (
                alt.Chart(phase_weight)
                .mark_line(color="#FF8C00", size=2)
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y("body_fat:Q", title=None, scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip("body_fat:Q", title="Masse grasse", format=".2f"),
                    ],
                )
            )

            # Ligne d'objectif et zone
            if bf_target:
                target_line = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "target": [bf_target, bf_target],
                            }
                        )
                    )
                    .mark_line(color="#ff6b6b", strokeDash=[5, 5], size=3, opacity=0.8)
                    .encode(
                        x="date:T",
                        y=alt.Y("target:Q", title=None),
                    )
                )

                # Zone autour de l'objectif (±2%)
                zone = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "lower": [bf_target - 2, bf_target - 2],
                                "upper": [bf_target + 2, bf_target + 2],
                            }
                        )
                    )
                    .mark_area(opacity=0.15, color="#ff6b6b")
                    .encode(x="date:T", y="lower:Q", y2="upper:Q")
                )

                chart = zone + base + target_line
            else:
                chart = base

            st.altair_chart(chart.properties(height=200), use_container_width=True)

        with col3:
            st.markdown("")
            st.markdown(
                "<p style='text-align: center; font-weight: bold;'>Masse musculaire</p>",
                unsafe_allow_html=True,
            )
            # Ligne de données
            base = (
                alt.Chart(phase_weight)
                .mark_line(color="#1f77b4", size=2)
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y(
                        "skeletal_muscle_mass:Q",
                        title=None,
                        scale=alt.Scale(zero=False),
                    ),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                        alt.Tooltip(
                            "skeletal_muscle_mass:Q", title="Muscle", format=".2f"
                        ),
                    ],
                )
            )

            # Ligne d'objectif et zone
            if muscle_target:
                target_line = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "target": [muscle_target, muscle_target],
                            }
                        )
                    )
                    .mark_line(color="#4facfe", strokeDash=[5, 5], size=3, opacity=0.8)
                    .encode(
                        x="date:T",
                        y=alt.Y("target:Q", title=None),
                    )
                )

                # Zone autour de l'objectif (±1kg)
                zone = (
                    alt.Chart(
                        pd.DataFrame(
                            {
                                "date": [phase.start, phase.end],
                                "lower": [muscle_target - 1, muscle_target - 1],
                                "upper": [muscle_target + 1, muscle_target + 1],
                            }
                        )
                    )
                    .mark_area(opacity=0.15, color="#4facfe")
                    .encode(x="date:T", y="lower:Q", y2="upper:Q")
                )

                chart = zone + base + target_line
            else:
                chart = base

            st.altair_chart(chart.properties(height=200), use_container_width=True)

    st.divider()
