"""change name to title

Revision ID: dd92cfa3fb59
Revises: 7ae563a149ce
Create Date: 2026-07-07 19:36:16.967877

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd92cfa3fb59'
down_revision: Union[str, Sequence[str], None] = '7ae563a149ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "products",
        "name",
        new_column_name="title",
        existing_type=sa.String(length=80),
        existing_nullable=False,
    )
    op.drop_index("ix_products_name")
    op.create_index("ix_products_title", "products", ["title"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "products",
        "title",
        new_column_name="name",
        existing_type=sa.String(length=80),
        existing_nullable=False,
    )
    op.drop_index("ix_products_title")
    op.create_index("ix_products_name", "products", ["name"], unique=False)
