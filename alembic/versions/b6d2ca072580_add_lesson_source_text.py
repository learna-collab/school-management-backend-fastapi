"""add lesson source text

Revision ID: b6d2ca072580
Revises: 8275525e2554
Create Date: 2026-11-12 11:49:46.737016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6d2ca072580'
down_revision: Union[str, Sequence[str], None] = '8275525e2554'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "lessons",
        sa.Column("source_text", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("lessons", "source_text")
