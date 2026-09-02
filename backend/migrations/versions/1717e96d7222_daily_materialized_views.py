"""daily materialized views

Les vues portent les agrégats quotidiens qui, sans elles, seraient les
requêtes les plus coûteuses de l'application (tableau de bord, heatmaps).

La frontière de journée est Europe/Paris : regrouper en UTC ferait basculer
dans la veille tout ce qui est consommé avant 2 h du matin en été.

Chaque vue reçoit un index unique sur day, sans lequel REFRESH ...
CONCURRENTLY est refusé par PostgreSQL.

Revision ID: 1717e96d7222
Revises: afc9036d5272
Create Date: 2026-09-02 19:12:05.802651

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1717e96d7222'
down_revision: Union[str, Sequence[str], None] = 'afc9036d5272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DAY_TZ = "Europe/Paris"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_body AS
        SELECT DISTINCT ON (day)
            day,
            weight_kg,
            body_fat_pct,
            body_fat_mass_kg,
            skeletal_muscle_mass_kg,
            fat_free_mass_kg,
            total_body_water_kg,
            basal_metabolic_rate_kcal
        FROM (
            SELECT
                (measured_at AT TIME ZONE '{DAY_TZ}')::date AS day,
                measured_at,
                weight_kg,
                body_fat_pct,
                body_fat_mass_kg,
                skeletal_muscle_mass_kg,
                fat_free_mass_kg,
                total_body_water_kg,
                basal_metabolic_rate_kcal
            FROM body_measurement
        ) AS daily
        ORDER BY day, measured_at DESC
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_body_day ON mv_daily_body (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_nutrition AS
        SELECT
            (consumed_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            SUM(calories) AS calories,
            COUNT(*) AS entry_count
        FROM nutrition_entry
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_nutrition_day ON mv_daily_nutrition (day)"
    )

    op.execute(
        f"""
        CREATE MATERIALIZED VIEW mv_daily_training AS
        SELECT
            (started_at AT TIME ZONE '{DAY_TZ}')::date AS day,
            COUNT(*) AS session_count,
            SUM(duration_ms) AS duration_ms,
            SUM(calories_kcal) AS calories_kcal,
            SUM(distance_m) AS distance_m
        FROM workout
        GROUP BY 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_mv_daily_training_day ON mv_daily_training (day)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_training")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_nutrition")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_body")
