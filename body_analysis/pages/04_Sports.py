import json
import logging
import os

import altair as alt
import pandas as pd
import streamlit as st

from body_analysis.data_ingestion import find_data_files, load_exercise_df
from body_analysis.sports_utils import (
    COLORS,
    CSS_STYLES,
    SPORT_EMOJI,
    SPORTS_MAP,
    create_bar_chart,
    create_heatmap_chart,
    detect_sport,
    prepare_heatmap_data,
    render_metric_card,
    safe_div,
    safe_fmt,
)

ENV = os.environ.get("ENV", "dev")
if ENV == "production":
    DATA_DIR_DEFAULT = "/app/data"
else:
    DATA_DIR_DEFAULT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data"),
    )

logger = logging.getLogger(__name__)

st.title("Analyse des sports")

# Charger les données d'exercice
paths = find_data_files()
if not paths.exercise_csv:
    st.warning("Aucun fichier d'exercice trouvé.")
    st.stop()

rows = load_exercise_df(paths.exercise_csv)
df = pd.DataFrame(rows)


# Ajouter une colonne avec le nom du sport
df["sport"] = df.apply(detect_sport, axis=1)


# On ne garde que les sports connus (présents dans SPORTS_MAP ou "Musculation")
known_sports = set(SPORTS_MAP.values()) | {"Musculation"}
df_known = df[df["sport"].isin(known_sports)]


# Liste unique des titres de sport + option "Tous les entraînements"
sport_titles = ["Tous les entraînements"] + sorted(df_known["sport"].unique())


# Appliquer les styles CSS
st.markdown(CSS_STYLES, unsafe_allow_html=True)

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

if not df_sport.empty and "date" in df_sport:
    df_heatmap = prepare_heatmap_data(df_sport)
    if not df_heatmap.empty:
        heatmap = create_heatmap_chart(df_heatmap)
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
        render_metric_card(
            "Durée totale",
            "⏱️",
            f"{safe_div(duree_totale, 60, '.0f')} h",
            f"⏱️ {safe_div(duree_totale, nb_seances, '.0f')} min/séance",
            COLORS["duration"],
        ),
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        render_metric_card(
            "Calories totales",
            "🔥",
            f"{safe_fmt(calories_totales, '.0f')} kcal",
            f"🔥 {safe_div(calories_totales, nb_seances, '.0f')} kcal/séance",
            COLORS["calories"],
        ),
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        render_metric_card(
            "Distance totale",
            "📏",
            f"{safe_fmt(distance_totale, '.1f')} km",
            f"📏 {safe_div(distance_totale, nb_seances, '.2f')} km/séance",
            COLORS["distance"],
        ),
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        render_metric_card(
            "Fréquence cardiaque",
            "❤️",
            f"{safe_div(heart_rate_avg, nb_seances, '.0f')} bpm",
            (
                f"❤️ {safe_div(heart_rate_min, nb_seances, '.0f')} | "
                f"{safe_div(heart_rate_max, nb_seances, '.0f')} bpm"
            ),
            COLORS["heart_rate"],
        ),
        unsafe_allow_html=True,
    )

with col5:
    st.markdown(
        render_metric_card(
            "Vitesse moyenne",
            "🚀",
            f"{safe_fmt(vitesse_moyenne, '.2f') if vitesse_moyenne else '-'} km/h",
            "🚀",
            COLORS["speed"],
        ),
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown("## Évolution des séances")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Calories brûlées")
    chart_calories = create_bar_chart(
        df_sport,
        "date",
        "calorie",
        "🔥 Calories brûlées",
        COLORS["calories"],
        "Calories brûlées",
    )
    st.altair_chart(chart_calories, use_container_width=True)

with col_b:
    st.subheader("Durée des séances")
    df_sport_minutes = df_sport.copy()
    df_sport_minutes["duration_min"] = (
        df_sport_minutes["duration"].astype(float) / 1000 / 60
    )
    chart_duration = create_bar_chart(
        df_sport_minutes,
        "date",
        "duration_min",
        "⏱️ Durée des séances",
        COLORS["duration"],
        "Durée (min)",
    )
    st.altair_chart(chart_duration, use_container_width=True)

col_a, col_b = st.columns(2)

with col_a:
    if distance_totale is not None:
        st.subheader("Distance parcourue")
        chart_dist = create_bar_chart(
            df_sport,
            "date",
            "distance",
            "📏 Distance parcourue",
            COLORS["distance"],
            "Distance (m)",
        )
        st.altair_chart(chart_dist, use_container_width=True)
    else:
        st.info("Les données de distance ne sont pas disponibles pour ce sport.")

with col_b:
    if heart_rate_avg is not None:
        st.subheader("Fréquence cardiaque")
        chart_hr = (
            alt.Chart(df_sport)
            .mark_bar(color=COLORS["heart_rate"])
            .encode(
                x=alt.X("date", title="Date"),
                y=alt.Y("heart_rate", title="Fréquence cardiaque (bpm)"),
                tooltip=[
                    alt.Tooltip("date:T", title="Date"),
                    alt.Tooltip("heart_rate:Q", title="Fréquence cardiaque (bpm)"),
                ],
            )
        )
        st.altair_chart(chart_hr, use_container_width=True)
    else:
        st.info(
            "Les données de fréquence cardiaque ne sont pas disponibles pour ce sport.",
        )

# Graphique de vitesse par séance
if "distance" in df_sport and "duration" in df_sport:
    df_vitesse = df_sport.copy()
    df_vitesse["vitesse_kmh"] = (df_vitesse["distance"].astype(float) / 1000) / (
        df_vitesse["duration"].astype(float) / 1000 / 60 / 60
    )
    st.subheader("Vitesse par séance (km/h)")
    chart_vitesse = (
        alt.Chart(df_vitesse)
        .mark_line(color=COLORS["speed"])
        .encode(
            x=alt.X("date", title="Date"),
            y=alt.Y("vitesse_kmh", title="Vitesse (km/h)", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("vitesse_kmh:Q", title="Vitesse (km/h)"),
            ],
        )
        .properties(height=300, title="🚀 Vitesse par séance")
        .interactive()
    )
    st.altair_chart(chart_vitesse, use_container_width=True)

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

# Données additionnelles pour la natation
if selected_sport == "Natation":
    st.markdown("---")
    st.markdown("## Statistiques par nage")

    # Charger et analyser les données JSON pour les statistiques
    if not df_sport.empty and "additionnal" in df_sport.columns:
        df_with_additional = df_sport[df_sport["additionnal"].notna()].copy()

        # Collecter les données pour le graphique
        speed_evolution_data = []
        session_counter = {}

        for _, row in df_with_additional.iterrows():
            filename = row.get("additionnal")
            if filename:
                folder = filename[0].lower()
                file_path = os.path.join(
                    DATA_DIR_DEFAULT,
                    "com.samsung.shealth.exercise",
                    folder,
                    filename,
                )

                try:
                    with open(file_path) as f:
                        data_json = json.load(f)

                    pool_length = data_json.get("pool_length", 25)
                    lengths = data_json.get("lengths", [])

                    for length in lengths:
                        stroke_type = length.get("stroke_type", "Unknown")
                        duration_ms = length.get("duration", 0)
                        duration_sec = duration_ms / 1000

                        # Calcul de la vitesse en min/sec pour 100m
                        if duration_sec > 0:
                            time_per_100m = (duration_sec / pool_length) * 100
                            time_100m_min = int(time_per_100m // 60)
                            time_100m_sec = int(time_per_100m % 60)
                            time_100m_display = f"{time_100m_min}:{time_100m_sec:02d}"

                            # Incrémenter le compteur de session pour ce type de nage
                            if stroke_type not in session_counter:
                                session_counter[stroke_type] = 0
                            session_counter[stroke_type] += 1

                            # Récupérer la FC moyenne
                            heart_rate = length.get(
                                "heart_rate",
                                row.get("heart_rate", None),
                            )

                            speed_evolution_data.append(
                                {
                                    "Nage": stroke_type,
                                    "Numéro de longueur": (
                                        session_counter[stroke_type]
                                    ),
                                    "Temps pour 100m (secondes)": (time_per_100m),
                                    "Temps pour 100m": time_100m_display,
                                    "Date": (
                                        row.get("date")
                                        if "date" in row.index
                                        else pd.Timestamp.now()
                                    ),
                                    "FC": heart_rate,
                                    "Duration (s)": duration_sec,
                                    "Pool Length": pool_length,
                                },
                            )
                except (FileNotFoundError, json.JSONDecodeError, OSError):
                    pass

        if speed_evolution_data:
            df_speed = pd.DataFrame(speed_evolution_data)

            # Dictionnaire des emojis par type de nage
            stroke_emojis_chart = {
                "Freestyle": "🏊",
                "Breaststroke": "🏊‍♂️",
                "Butterfly": "🦋",
                "Backstroke": "🔙",
                "Individual Medley": "🎯",
            }

            # --- SECTION STATISTIQUES GÉNÉRALES ---
            st.subheader("📊 Statistiques générales par nage")

            # Convertir en DataFrame
            df_speed = pd.DataFrame(speed_evolution_data)

            # Emojis par nage
            stroke_emojis = {
                "Freestyle": "🏊",
                "Breaststroke": "🏊‍♂️",
                "Butterfly": "🦋",
                "Backstroke": "🔙",
                "Individual Medley": "🎯",
            }

            # Créer des colonnes pour les cartes
            stroke_list = sorted(df_speed["Nage"].unique())
            cols = st.columns(min(2, len(stroke_list)))

            # Grouper par nage et calculer les stats
            for idx, stroke_type in enumerate(stroke_list):
                df_stroke_data = df_speed[df_speed["Nage"] == stroke_type]
                emoji = stroke_emojis.get(stroke_type, "🏊")

                # Calcul des statistiques
                total_time_sec = (
                    df_stroke_data["Temps pour 100m (secondes)"].sum() / 100 * 25
                )
                total_km = len(df_stroke_data) * 0.025
                avg_time_per_100m_sec = df_stroke_data[
                    "Temps pour 100m (secondes)"
                ].mean()
                total_time_min = total_time_sec / 60

                # Format mm:ss/100m
                avg_time_per_100m_min = int(
                    avg_time_per_100m_sec // 60,
                )
                avg_time_per_100m_sec_remainder = int(
                    avg_time_per_100m_sec % 60,
                )
                time_format = (
                    f"{avg_time_per_100m_min}:"
                    f"{avg_time_per_100m_sec_remainder:02d}/100m"
                )

                # SWOLF au 50m
                swolf_50m_values = []
                for _, row in df_stroke_data.iterrows():
                    time_100m = row["Temps pour 100m (secondes)"]
                    time_50m = time_100m / 2
                    swolf_50m_values.append(time_50m)

                swolf_50m = (
                    sum(swolf_50m_values) / len(swolf_50m_values)
                    if swolf_50m_values
                    else None
                )

                # Calcul des 3 indicateurs
                fc_values = [x for x in df_stroke_data["FC"].values if pd.notna(x)]
                avg_heart_rate = (
                    (sum(fc_values) / len(fc_values)) if fc_values else None
                )

                vitesse_ms = (
                    (
                        df_stroke_data["Pool Length"].iloc[0]
                        / df_stroke_data["Duration (s)"].mean()
                    )
                    if len(df_stroke_data) > 0
                    else 0
                )

                cout_cardiaque = (
                    (avg_heart_rate / vitesse_ms)
                    if avg_heart_rate and vitesse_ms > 0
                    else None
                )

                distance_par_battement = (
                    (vitesse_ms / (avg_heart_rate / 60))
                    if avg_heart_rate and avg_heart_rate > 0
                    else None
                )

                # 4️⃣ Score d'Efficacité Natation (SEN)
                indice_economie = (
                    (vitesse_ms**2 / avg_heart_rate)
                    if avg_heart_rate and vitesse_ms > 0
                    else None
                )

                # Afficher la carte dans la colonne
                col = cols[idx % len(cols)]
                with col:
                    st.markdown(
                        f"""
                        <div class="metric-card"
                            style="border-left: 4px solid #667eea;
                            padding: 12px; min-height: auto;">
                            <div style="font-size: 16px;
                                font-weight: bold;
                                color: #667eea;
                                margin-bottom: 10px;">
                                {emoji} {stroke_type}
                            </div>
                            <div style="display: grid;
                                grid-template-columns: 1fr 1fr;
                                gap: 8px;
                                font-size: 13px;">
                                <div>
                                    <div style="font-size: 11px;
                                        color: #999;
                                        margin-bottom: 3px;">
                                        ⏱️ Temps/100m
                                    </div>
                                    <div style="font-size: 16px;
                                        font-weight: bold;
                                        color: #667eea;">
                                        {time_format}
                                    </div>
                                </div>
                                <div>
                                    <div style="font-size: 11px;
                                        color: #999;
                                        margin-bottom: 3px;">
                                        🎯 SWOLF/50m
                                    </div>
                                    <div style="font-size: 16px;
                                        font-weight: bold;
                                        color: #e74c3c;">
                                        {
                            (safe_fmt(swolf_50m, ".1f") if swolf_50m else "-")
                        }
                                    </div>
                                </div>
                                <div>
                                    <div style="font-size: 11px;
                                        color: #999;
                                        margin-bottom: 3px;">
                                        ⏱️ Durée
                                    </div>
                                    <div style="font-size: 16px;
                                        font-weight: bold;
                                        color: #2ca02c;">
                                        {safe_fmt(total_time_min, ".0f")} min
                                    </div>
                                </div>
                                <div>
                                    <div style="font-size: 11px;
                                        color: #999;
                                        margin-bottom: 3px;">
                                        📏 Distance
                                    </div>
                                    <div style="font-size: 16px;
                                        font-weight: bold;
                                        color: #1f77b4;">
                                        {safe_fmt(total_km, ".2f")} km
                                    </div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            st.markdown("---")

            # Graphiques d'évolution des indicateurs par nage
            st.subheader("📈 Évolution des indicateurs par nage")

            for stroke_type in sorted(df_speed["Nage"].unique()):
                df_stroke_data = df_speed[df_speed["Nage"] == stroke_type].copy()
                stroke_emojis = {
                    "Freestyle": "🏊",
                    "Breaststroke": "🏊‍♂️",
                    "Butterfly": "🦋",
                    "Backstroke": "🔙",
                    "Individual Medley": "🎯",
                }
                emoji = stroke_emojis.get(stroke_type, "🏊")

                # Calculer les indicateurs pour chaque longueur
                fc_values = [x for x in df_stroke_data["FC"].to_numpy() if pd.notna(x)]
                if not fc_values:
                    continue

                # Ajouter les indicateurs au dataframe
                df_stroke_data = df_stroke_data.copy()
                df_stroke_data["FC_numeric"] = (df_stroke_data["FC"]).astype(float)

                # Vitesse en m/s pour chaque longueur
                df_stroke_data["Vitesse_ms"] = (
                    df_stroke_data["Pool Length"] / df_stroke_data["Duration (s)"]
                )

                # Coût cardiaque
                df_stroke_data["Cout_cardiaque"] = (
                    df_stroke_data["FC_numeric"] / df_stroke_data["Vitesse_ms"]
                )

                # Distance par battement
                df_stroke_data["Distance_par_battement"] = df_stroke_data[
                    "Vitesse_ms"
                ] / (df_stroke_data["FC_numeric"] / 60)

                # Indice d'économie (approx par longueur)
                df_stroke_data["Indice_economie"] = (
                    df_stroke_data["Vitesse_ms"] ** 2
                ) / df_stroke_data["FC_numeric"]

                # Créer un expander pour afficher les graphiques au clic
                with st.expander(f"{emoji} {stroke_type} - Indicateurs détaillés"):
                    # Créer 4 graphiques : 2 à 2
                    col1, col2 = st.columns(2)

                    with col1:
                        base_cout = alt.Chart(df_stroke_data).encode(
                            x=alt.X(
                                "Numéro de longueur:Q",
                                title="Longueur",
                            ),
                        )
                        chart_cout_line = base_cout.mark_line(point=True).encode(
                            y=alt.Y(
                                "Cout_cardiaque:Q",
                                title=("Coût cardiaque (bpm/m/s)"),
                            ),
                            color=alt.value("#764ba2"),
                            tooltip=[
                                alt.Tooltip(
                                    "Numéro de longueur:Q",
                                    title="Longueur",
                                ),
                                alt.Tooltip(
                                    "Cout_cardiaque:Q",
                                    title="Coût card.",
                                    format=".2f",
                                ),
                                alt.Tooltip(
                                    "FC_numeric:Q",
                                    title="FC",
                                    format=".0f",
                                ),
                            ],
                        )
                        chart_cout_trend = (
                            base_cout.transform_regression(
                                "Numéro de longueur",
                                "Cout_cardiaque",
                            )
                            .mark_line(size=3, opacity=0.8)
                            .encode(
                                y=alt.Y("Cout_cardiaque:Q"),
                                color=alt.value("#ffffff"),
                            )
                        )
                        chart_cout = (
                            (chart_cout_line + chart_cout_trend)
                            .properties(
                                height=300,
                                title=("2️⃣ Coût cardiaque ↓"),
                            )
                            .interactive()
                        )
                        st.altair_chart(chart_cout, use_container_width=True)

                    with col2:
                        base_dist = alt.Chart(df_stroke_data).encode(
                            x=alt.X(
                                "Numéro de longueur:Q",
                                title="Longueur",
                            ),
                        )
                        chart_dist_line = base_dist.mark_line(point=True).encode(
                            y=alt.Y(
                                "Distance_par_battement:Q",
                                title=("Distance/battement (m/batt)"),
                            ),
                            color=alt.value("#fd7e14"),
                            tooltip=[
                                alt.Tooltip(
                                    "Numéro de longueur:Q",
                                    title="Longueur",
                                ),
                                alt.Tooltip(
                                    "Distance_par_battement:Q",
                                    title="Dist/batt",
                                    format=".3f",
                                ),
                                alt.Tooltip(
                                    "FC_numeric:Q",
                                    title="FC",
                                    format=".0f",
                                ),
                            ],
                        )
                        chart_dist_trend = (
                            base_dist.transform_regression(
                                "Numéro de longueur",
                                "Distance_par_battement",
                            )
                            .mark_line(size=3, opacity=0.8)
                            .encode(
                                y=alt.Y("Distance_par_battement:Q"),
                                color=alt.value("#ffffff"),
                            )
                        )
                        chart_dist = (
                            (chart_dist_line + chart_dist_trend)
                            .properties(
                                height=300,
                                title=("3️⃣ Distance/battement ↑"),
                            )
                            .interactive()
                        )
                        st.altair_chart(chart_dist, use_container_width=True)

                    col3, col4 = st.columns(2)

                    with col3:
                        base_eco = alt.Chart(df_stroke_data).encode(
                            x=alt.X(
                                "Numéro de longueur:Q",
                                title="Longueur",
                            ),
                        )
                        chart_eco_line = base_eco.mark_line(point=True).encode(
                            y=alt.Y(
                                "Indice_economie:Q",
                                title=("SEN (Vitesse²/FC) ↑"),
                            ),
                            color=alt.value("#20c997"),
                            tooltip=[
                                alt.Tooltip(
                                    "Numéro de longueur:Q",
                                    title="Longueur",
                                ),
                                alt.Tooltip(
                                    "Indice_economie:Q",
                                    title="SEN",
                                    format=".2f",
                                ),
                                alt.Tooltip(
                                    "FC_numeric:Q",
                                    title="FC",
                                    format=".0f",
                                ),
                            ],
                        )
                        chart_eco_trend = (
                            base_eco.transform_regression(
                                "Numéro de longueur",
                                "Indice_economie",
                            )
                            .mark_line(size=3, opacity=0.8)
                            .encode(
                                y=alt.Y("Indice_economie:Q"),
                                color=alt.value("#ffffff"),
                            )
                        )
                        chart_eco = (
                            (chart_eco_line + chart_eco_trend)
                            .properties(
                                height=300,
                                title=("4️⃣ SEN (Score Efficacité) ↑"),
                            )
                            .interactive()
                        )
                        st.altair_chart(chart_eco, use_container_width=True)

                    with col4:
                        base_vitesse = alt.Chart(df_stroke_data).encode(
                            x=alt.X(
                                "Numéro de longueur:Q",
                                title="Longueur",
                            ),
                        )
                        chart_vitesse_line = base_vitesse.mark_line(point=True).encode(
                            y=alt.Y(
                                "Vitesse_ms:Q",
                                title=("Vitesse (m/s) ↑"),
                            ),
                            color=alt.value("#1f77b4"),
                            tooltip=[
                                alt.Tooltip(
                                    "Numéro de longueur:Q",
                                    title="Longueur",
                                ),
                                alt.Tooltip(
                                    "Vitesse_ms:Q",
                                    title="Vitesse",
                                    format=".2f",
                                ),
                                alt.Tooltip(
                                    "Duration (s):Q",
                                    title="Durée (s)",
                                    format=".1f",
                                ),
                            ],
                        )
                        chart_vitesse_trend = (
                            base_vitesse.transform_regression(
                                "Numéro de longueur",
                                "Vitesse_ms",
                            )
                            .mark_line(size=3, opacity=0.8)
                            .encode(
                                y=alt.Y("Vitesse_ms:Q"),
                                color=alt.value("#ffffff"),
                            )
                        )
                        chart_vitesse = (
                            (chart_vitesse_line + chart_vitesse_trend)
                            .properties(
                                height=300,
                                title=("⚡ Vitesse"),
                            )
                            .interactive()
                        )
                        st.altair_chart(chart_vitesse, use_container_width=True)


# ============================================================================
# SECTION RUNNING - COURSE À PIED
# ============================================================================

if selected_sport == "Course à pied":
    st.divider()
    st.markdown("## 🏃 Course à pied")

    # Filtrer les courses à pied dans la plage de dates sélectionnée
    running_exercises = df_sport[df_sport["sport"] == "Course à pied"].copy()

    if len(running_exercises) == 0:
        st.info("Aucune course à pied enregistrée dans la période sélectionnée")
    else:
        # === STATS GLOBALES ===
        st.subheader("📊 Statistiques globales")

        # Préparer les données
        running_exercises["distance_km"] = running_exercises["distance"] / 1000
        running_exercises["duration_min"] = running_exercises["duration"] / 1000 / 60
        running_exercises["duration_s"] = running_exercises["duration"] / 1000
        running_exercises["allure_min_par_km"] = (
            running_exercises["duration_min"] / running_exercises["distance_km"]
        )
        running_exercises["vitesse_ms"] = (
            running_exercises["distance"] / running_exercises["duration_s"]
        )

        # Parser les fichiers JSON du running une seule fois
        cadence_list = []
        vitesse_kmh_list = []

        for additional_filename in running_exercises["additionnal"]:
            cadence = None
            speed_kmh = None

            if additional_filename:
                try:
                    folder = additional_filename[0].lower()
                    file_path = os.path.join(
                        DATA_DIR_DEFAULT,
                        "com.samsung.shealth.exercise",
                        folder,
                        additional_filename,
                    )

                    with open(file_path) as f:
                        data_json = json.load(f)

                    main_workout = data_json.get("main_workout", {})
                    cadence = main_workout.get("avg_cadence")
                    avg_speed = main_workout.get("avg_speed", 0)
                    if avg_speed:
                        speed_kmh = avg_speed * 3.6
                except (FileNotFoundError, json.JSONDecodeError, OSError):
                    pass

            cadence_list.append(cadence)
            vitesse_kmh_list.append(speed_kmh)

        running_exercises["cadence"] = cadence_list
        running_exercises["vitesse_kmh"] = vitesse_kmh_list

        # Calculer les stats globales
        total_distance = running_exercises["distance_km"].sum()
        total_duration = running_exercises["duration_min"].sum()
        nb_courses = len(running_exercises)
        avg_hr = running_exercises["heart_rate"].mean()
        avg_allure = running_exercises["allure_min_par_km"].mean()
        avg_cadence = running_exercises["cadence"].mean()

        # Calculer l'allure moyenne au format mm:ss/km
        avg_allure_min = int(avg_allure)
        avg_allure_sec = int((avg_allure - avg_allure_min) * 60)
        avg_allure_str = f"{avg_allure_min}:{avg_allure_sec:02d}/km"

        # Afficher les stats dans des colonnes
        cols = st.columns(5)

        with cols[0]:
            st.metric(
                "📏 Distance totale",
                f"{total_distance:.1f} km",
            )

        with cols[1]:
            st.metric(
                "🏃 Nombre de séances",
                f"{nb_courses}",
            )

        with cols[2]:
            st.metric(
                "⏱️ Allure moy",
                avg_allure_str,
            )

        with cols[3]:
            st.metric(
                "❤️ FC moy",
                f"{avg_hr:.0f} bpm",
            )

        with cols[4]:
            st.metric(
                "👟 Cadence moy",
                f"{avg_cadence:.0f} pas/min",
            )

        st.divider()

        # === GRAPHIQUES D'ÉVOLUTION ===
        st.subheader("📈 Évolution des séances")

        # Nettoyer et reset l'index
        running_exercises_clean = running_exercises.reset_index(drop=True).copy()

        # Ajouter des indicateurs d'efficacité
        running_exercises_clean["economie"] = running_exercises_clean.apply(
            lambda r: r["distance_km"] / r["heart_rate"]
            if r["heart_rate"] > 0
            else None,
            axis=1,
        ).astype("float64")

        running_exercises_clean["efficacite_energetique"] = (
            running_exercises_clean.apply(
                lambda r: r["distance_km"] / (r["heart_rate"] * r["duration_min"])
                if (r["heart_rate"] > 0 and r["duration_min"] > 0)
                else None,
                axis=1,
            ).astype("float64")
        )

        # Créer les graphiques
        col1, col2 = st.columns(2)

        with col1:
            chart_distance = (
                alt.Chart(running_exercises_clean)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("distance_km:Q", title="Distance (km)"),
                    color=alt.value("#e74c3c"),
                )
                .properties(height=300, title="📏 Distance par séance")
                .interactive()
            )
            st.altair_chart(chart_distance, use_container_width=True)

        with col2:
            chart_allure = (
                alt.Chart(running_exercises_clean)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y(
                        "allure_min_par_km:Q",
                        title="Allure (min/km)",
                    ),
                    color=alt.value("#3498db"),
                )
                .properties(height=300, title="⏱️ Allure par séance")
                .interactive()
            )
            st.altair_chart(chart_allure, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            chart_hr = (
                alt.Chart(running_exercises_clean)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="Date"),
                    y=alt.Y("heart_rate:Q", title="FC moy (bpm)"),
                    color=alt.value("#c0392b"),
                )
                .properties(height=300, title="❤️ Fréquence cardiaque")
                .interactive()
            )
            st.altair_chart(chart_hr, use_container_width=True)

        with col4:
            running_cadence = running_exercises_clean.dropna(subset=["cadence"])
            if len(running_cadence) > 0:
                chart_cadence = (
                    alt.Chart(running_cadence)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("cadence:Q", title="Cadence (pas/min)"),
                        color=alt.value("#9b59b6"),
                    )
                    .properties(height=300, title="👟 Cadence")
                    .interactive()
                )
                st.altair_chart(chart_cadence, use_container_width=True)
            else:
                st.info("Pas de données de cadence disponibles")
