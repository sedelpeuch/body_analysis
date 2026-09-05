"""add workout source_updated_at for skip-unchanged reimport

Revision ID: f995d6c118bd
Revises: 23418da46b5f
Create Date: 2026-09-03 08:59:50.863017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f995d6c118bd'
down_revision: Union[str, Sequence[str], None] = '23418da46b5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workout",
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workout", "source_updated_at")
