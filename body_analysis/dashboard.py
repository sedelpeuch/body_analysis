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
ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR = "/app/data"
else:
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
            EMOJI = "📈"
        elif phase_type == "cut":
            EMOJI = "📉"
        elif phase_type == "maintain":
            EMOJI = "➡️"
        else:
            EMOJI = "🆓"

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
        weight_range = (
            f"{weight_start:.1f} → {weight_end:.1f} kg"
            if weight_start is not None and weight_end is not None
            else ""
        )

        bf_delta = summary.get("body_fat_delta")
        bf_start = summary.get("body_fat_start")
        bf_end = summary.get("body_fat_end")
        bf_str = f"{bf_delta:+.1f}%" if bf_delta is not None else "N/A"
        bf_range = (
            f"{bf_start:.1f} → {bf_end:.1f}%"
            if bf_start is not None and bf_end is not None
            else ""
        )

        muscle_delta = summary.get("skeletal_muscle_delta")
        muscle_start = summary.get("skeletal_muscle_start")
        muscle_end = summary.get("skeletal_muscle_end")
        muscle_str = f"{muscle_delta:+.1f} kg" if muscle_delta is not None else "N/A"
        muscle_range = (
            f"{muscle_start:.1f} → {muscle_end:.1f} kg"
            if muscle_start is not None and muscle_end is not None
            else ""
        )

        avg_cal = summary.get("avg_daily_calories")
        cal_str = f"{avg_cal:.0f} kcal" if avg_cal is not None else "N/A"

        st.markdown(
            f"""
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content {phase_class}">
                <strong>{EMOJI} {phase_name}</strong><br>
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

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info(
        "Aucune phase définie. Ajoutez un fichier data/phases.json pour tracer les changements de phase."
    )

# === Sélecteur d'années pour les graphiques ===
st.subheader("Filtrer par année")
import datetime


def get_years(df, date_col):
    if df.empty or date_col not in df.columns:
        return []
    return sorted(set(df[date_col].dt.year))


years_weight = get_years(weight_df, "date")
years_cal = get_years(daily_cal_df, "date")
years = [y for y in sorted(set(years_weight + years_cal), reverse=True) if y >= 2024]
current_year = datetime.datetime.now().year

if years:
    default_idx = 0 if current_year not in years else years.index(current_year)
    year_labels = ["Tout"] + [str(y) for y in years]
    selected = st.radio(
        "Année à afficher",
        year_labels,
        index=default_idx + 1 if current_year in years else 0,
        horizontal=True,
    )
else:
    selected = "Tout"

# Légende des couleurs de phases
phase_legend = {
    "bulk": ("Prise de masse", "#2196F3", "📈"),
    "cut": ("Sèche", "#FF9800", "📉"),
    "maintain": ("Maintien", "#4CAF50", "➡️"),
    "free": ("Libre", "#9E9E9E", "🆓"),
}
legend_html = ""
for key, (label, color, emoji) in phase_legend.items():
    legend_html += f"<span style='display:inline-block; margin-right:18px;'><span style='background:{color}; border-radius:3px; padding:3px 10px; color:#fff;'>{emoji}</span> <span style='color:{color}; font-weight:bold;'>{label}</span></span>"
legend_html += "</div>"
st.markdown(legend_html, unsafe_allow_html=True)


def filter_year(df, date_col, year):
    if df.empty or date_col not in df.columns:
        return df
    if year == "Tout":
        return df
    return df[df[date_col].dt.year == int(year)]


def filter_phases(phases, year):
    if not phases or year == "Tout":
        return phases
    filtered = []
    for p in phases:
        start_year = pd.Timestamp(p.start).year
        end_year = pd.Timestamp(p.end).year
        if int(year) >= start_year and int(year) <= end_year:
            start = max(pd.Timestamp(p.start), pd.Timestamp(f"{year}-01-01"))
            end = min(pd.Timestamp(p.end), pd.Timestamp(f"{year}-12-31"))
            filtered.append(
                type("Phase", (), {"start": start, "end": end, "type": p.type})()
            )
    return filtered


# === Graphique Poids ===
from pandas import Timestamp

phase_colors = {
    "bulk": "#2196F3",
    "cut": "#FF9800",
    "maintain": "#4CAF50",
    "free": "#9E9E9E",
}
phase_opacity = 0.15
phase_rects = None
filtered_phases = filter_phases(phases, selected)
if filtered_phases:
    rect_data = []
    for p in filtered_phases:
        color = phase_colors.get(p.type, "#CCCCCC")
        rect_data.append(
            {
                "start": Timestamp(p.start),
                "end": Timestamp(p.end),
                "type": p.type,
                "color": color,
            }
        )
    rect_df = pd.DataFrame(rect_data)
    phase_rects = (
        alt.Chart(rect_df)
        .mark_rect(opacity=phase_opacity)
        .encode(
            x=alt.X("start:T", title=None),
            x2="end:T",
            color=alt.Color(
                "type:N",
                scale=alt.Scale(
                    domain=list(phase_colors.keys()), range=list(phase_colors.values())
                ),
                legend=None,
            ),
        )
    )

st.subheader("Évolution du poids")
filtered_weight_df = filter_year(weight_df, "date", selected)
if filtered_weight_df.empty or "weight" not in filtered_weight_df.columns:
    st.info("Aucune donnée de poids disponible.")
else:
    base = alt.Chart(filtered_weight_df).encode(
        x=alt.X("date:T", axis=alt.Axis(format="%m/%y", title="Mois/Année"))
    )
    y_min = filtered_weight_df["weight"].min()
    y_max = filtered_weight_df["weight"].max()
    line = base.mark_line(color="#1f77b4").encode(
        y=alt.Y("weight:Q", title="Poids (kg)", scale=alt.Scale(domain=[y_min, y_max]))
    )
    chart = line
    if phase_rects is not None:
        chart = phase_rects + chart
    st.altair_chart(chart.properties(height=400), use_container_width=True)

# === Graphique Masse grasse et musculaire ===
phase_rects2 = None
filtered_phases2 = filter_phases(phases, selected)
if filtered_phases2:
    rect_data2 = []
    for p in filtered_phases2:
        color = phase_colors.get(p.type, "#CCCCCC")
        rect_data2.append(
            {
                "start": Timestamp(p.start),
                "end": Timestamp(p.end),
                "type": p.type,
                "color": color,
            }
        )
    rect_df2 = pd.DataFrame(rect_data2)
    phase_rects2 = (
        alt.Chart(rect_df2)
        .mark_rect(opacity=phase_opacity)
        .encode(
            x=alt.X("start:T", title=None),
            x2="end:T",
            color=alt.Color(
                "type:N",
                scale=alt.Scale(
                    domain=list(phase_colors.keys()), range=list(phase_colors.values())
                ),
                legend=None,
            ),
        )
    )

st.subheader("Masse grasse et musculaire")
filtered_metrics_df = filter_year(weight_df, "date", selected)
if not filtered_metrics_df.empty:
    metrics_cols = [
        c
        for c in ["body_fat", "skeletal_muscle_mass"]
        if c in filtered_metrics_df.columns
    ]
    if metrics_cols:
        melt = filtered_metrics_df.melt(
            id_vars=["date"],
            value_vars=metrics_cols,
            var_name="metric",
            value_name="value",
        )
        melt = melt.dropna(subset=["value"])
        y_min = melt["value"].min()
        y_max = melt["value"].max()
        chart2 = (
            alt.Chart(melt)
            .mark_line()
            .encode(
                x=alt.X("date:T", axis=alt.Axis(format="%m/%y", title="Mois/Année")),
                y=alt.Y("value:Q", scale=alt.Scale(domain=[y_min, y_max])),
                color=alt.Color(
                    "metric:N",
                    legend=alt.Legend(orient="bottom"),
                    scale=alt.Scale(
                        domain=["body_fat", "skeletal_muscle_mass"],
                        range=["#FF8C00", "#4ECDC4"],
                    ),
                ),
            )
            .properties(height=400)
        )
        if phase_rects2 is not None:
            chart2 = phase_rects2 + chart2
        st.altair_chart(chart2, use_container_width=True)

# === Graphique Apport calorique ===
phase_rects3 = None
filtered_phases3 = filter_phases(phases, selected)
if filtered_phases3:
    rect_data3 = []
    for p in filtered_phases3:
        color = phase_colors.get(p.type, "#CCCCCC")
        rect_data3.append(
            {
                "start": Timestamp(p.start),
                "end": Timestamp(p.end),
                "type": p.type,
                "color": color,
            }
        )
    rect_df3 = pd.DataFrame(rect_data3)
    phase_rects3 = (
        alt.Chart(rect_df3)
        .mark_rect(opacity=phase_opacity)
        .encode(
            x=alt.X("start:T", title=None),
            x2="end:T",
            color=alt.Color(
                "type:N",
                scale=alt.Scale(
                    domain=list(phase_colors.keys()), range=list(phase_colors.values())
                ),
                legend=None,
            ),
        )
    )

st.subheader("Apport calorique quotidien")
filtered_cal_df = filter_year(daily_cal_df, "date", selected)
if filtered_cal_df.empty:
    st.info("Aucune donnée d'alimentation disponible.")
else:
    cal_chart = (
        alt.Chart(filtered_cal_df)
        .mark_bar(color="#2ca02c")
        .encode(
            x=alt.X("date:T", axis=alt.Axis(format="%m/%y", title="Mois/Année")),
            y=alt.Y("calories:Q", title="Calories")
        )
    )
    if phase_rects3 is not None:
        cal_chart = phase_rects3 + cal_chart
    st.altair_chart(cal_chart.properties(height=400), use_container_width=True)


# === Formatage des abscisses pour afficher mois + année ===
def format_month_year(dt):
    if isinstance(dt, (str, int)):
        return str(dt)
    return dt.strftime("%b %Y")


# Lors de la création des graphiques Altair, appliquer le format personnalisé
# Exemple pour un graphique Altair :
# chart = alt.Chart(df).mark_line().encode(
#     x=alt.X('date:T', axis=alt.Axis(format='%b %Y', title='Mois et année')),
#     ...
# )
# Si tu utilises pandas pour préparer les labels, tu peux faire :
# df['mois_annee'] = df['date'].apply(format_month_year)
# et utiliser 'mois_annee' comme abscisse dans le graphique
