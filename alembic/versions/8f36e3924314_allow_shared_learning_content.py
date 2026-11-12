"""allow shared learning content

Revision ID: 8f36e3924314
Revises: b6d2ca072580
Create Date: 2026-11-12 11:55:26.615028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f36e3924314'
down_revision: Union[str, Sequence[str], None] = 'b6d2ca072580'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "lesson_learning_contents",
        "school_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "lesson_learning_contents",
        "school_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
