import json
import logging

import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import find_data_files, load_exercise_df

st.title("Analyse des sports")

# Charger les données d'exercice
paths = find_data_files()
if not paths.exercise_csv:
    st.warning("Aucun fichier d'exercice trouvé.")
    st.stop()

rows = load_exercise_df(paths.exercise_csv)
df = pd.DataFrame(rows)

# Dictionnaire de correspondance des sports
SPORTS_MAP = {
    0: "Marche",
    1001: "Marche",
    1002: "Course à pied",
    11007: "Vélo",
    13001: "Randonnée",
    14001: "Natation",
    15004: "Rameur",
    10025: "Poids du corps",
}

logger = logging.getLogger(__name__)


def safe_fmt(val: float | None, fmt: str, default: str = "-") -> str:
    """Format a value safely.

    Returns default if value is None or formatting fails.

    Args:
        val: Value to format (float or None).
        fmt: Format string (e.g. '.0f').
        default: Value to return if formatting fails.

    Returns:
        Formatted string or default.

    """
    if val is not None:
        try:
            return format(val, fmt)
        except (ValueError, TypeError) as exc:
            logger.warning("safe_fmt error: %s", exc)
    return default


def safe_div(val: float | None, div: float | None, fmt: str, default: str = "-") -> str:
    """Safely divide val by div and format.

    Returns default if error or missing value.

    Args:
        val: Numerator (float or None).
        div: Denominator (float or None).
        fmt: Format string (e.g. '.0f').
        default: Value to return if division/formatting fails.

    Returns:
        Formatted string or default.

    """
    if val is not None and div:
        try:
            return format(val / div, fmt)
        except (ZeroDivisionError, ValueError, TypeError) as exc:
            logger.warning("safe_div error: %s", exc)
    return default


def detect_sport(row):
    code = row.get("exercise_type")
    subset_data = row.get("subset_data")
    # Si subset_data ressemble à une liste de dicts avec 'reps', c'est musculation
    if subset_data:
        try:
            val = (
                json.loads(subset_data) if isinstance(subset_data, str) else subset_data
            )
            if (
                isinstance(val, list)
                and val
                and isinstance(val[0], dict)
                and "reps" in val[0]
            ):
                return "Musculation"
        except Exception:
            pass
    # Sinon, utiliser le mapping
    if code in SPORTS_MAP:
        return SPORTS_MAP[code]
    return str(code) if code is not None else "?"


# Ajouter une colonne avec le nom du sport
df["sport"] = df.apply(detect_sport, axis=1)


# On ne garde que les sports connus (présents dans SPORTS_MAP ou "Musculation")
known_sports = set(SPORTS_MAP.values()) | {"Musculation"}
df_known = df[df["sport"].isin(known_sports)]


# Liste unique des titres de sport + option "Tous les entraînements"
sport_titles = ["Tous les entraînements"] + sorted(df_known["sport"].unique())


# Style CSS pour les cards
st.markdown(
    """
<style>
    .sport-card {
        background: rgba(102, 126, 234, 0.05);
        padding: 18px;
        border-radius: 12px;
        border: 2px solid rgba(102, 126, 234, 0.18);
        margin: 8px 0;
        transition: all 0.3s ease;
        text-align: center;
        cursor: pointer;
        font-size: 18px;
        font-weight: 500;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.08);
    }
    .sport-card.selected {
        border-color: #667eea;
        background: rgba(102, 126, 234, 0.12);
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.18);
    }
    .sport-emoji {
        font-size: 32px;
        margin-bottom: 8px;
        display: block;
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
        font-size: 14px;
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

# Emoji par sport
SPORT_EMOJI = {
    "Marche": "🚶",
    "Course à pied": "🏃",
    "Vélo": "🚴",
    "Randonnée": "🥾",
    "Natation": "🏊",
    "Rameur": "🚣",
    "Poids du corps": "💪",
    "Musculation": "🏋️",
    "Tous les entraînements": "📊",
}

st.markdown("### Sélectionner un sport")
if "selected_sport_idx" not in st.session_state:
    st.session_state.selected_sport_idx = 0

num_sports = len(sport_titles)
cols_per_row = 3
rows = (num_sports + cols_per_row - 1) // cols_per_row

for row in range(rows):
    cols = st.columns(cols_per_row)
    for col_idx in range(cols_per_row):
        sport_idx = row * cols_per_row + col_idx
        if sport_idx < num_sports:
            sport_name = sport_titles[sport_idx]
            is_selected = st.session_state.selected_sport_idx == sport_idx
            emoji = SPORT_EMOJI.get(sport_name, "❓")

            # Utiliser st.markdown pour afficher la card, et rendre la carte cliquable via un lien
            # Carte cliquable façon Phases : st.button, emoji + nom, style natif
            with cols[col_idx]:
                label = f"{emoji}  {sport_name}"
                if st.button(
                    label,
                    key=f"sport_card_{sport_idx}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_sport_idx = sport_idx
                    st.rerun()

selected_sport = sport_titles[st.session_state.selected_sport_idx]


# Conversion de la colonne date en datetime si ce n'est pas déjà fait
if not pd.api.types.is_datetime64_any_dtype(df_known["date"]):
    df_known["date"] = pd.to_datetime(df_known["date"])

# Définir les bornes min et max pour le filtre de date
date_min = df_known["date"].min()
date_max = df_known["date"].max()


# Filtre de date simple : valeurs par défaut = min et max des données
default_start = date_min.date()
default_end = date_max.date()

col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input(
        "Date de début",
        value=default_start,
        min_value=date_min.date(),
        max_value=date_max.date(),
    )
with col_date2:
    end_date = st.date_input(
        "Date de fin",
        value=default_end,
        min_value=date_min.date(),
        max_value=date_max.date(),
    )

# Filtrer le DataFrame selon le sport et la plage de dates
if selected_sport == "Tous les entraînements":
    df_sport = df_known.copy()
else:
    df_sport = df_known[df_known["sport"] == selected_sport]

df_sport = df_sport[
    (df_sport["date"] >= pd.to_datetime(start_date))
    & (df_sport["date"] <= pd.to_datetime(end_date))
]

# --- Heatmap calendrier des entraînements ---
st.markdown("---")
st.header("Calendrier des entraînements")

# On part du DataFrame filtré (df_sport)
if not df_sport.empty and "date" in df_sport:
    df_heat = df_sport.copy()
    df_heat["date"] = pd.to_datetime(df_heat["date"])
    df_heat["date_jour"] = df_heat["date"].dt.date
    # On compte le nombre de séances par jour (sans tenir compte des heures/minutes/secondes)
    df_heatmap = df_heat.groupby("date_jour").size().reset_index(name="nb_seances")
    df_heatmap["date"] = pd.to_datetime(df_heatmap["date_jour"])
    df_heatmap["day"] = df_heatmap["date"].dt.day
    df_heatmap["month"] = df_heatmap["date"].dt.month
    df_heatmap["weekday"] = df_heatmap["date"].dt.dayofweek
    df_heatmap["week"] = df_heatmap["date"].dt.isocalendar().week

    if not df_heatmap.empty:
        heatmap = (
            alt.Chart(df_heatmap)
            .mark_rect()
            .encode(
                x=alt.X("week:O", title="Semaine", axis=alt.Axis(labelAngle=0)),
                y=alt.Y(
                    "weekday:O",
                    title="Jour",
                    axis=alt.Axis(
                        labelExpr="['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][datum.value]",
                    ),
                ),
                color=alt.Color(
                    "nb_seances:Q",
                    scale=alt.Scale(scheme="blues"),
                    legend=alt.Legend(title="Séances"),
                ),
                tooltip=[
                    alt.Tooltip("date:T", title="Date", format="%d/%m/%Y"),
                    alt.Tooltip("nb_seances:Q", title="Séances", format=".0f"),
                ],
            )
        )
        st.altair_chart(heatmap.properties(height=200), use_container_width=True)
    else:
        st.info("Aucune séance pour la période sélectionnée.")

# Statistiques générales avec cards modernes
st.markdown("---")
st.markdown("## Statistiques générales")

nb_seances = len(df_sport)
duree_totale = (
    df_sport["duration"].astype(float).sum() / 1000 / 60
    if "duration" in df_sport
    else None
)
calories_totales = (
    df_sport["calorie"].astype(float).sum() if "calorie" in df_sport else None
)
try:
    distance_totale = (
        df_sport["distance"].astype(float).sum() / 1000
        if "distance" in df_sport
        else None
    )
except ValueError:
    distance_totale = None
try:
    heart_rate_avg = (
        df_sport["heart_rate"].astype(float).sum() if "heart_rate" in df_sport else None
    )
    heart_rate_max = (
        df_sport["heart_rate_max"].astype(float).sum()
        if "heart_rate_max" in df_sport
        else None
    )
    heart_rate_min = (
        df_sport["heart_rate_min"].astype(float).sum()
        if "heart_rate_min" in df_sport
        else None
    )
except ValueError:
    heart_rate_avg = None
    heart_rate_max = None
    heart_rate_min = None


# Calcul vitesse moyenne (km/h)
vitesse_moyenne = None
if distance_totale and duree_totale and duree_totale > 0:
    vitesse_moyenne = distance_totale / (duree_totale / 60)

col1, col2, col3 = st.columns(3)
col4, col5 = st.columns(2)

with col1:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #667eea;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">⏱️ Durée totale</div>
            <div class="metric-value" style="color: #667eea;">{safe_div(duree_totale, 60, ".0f")} h</div>
            <div class='sub-metric'>⏱️ {safe_div(duree_totale, nb_seances, ".0f")} min/séance</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #FF8C00;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">🔥 Calories totales</div>
            <div class="metric-value" style="color: #FF8C00;">{safe_fmt(calories_totales, ".0f")} kcal</div>
            <div class='sub-metric'>🔥 {safe_div(calories_totales, nb_seances, ".0f")} kcal/séance</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #2ca02c;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">📏 Distance totale</div>
            <div class="metric-value" style="color: #2ca02c;">{safe_fmt(distance_totale, ".1f")} km</div>
            <div class='sub-metric'>📏 {safe_div(distance_totale, nb_seances, ".2f")} km/séance</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #e74c3c;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">❤️ Fréquence cardiaque</div>
            <div class="metric-value" style="color: #e74c3c;">{safe_div(heart_rate_avg, nb_seances, ".0f")} bpm</div>
            <div class='sub-metric'>❤️ {safe_div(heart_rate_min, nb_seances, ".0f")} | {safe_div(heart_rate_max, nb_seances, ".0f")} bpm</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Card vitesse moyenne
with col5:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #1f77b4;">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">🚀 Vitesse moyenne</div>
            <div class="metric-value" style="color: #1f77b4;">{safe_fmt(vitesse_moyenne, ".2f") if vitesse_moyenne else "-"} km/h</div>
            <div class='sub-metric'>🚀</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown("## Évolution des séances")

# Afficher les graphiques côte à côte
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Calories brûlées")
    alt_chart = (
        alt.Chart(df_sport)
        .mark_bar()
        .encode(
            x=alt.X("date", title="Date"),
            y=alt.Y("calorie", title="Calories brûlées"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("calorie:Q", title="Calories brûlées"),
            ],
        )
    )
    st.altair_chart(alt_chart, use_container_width=True)

with col_b:
    st.subheader("Durée des séances")
    df_sport_minutes = df_sport.copy()
    df_sport_minutes["duration_min"] = (
        df_sport_minutes["duration"].astype(float) / 1000 / 60
    )
    alt_chart_duree = (
        alt.Chart(df_sport_minutes)
        .mark_bar(color="orange")
        .encode(
            x=alt.X("date", title="Date"),
            y=alt.Y("duration_min", title="Durée (min)"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("duration_min:Q", title="Durée (min)"),
            ],
        )
    )
    st.altair_chart(alt_chart_duree, use_container_width=True)

col_a, col_b = st.columns(2)

with col_a:
    if distance_totale is not None:
        st.subheader("Distance parcourue")
        alt_chart_dist = (
            alt.Chart(df_sport)
            .mark_bar(color="green")
            .encode(
                x=alt.X("date", title="Date"),
                y=alt.Y("distance", title="Distance (m)"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip("distance:Q", title="Distance (m)"),
                ],
            )
        )
        st.altair_chart(alt_chart_dist, use_container_width=True)
    else:
        st.info("Les données de distance ne sont pas disponibles pour ce sport.")

with col_b:
    if heart_rate_avg is not None:
        st.subheader("Fréquence cardiaque")
        alt_chart_hr = (
            alt.Chart(df_sport)
            .mark_bar(color="red")
            .encode(
                x=alt.X("date", title="Date"),
                y=alt.Y("heart_rate", title="Fréquence cardiaque (bpm)"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip("heart_rate:Q", title="Fréquence cardiaque (bpm)"),
                ],
            )
        )
        st.altair_chart(alt_chart_hr, use_container_width=True)
    else:
        st.info(
            "Les données de fréquence cardiaque ne sont pas disponibles pour ce sport.",
        )

# Graphique de vitesse par séance
if "distance" in df_sport and "duration" in df_sport:
    df_vitesse = df_sport.copy()
    # Vitesse en km/h par séance
    df_vitesse["vitesse_kmh"] = (df_vitesse["distance"].astype(float) / 1000) / (
        df_vitesse["duration"].astype(float) / 1000 / 60 / 60
    )
    st.subheader("Vitesse par séance (km/h)")
    alt_chart_vitesse = (
        alt.Chart(df_vitesse)
        .mark_line(color="#1f77b4")
        .encode(
            x=alt.X("date", title="Date"),
            y=alt.Y("vitesse_kmh", title="Vitesse (km/h)", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("vitesse_kmh:Q", title="Vitesse (km/h)"),
            ],
        )
    )
    st.altair_chart(alt_chart_vitesse, use_container_width=True)

st.markdown("---")
st.markdown("# Records")

# Calcul des records
record_distance = None
record_vitesse = None
record_calories = None
record_duree = None
row_distance = row_vitesse = row_calories = row_duree = None

if not df_sport.empty:
    # Plus longue distance
    if "distance" in df_sport:
        idx = df_sport["distance"].astype(float).idxmax()
        row_distance = df_sport.loc[idx]
        record_distance = row_distance["distance"] / 1000
    # Plus grande vitesse
    if "distance" in df_sport and "duration" in df_sport:
        df_tmp = df_sport.copy()
        df_tmp = df_tmp[df_tmp["duration"].astype(float) > 0]
        if not df_tmp.empty:
            vitesse = (df_tmp["distance"].astype(float) / 1000) / (
                df_tmp["duration"].astype(float) / 1000 / 60 / 60
            )
            idx = vitesse.idxmax()
            row_vitesse = df_tmp.loc[idx]
            record_vitesse = vitesse.loc[idx]
    # Plus de calories
    if "calorie" in df_sport:
        idx = df_sport["calorie"].astype(float).idxmax()
        row_calories = df_sport.loc[idx]
        record_calories = row_calories["calorie"]
    # Plus de temps
    if "duration" in df_sport:
        idx = df_sport["duration"].astype(float).idxmax()
        row_duree = df_sport.loc[idx]
        record_duree = row_duree["duration"] / 1000 / 60

colr1, colr2, colr3, colr4 = st.columns(4)

with colr1:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #2ca02c;">
            <div style="font-size: 16px; font-weight: bold; color: #999;">
                🏆 Distance
            </div>
            <div class="metric-value" style="color: #2ca02c;">
                {safe_fmt(record_distance, ".2f") if record_distance is not None else "-"} km
            </div>
            <div class='sub-metric'>
                📅 {row_distance["date"].strftime("%d/%m/%Y") if row_distance is not None else "-"}<br/>
                🕒 {safe_fmt(row_distance["duration"] / 1000 / 60, ".0f") if row_distance is not None else "-"} min<br/>
                ⚡ {safe_fmt((row_distance["distance"] / 1000) / ((row_distance["duration"] / 1000) / 60 / 60), ".2f") if row_distance is not None and row_distance["duration"] > 0 else "-"} km/h<br/>
                🔥 {safe_fmt(row_distance["calorie"], ".0f") if row_distance is not None and "calorie" in row_distance else "-"} kcal<br/>
                📏 {safe_fmt(row_distance["distance"] / 1000, ".2f") if row_distance is not None else "-"} km
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with colr2:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #1f77b4;">
            <div style="font-size: 16px; font-weight: bold; color: #999;">
                ⚡ Vitesse
            </div>
            <div class="metric-value" style="color: #1f77b4;">
                {safe_fmt(record_vitesse, ".2f") if record_vitesse is not None else "-"} km/h
            </div>
            <div class='sub-metric'>
                📅 {row_vitesse["date"].strftime("%d/%m/%Y") if row_vitesse is not None else "-"}<br/>
                🕒 {safe_fmt(row_vitesse["duration"] / 1000 / 60, ".0f") if row_vitesse is not None else "-"} min<br/>
                ⚡ {safe_fmt((row_vitesse["distance"] / 1000) / ((row_vitesse["duration"] / 1000) / 60 / 60), ".2f") if row_vitesse is not None and row_vitesse["duration"] > 0 else "-"} km/h<br/>
                🔥 {safe_fmt(row_vitesse["calorie"], ".0f") if row_vitesse is not None and "calorie" in row_vitesse else "-"} kcal<br/>
                📏 {safe_fmt(row_vitesse["distance"] / 1000, ".2f") if row_vitesse is not None else "-"} km
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with colr3:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #FF8C00;">
            <div style="font-size: 16px; font-weight: bold; color: #999;">
                🔥 Énergie
            </div>
            <div class="metric-value" style="color: #FF8C00;">
                {safe_fmt(record_calories, ".0f") if record_calories is not None else "-"} kcal
            </div>
            <div class='sub-metric'>
                📅 {row_calories["date"].strftime("%d/%m/%Y") if row_calories is not None else "-"}<br/>
                🕒 {safe_fmt(row_calories["duration"] / 1000 / 60, ".0f") if row_calories is not None else "-"} min<br/>
                ⚡ {safe_fmt((row_calories["distance"] / 1000) / ((row_calories["duration"] / 1000) / 60 / 60), ".2f") if row_calories is not None and row_calories["duration"] > 0 else "-"} km/h<br/>
                🔥 {safe_fmt(row_calories["calorie"], ".0f") if row_calories is not None and "calorie" in row_calories else "-"} kcal<br/>
                📏 {safe_fmt(row_calories["distance"] / 1000, ".2f") if row_calories is not None else "-"} km
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with colr4:
    st.markdown(
        f"""
        <div class="metric-card" style="border-left: 4px solid #667eea;">
            <div style="font-size: 16px; font-weight: bold; color: #999;">
                ⏱️ Durée
            </div>
            <div class="metric-value" style="color: #667eea;">
                {safe_fmt(record_duree, ".0f") if record_duree is not None else "-"} min
            </div>
            <div class='sub-metric'>
                📅 {row_duree["date"].strftime("%d/%m/%Y") if row_duree is not None else "-"}<br/>
                🕒 {safe_fmt(row_duree["duration"] / 1000 / 60, ".0f") if row_duree is not None else "-"} min<br/>
                ⚡ {safe_fmt((row_duree["distance"] / 1000) / ((row_duree["duration"] / 1000) / 60 / 60), ".2f") if row_duree is not None and row_duree["duration"] > 0 else "-"} km/h<br/>
                🔥 {safe_fmt(row_duree["calorie"], ".0f") if row_duree is not None and "calorie" in row_duree else "-"} kcal<br/>
                📏 {safe_fmt(row_duree["distance"] / 1000, ".2f") if row_duree is not None else "-"} km
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Sports concernés
SPORTS_ALT = {"Course à pied", "Vélo", "Randonnée", "Marche"}
if selected_sport in SPORTS_ALT:
    st.markdown("---")
    st.markdown("## Points visités")
    # Affichage carte des points visités
    df_points = df_sport.copy()
    # On ne garde que les lignes avec latitude et longitude valides
    if "latitude" in df_points and "longitude" in df_points:
        df_points = df_points[
            df_points["latitude"].notnull() & df_points["longitude"].notnull()
        ]
        if not df_points.empty:
            st.map(
                df_points[["latitude", "longitude"]].rename(
                    columns={"latitude": "lat", "longitude": "lon"},
                ),
            )
        else:
            st.info("Aucun point GPS disponible pour ce sport.")
