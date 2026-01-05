"""Utilities for sports analysis dashboard.

This module provides reusable functions for:
- Data formatting and calculations
- UI components rendering
- Chart creation
"""

import json
import logging
import os

import altair as alt
import pandas as pd

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

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

STROKE_EMOJI = {
    "Freestyle": "🏊",
    "Breaststroke": "🏊‍♂️",
    "Butterfly": "🦋",
    "Backstroke": "🔙",
    "Individual Medley": "🎯",
}

COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "duration": "#667eea",
    "calories": "#FF8C00",
    "distance": "#2ca02c",
    "heart_rate": "#e74c3c",
    "speed": "#1f77b4",
    "cost": "#764ba2",
    "distance_per_beat": "#fd7e14",
    "efficiency": "#20c997",
}

CSS_STYLES = """
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
"""

# ============================================================================
# FORMATTING FUNCTIONS
# ============================================================================


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


def safe_div(
    val: float | None,
    div: float | None,
    fmt: str,
    default: str = "-",
) -> str:
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


def format_time_mm_ss(seconds: float | None) -> str:
    """Format seconds to mm:ss format.

    Args:
        seconds: Number of seconds.

    Returns:
        Formatted time string or "-".

    """
    if seconds is None or seconds < 0:
        return "-"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


# ============================================================================
# DETECTION FUNCTIONS
# ============================================================================


def detect_sport(row: dict) -> str:
    """Detect sport from row data.

    Handles:
    - Weight training (by detecting 'reps' in subset_data)
    - Other sports via SPORTS_MAP mapping

    Args:
        row: DataFrame row as dict.

    Returns:
        Sport name string.

    """
    code = row.get("exercise_type")
    subset_data = row.get("subset_data")

    # Check if it's weight training (has reps)
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

    # Use mapping for other sports
    if code in SPORTS_MAP:
        return SPORTS_MAP[code]
    return str(code) if code is not None else "?"


# ============================================================================
# METRIC CARD RENDERING
# ============================================================================


def render_metric_card(
    title: str,
    emoji: str,
    value: str,
    sub_metric: str = "",
    color: str = COLORS["primary"],
) -> str:
    """Render a single metric card.

    Args:
        title: Card title.
        emoji: Emoji to display.
        value: Main value to display (big).
        sub_metric: Additional metric text (small).
        color: Color for the left border.

    Returns:
        HTML string for the card.

    """
    sub_metric_html = (
        f"<div class='sub-metric'>{sub_metric}</div>" if sub_metric else ""
    )

    return f"""
        <div class="metric-card" style="border-left: 4px solid {color};">
            <div style="font-size: 16px; font-weight: bold; color: #999; margin-bottom: 10px;">
                {emoji} {title}
            </div>
            <div class="metric-value" style="color: {color};">
                {value}
            </div>
            {sub_metric_html}
        </div>
        """


def render_record_card(
    title: str,
    emoji: str,
    main_value: str,
    color: str,
    date_str: str = "-",
    duration_str: str = "-",
    speed_str: str = "-",
    calories_str: str = "-",
    distance_str: str = "-",
) -> str:
    """Render a record card with details.

    Args:
        title: Card title.
        emoji: Main emoji.
        main_value: Main value (big).
        color: Border color.
        date_str: Date string.
        duration_str: Duration string.
        speed_str: Speed string.
        calories_str: Calories string.
        distance_str: Distance string.

    Returns:
        HTML string for the record card.

    """
    return f"""
        <div class="metric-card" style="border-left: 4px solid {color};">
            <div style="font-size: 16px; font-weight: bold; color: #999;">
                {emoji} {title}
            </div>
            <div class="metric-value" style="color: {color};">
                {main_value}
            </div>
            <div class='sub-metric'>
                📅 {date_str}<br/>
                🕒 {duration_str}<br/>
                ⚡ {speed_str}<br/>
                🔥 {calories_str}<br/>
                📏 {distance_str}
            </div>
        </div>
        """


# ============================================================================
# SWIMMING CARD RENDERING
# ============================================================================


def render_swimming_stroke_card(
    stroke_type: str,
    emoji: str,
    time_format: str,
    swolf_50m: float | None,
    total_time_min: float | None,
    total_km: float | None,
) -> str:
    """Render swimming stroke statistics card.

    Args:
        stroke_type: Type of stroke.
        emoji: Stroke emoji.
        time_format: Time per 100m (mm:ss).
        swolf_50m: SWOLF score for 50m.
        total_time_min: Total time in minutes.
        total_km: Total distance in km.

    Returns:
        HTML string for the card.

    """
    swolf_str = safe_fmt(swolf_50m, ".1f") if swolf_50m else "-"

    return f"""
        <div class="metric-card"
            style="border-left: 4px solid {COLORS["primary"]};
            padding: 12px; min-height: auto;">
            <div style="font-size: 16px;
                font-weight: bold;
                color: {COLORS["primary"]};
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
                        color: {COLORS["primary"]};">
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
                        color: {COLORS["heart_rate"]};">
                        {swolf_str}
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
                        color: {COLORS["distance"]};">
                        {safe_fmt(total_time_min, ".0f") if total_time_min else "-"} min
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
                        color: {COLORS["speed"]};">
                        {safe_fmt(total_km, ".2f") if total_km else "-"} km
                    </div>
                </div>
            </div>
        </div>
        """


# ============================================================================
# CHART FUNCTIONS
# ============================================================================


def create_heatmap_chart(df_heatmap: pd.DataFrame) -> alt.Chart:
    """Create a heatmap chart for training sessions.

    Args:
        df_heatmap: DataFrame with columns:
            - week: Week number
            - weekday: Day of week (0-6)
            - nb_seances: Number of sessions

    Returns:
        Altair chart.

    """
    return (
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


def create_line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    color: str = COLORS["primary"],
    y_title: str = "",
) -> alt.Chart:
    """Create a simple line chart.

    Args:
        df: Input DataFrame.
        x_col: X-axis column name.
        y_col: Y-axis column name.
        title: Chart title.
        color: Line color.
        y_title: Y-axis title (defaults to y_col if empty).

    Returns:
        Altair chart.

    """
    y_title = y_title or y_col
    return (
        alt.Chart(df)
        .mark_line(point=True, color=color)
        .encode(
            x=alt.X(f"{x_col}:T", title="Date"),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            tooltip=[
                alt.Tooltip(f"{x_col}:T", title="Date"),
                alt.Tooltip(f"{y_col}:Q", title=y_title),
            ],
        )
        .properties(height=300, title=title)
        .interactive()
    )


def create_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    color: str = COLORS["primary"],
    y_title: str = "",
) -> alt.Chart:
    """Create a simple bar chart.

    Args:
        df: Input DataFrame.
        x_col: X-axis column name.
        y_col: Y-axis column name.
        title: Chart title.
        color: Bar color.
        y_title: Y-axis title (defaults to y_col if empty).

    Returns:
        Altair chart.

    """
    y_title = y_title or y_col
    return (
        alt.Chart(df)
        .mark_bar(color=color)
        .encode(
            x=alt.X(f"{x_col}:T", title="Date"),
            y=alt.Y(f"{y_col}:Q", title=y_title),
            tooltip=[
                alt.Tooltip(f"{x_col}:T", title="Date"),
                alt.Tooltip(f"{y_col}:Q", title=y_title),
            ],
        )
        .properties(height=300, title=title)
        .interactive()
    )


# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================


def prepare_heatmap_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for heatmap visualization.

    Args:
        df: Input DataFrame with 'date' column.

    Returns:
        DataFrame with heatmap-ready data.

    """
    df_heat = df.copy()
    df_heat["date"] = pd.to_datetime(df_heat["date"])
    df_heat["date_jour"] = df_heat["date"].dt.date

    df_heatmap = df_heat.groupby("date_jour").size().reset_index(name="nb_seances")
    df_heatmap["date"] = pd.to_datetime(df_heatmap["date_jour"])
    df_heatmap["day"] = df_heatmap["date"].dt.day
    df_heatmap["month"] = df_heatmap["date"].dt.month
    df_heatmap["weekday"] = df_heatmap["date"].dt.dayofweek
    df_heatmap["week"] = df_heatmap["date"].dt.isocalendar().week

    return df_heatmap


def load_exercise_json(file_path: str) -> dict | None:
    """Load exercise JSON file safely.

    Args:
        file_path: Path to JSON file.

    Returns:
        Parsed JSON dict or None if error.

    """
    try:
        with open(file_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
        logger.debug(f"Could not load JSON from {file_path}: {e}")
        return None


def get_exercise_file_path(data_dir: str, filename: str) -> str:
    """Build full path to exercise JSON file.

    Args:
        data_dir: Base data directory.
        filename: Exercise filename.

    Returns:
        Full file path.

    """
    folder = filename[0].lower()
    return os.path.join(
        data_dir,
        "com.samsung.shealth.exercise",
        folder,
        filename,
    )


def calculate_pace_mm_ss(duration_minutes: float, distance_km: float) -> str:
    """Calculate pace in min:ss/km format.

    Args:
        duration_minutes: Duration in minutes.
        distance_km: Distance in kilometers.

    Returns:
        Formatted pace string or "-".

    """
    if distance_km <= 0 or duration_minutes <= 0:
        return "-"

    pace_min_per_km = duration_minutes / distance_km
    pace_min = int(pace_min_per_km)
    pace_sec = int((pace_min_per_km - pace_min) * 60)
    return f"{pace_min}:{pace_sec:02d}/km"
