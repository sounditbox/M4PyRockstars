"""enforce nonnegative stock

Revision ID: b7c9e2a41d6f
Revises: 1ad5c4e62185
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c9e2a41d6f"
down_revision: Union[str, Sequence[str], None] = "1ad5c4e62185"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Ensure direct database writes cannot create negative stock."""
    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column(
            "stock_count",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=sa.text("0"),
        )
        batch_op.create_check_constraint(
            "ck_products_stock_count_nonnegative",
            "stock_count >= 0",
        )


def downgrade() -> None:
    """Remove the stock constraint and database default."""
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint(
            "ck_products_stock_count_nonnegative",
            type_="check",
        )
        batch_op.alter_column(
            "stock_count",
            existing_type=sa.Integer(),
            existing_nullable=False,
            server_default=None,
        )
