"""add public fields to travel_plans

Revision ID: 20251106_01
Revises: 
Create Date: 2025-11-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251106_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns with server defaults for existing rows
    op.add_column(
        "travel_plans",
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "travel_plans",
        sa.Column("public_at", sa.DateTime(), nullable=True),
    )
    # Optional: drop server_default to leave application-level default
    op.alter_column("travel_plans", "is_public", server_default=None)


def downgrade() -> None:
    op.drop_column("travel_plans", "public_at")
    op.drop_column("travel_plans", "is_public")