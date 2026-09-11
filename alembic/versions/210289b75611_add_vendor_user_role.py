"""add vendor user role

Revision ID: 210289b75611
Revises: 3f67b8326321
Create Date: 2026-09-11 02:17:40.000578

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "210289b75611"
down_revision: Union[str, Sequence[str], None] = "3f67b8326321"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'VENDOR'")


def downgrade():
    # PostgreSQL does not support removing a value directly from an enum.
    # Leave this migration irreversible unless you specifically need
    # an enum-rebuild downgrade.
    pass
