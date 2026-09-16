"""add levels to academic templates

Revision ID: 706d3ef1acd5
Revises: ebc907ffb9f0
Create Date: 2026-09-16 16:07:56.605749

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "706d3ef1acd5"
down_revision: Union[str, Sequence[str], None] = "ebc907ffb9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "academic_templates",
        sa.Column(
            "levels",
            postgresql.ARRAY(sa.String(length=50)),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
    )

    op.execute(
        """
        UPDATE academic_templates
        SET levels = ARRAY['NURSERY', 'PRIMARY']
        WHERE name = 'Nursery & Primary';
        """
    )

    op.execute(
        """
        UPDATE academic_templates
        SET levels = ARRAY['SECONDARY']
        WHERE name = 'Secondary';
        """
    )

    op.execute(
        """
        UPDATE academic_templates
        SET levels = ARRAY['PRIMARY']
        WHERE name = 'Primary';
        """
    )

    op.execute(
        """
        UPDATE academic_templates
        SET levels = ARRAY['NURSERY', 'PRIMARY', 'SECONDARY']
        WHERE name = 'Nursery, Primary & Secondary';
        """
    )

    op.alter_column(
        "academic_templates",
        "levels",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column(
        "academic_templates",
        "levels",
    )
