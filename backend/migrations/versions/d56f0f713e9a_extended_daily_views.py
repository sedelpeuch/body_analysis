"""extended daily views

Trois vues, une par famille qui n'est pas déjà à grain quotidien :
nutrition_detail (par repas), sleep_session (par nuit), et les trois
signaux continus hrv/heart_rate/stress regroupés dans une seule vue.

La frontière de journée est Europe/Paris, comme les vues du plan 1.

Revision ID: d56f0f713e9a
Revises: 85c1a0f3b4e2
Create Date: 2026-09-02 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d56f0f713e9a"
down_revision: Union[str, Sequence[str], None] = "85c1a0f3b4e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DAY_TZ = "Europe/Paris"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_nutrition_detail AS
        SELECT
            (consumed_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            SUM(calories) AS calories,
            SUM(protein) AS protein,
            SUM(total_fat) AS total_fat,
            SUM(carbohydrate) AS carbohydrate,
            SUM(dietary_fiber) AS dietary_fiber,
            SUM(sugar) AS sugar,
            SUM(sodium) AS sodium,
            COUNT(*) AS entry_count
        FROM nutrition_detail
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_nutrition_detail_day "
        "ON mv_daily_nutrition_detail (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_sleep AS
        SELECT DISTINCT ON (day)
            day,
            efficiency,
            efficiency_with_latency,
            physical_recovery,
            mental_recovery,
            deep_score,
            rem_score,
            sleep_duration
        FROM (
            SELECT
                (COALESCE(ended_at, started_at) AT TIME ZONE '{DAY_TZ}')::date AS day,
                started_at,
                efficiency,
                efficiency_with_latency,
                physical_recovery,
                mental_recovery,
                deep_score,
                rem_score,
                sleep_duration
            FROM sleep_session
        ) AS nightly
        ORDER BY day, started_at DESC
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_mv_daily_sleep_day ON mv_daily_sleep (day)")

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_vitals AS
        SELECT
            day,
            AVG(avg_heart_rate) AS avg_heart_rate,
            AVG(avg_stress_score) AS avg_stress_score,
            AVG(avg_sdnn) AS avg_sdnn
        FROM (
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                mean_heart_rate AS avg_heart_rate,
                NULL::double precision AS avg_stress_score,
                NULL::double precision AS avg_sdnn
            FROM heart_rate_reading
            UNION ALL
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                NULL::double precision,
                score,
                NULL::double precision
            FROM stress_reading
            UNION ALL
            SELECT
                (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                NULL::double precision,
                NULL::double precision,
                avg_sdnn
            FROM hrv_reading
        ) AS combined
        GROUP BY 1
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_mv_daily_vitals_day ON mv_daily_vitals (day)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_vitals")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_sleep")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_nutrition_detail")
