"""widen nutrition_detail meal_type to integer

Revision ID: 23418da46b5f
Revises: d56f0f713e9a
Create Date: 2026-09-03 08:24:49.072035

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23418da46b5f'
down_revision: Union[str, Sequence[str], None] = 'd56f0f713e9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "nutrition_detail",
        "meal_type",
        existing_type=sa.SmallInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "nutrition_detail",
        "meal_type",
        existing_type=sa.Integer(),
        type_=sa.SmallInteger(),
        existing_nullable=True,
    )
