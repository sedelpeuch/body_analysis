"""extended ingestion tables

Revision ID: 85c1a0f3b4e2
Revises: 1717e96d7222
Create Date: 2026-09-02 20:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "85c1a0f3b4e2"
down_revision: Union[str, Sequence[str], None] = "1717e96d7222"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_detail",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meal_type", sa.SmallInteger(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("calories", sa.Double(), nullable=True),
        sa.Column("protein", sa.Double(), nullable=True),
        sa.Column("total_fat", sa.Double(), nullable=True),
        sa.Column("saturated_fat", sa.Double(), nullable=True),
        sa.Column("trans_fat", sa.Double(), nullable=True),
        sa.Column("monosaturated_fat", sa.Double(), nullable=True),
        sa.Column("polysaturated_fat", sa.Double(), nullable=True),
        sa.Column("carbohydrate", sa.Double(), nullable=True),
        sa.Column("dietary_fiber", sa.Double(), nullable=True),
        sa.Column("sugar", sa.Double(), nullable=True),
        sa.Column("added_sugar", sa.Double(), nullable=True),
        sa.Column("cholesterol", sa.Double(), nullable=True),
        sa.Column("sodium", sa.Double(), nullable=True),
        sa.Column("potassium", sa.Double(), nullable=True),
        sa.Column("calcium", sa.Double(), nullable=True),
        sa.Column("iron", sa.Double(), nullable=True),
        sa.Column("vitamin_a", sa.Double(), nullable=True),
        sa.Column("vitamin_c", sa.Double(), nullable=True),
        sa.Column("vitamin_d", sa.Double(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_nutrition_detail_consumed_at"),
        "nutrition_detail",
        ["consumed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_nutrition_detail_meal_type"),
        "nutrition_detail",
        ["meal_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_nutrition_detail_source_uuid"),
        "nutrition_detail",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "energy_expenditure",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("rest_calorie", sa.Double(), nullable=True),
        sa.Column("active_calorie", sa.Double(), nullable=True),
        sa.Column("tef_calorie", sa.Double(), nullable=True),
        sa.Column("active_time_ms", sa.Integer(), nullable=True),
        sa.Column("total_exercise_calories", sa.Double(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_energy_expenditure_day"),
        "energy_expenditure",
        ["day"],
        unique=False,
    )
    op.create_index(
        op.f("ix_energy_expenditure_source_uuid"),
        "energy_expenditure",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "sleep_session",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_wake_up_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("efficiency", sa.Double(), nullable=True),
        sa.Column("efficiency_with_latency", sa.Double(), nullable=True),
        sa.Column("physical_recovery", sa.Integer(), nullable=True),
        sa.Column("mental_recovery", sa.Integer(), nullable=True),
        sa.Column("deep_score", sa.Integer(), nullable=True),
        sa.Column("rem_score", sa.Integer(), nullable=True),
        sa.Column("wake_score", sa.Integer(), nullable=True),
        sa.Column("nap_score", sa.Integer(), nullable=True),
        sa.Column("latency_score", sa.Integer(), nullable=True),
        sa.Column("sleep_latency", sa.Integer(), nullable=True),
        sa.Column("total_rem_duration", sa.Integer(), nullable=True),
        sa.Column("total_light_duration", sa.Integer(), nullable=True),
        sa.Column("sleep_duration", sa.Integer(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("has_sleep_data", sa.SmallInteger(), nullable=True),
        sa.Column("sleep_type", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sleep_session_started_at"),
        "sleep_session",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sleep_session_source_uuid"),
        "sleep_session",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "sleep_stage",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("sleep_source_uuid", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sleep_stage_sleep_source_uuid"),
        "sleep_stage",
        ["sleep_source_uuid"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sleep_stage_started_at"),
        "sleep_stage",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sleep_stage_source_uuid"),
        "sleep_stage",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "hrv_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avg_sdnn", sa.Double(), nullable=True),
        sa.Column("avg_rmssd", sa.Double(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_hrv_reading_started_at"),
        "hrv_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_hrv_reading_source_uuid"),
        "hrv_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "heart_rate_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mean_heart_rate", sa.Double(), nullable=True),
        sa.Column("min_heart_rate", sa.Double(), nullable=True),
        sa.Column("max_heart_rate", sa.Double(), nullable=True),
        sa.Column("heart_beat_count", sa.Integer(), nullable=True),
        sa.Column("tag_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_heart_rate_reading_started_at"),
        "heart_rate_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_heart_rate_reading_source_uuid"),
        "heart_rate_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "stress_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Double(), nullable=True),
        sa.Column("min_score", sa.Double(), nullable=True),
        sa.Column("max_score", sa.Double(), nullable=True),
        sa.Column("tag_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stress_reading_started_at"),
        "stress_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stress_reading_source_uuid"),
        "stress_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "respiratory_rate_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average", sa.Double(), nullable=True),
        sa.Column("lower_limit", sa.Double(), nullable=True),
        sa.Column("upper_limit", sa.Double(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_respiratory_rate_reading_started_at"),
        "respiratory_rate_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_respiratory_rate_reading_source_uuid"),
        "respiratory_rate_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "skin_temperature_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("temperature", sa.Double(), nullable=True),
        sa.Column("min_temperature", sa.Double(), nullable=True),
        sa.Column("max_temperature", sa.Double(), nullable=True),
        sa.Column("baseline", sa.Double(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skin_temperature_reading_started_at"),
        "skin_temperature_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_skin_temperature_reading_source_uuid"),
        "skin_temperature_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "oxygen_saturation_reading",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("spo2", sa.Double(), nullable=True),
        sa.Column("heart_rate", sa.Double(), nullable=True),
        sa.Column("tag_id", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_oxygen_saturation_reading_started_at"),
        "oxygen_saturation_reading",
        ["started_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_oxygen_saturation_reading_source_uuid"),
        "oxygen_saturation_reading",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "daily_activity",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=True),
        sa.Column("active_time_ms", sa.Integer(), nullable=True),
        sa.Column("calorie", sa.Double(), nullable=True),
        sa.Column("distance_m", sa.Double(), nullable=True),
        sa.Column("floor_count", sa.Integer(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("exercise_time_ms", sa.Integer(), nullable=True),
        sa.Column("run_time_ms", sa.Integer(), nullable=True),
        sa.Column("walk_time_ms", sa.Integer(), nullable=True),
        sa.Column("longest_active_time_ms", sa.Integer(), nullable=True),
        sa.Column("move_hourly_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_daily_activity_day"),
        "daily_activity",
        ["day"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_activity_source_uuid"),
        "daily_activity",
        ["source_uuid"],
        unique=True,
    )

    op.create_table(
        "step_daily_trend",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("source_uuid", sa.Text(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Double(), nullable=True),
        sa.Column("calorie", sa.Double(), nullable=True),
        sa.Column("speed", sa.Double(), nullable=True),
        sa.Column("source_type", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_step_daily_trend_day"),
        "step_daily_trend",
        ["day"],
        unique=False,
    )
    op.create_index(
        op.f("ix_step_daily_trend_source_uuid"),
        "step_daily_trend",
        ["source_uuid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_step_daily_trend_source_uuid"), table_name="step_daily_trend")
    op.drop_index(op.f("ix_step_daily_trend_day"), table_name="step_daily_trend")
    op.drop_table("step_daily_trend")

    op.drop_index(op.f("ix_daily_activity_source_uuid"), table_name="daily_activity")
    op.drop_index(op.f("ix_daily_activity_day"), table_name="daily_activity")
    op.drop_table("daily_activity")

    op.drop_index(
        op.f("ix_oxygen_saturation_reading_source_uuid"),
        table_name="oxygen_saturation_reading",
    )
    op.drop_index(
        op.f("ix_oxygen_saturation_reading_started_at"),
        table_name="oxygen_saturation_reading",
    )
    op.drop_table("oxygen_saturation_reading")

    op.drop_index(
        op.f("ix_skin_temperature_reading_source_uuid"),
        table_name="skin_temperature_reading",
    )
    op.drop_index(
        op.f("ix_skin_temperature_reading_started_at"),
        table_name="skin_temperature_reading",
    )
    op.drop_table("skin_temperature_reading")

    op.drop_index(
        op.f("ix_respiratory_rate_reading_source_uuid"),
        table_name="respiratory_rate_reading",
    )
    op.drop_index(
        op.f("ix_respiratory_rate_reading_started_at"),
        table_name="respiratory_rate_reading",
    )
    op.drop_table("respiratory_rate_reading")

    op.drop_index(op.f("ix_stress_reading_source_uuid"), table_name="stress_reading")
    op.drop_index(op.f("ix_stress_reading_started_at"), table_name="stress_reading")
    op.drop_table("stress_reading")

    op.drop_index(
        op.f("ix_heart_rate_reading_source_uuid"),
        table_name="heart_rate_reading",
    )
    op.drop_index(
        op.f("ix_heart_rate_reading_started_at"),
        table_name="heart_rate_reading",
    )
    op.drop_table("heart_rate_reading")

    op.drop_index(op.f("ix_hrv_reading_source_uuid"), table_name="hrv_reading")
    op.drop_index(op.f("ix_hrv_reading_started_at"), table_name="hrv_reading")
    op.drop_table("hrv_reading")

    op.drop_index(op.f("ix_sleep_stage_source_uuid"), table_name="sleep_stage")
    op.drop_index(op.f("ix_sleep_stage_started_at"), table_name="sleep_stage")
    op.drop_index(op.f("ix_sleep_stage_sleep_source_uuid"), table_name="sleep_stage")
    op.drop_table("sleep_stage")

    op.drop_index(op.f("ix_sleep_session_source_uuid"), table_name="sleep_session")
    op.drop_index(op.f("ix_sleep_session_started_at"), table_name="sleep_session")
    op.drop_table("sleep_session")

    op.drop_index(
        op.f("ix_energy_expenditure_source_uuid"),
        table_name="energy_expenditure",
    )
    op.drop_index(op.f("ix_energy_expenditure_day"), table_name="energy_expenditure")
    op.drop_table("energy_expenditure")

    op.drop_index(
        op.f("ix_nutrition_detail_source_uuid"),
        table_name="nutrition_detail",
    )
    op.drop_index(op.f("ix_nutrition_detail_meal_type"), table_name="nutrition_detail")
    op.drop_index(
        op.f("ix_nutrition_detail_consumed_at"),
        table_name="nutrition_detail",
    )
    op.drop_table("nutrition_detail")
