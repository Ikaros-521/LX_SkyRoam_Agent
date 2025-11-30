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
    # 检查列是否存在，如果不存在才添加
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('travel_plans')]
    
    # Add columns with server defaults for existing rows (如果不存在)
    if 'is_public' not in columns:
        op.add_column(
            "travel_plans",
            sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        # Optional: drop server_default to leave application-level default
        op.alter_column("travel_plans", "is_public", server_default=None)
    
    if 'public_at' not in columns:
        op.add_column(
            "travel_plans",
            sa.Column("public_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("travel_plans", "public_at")
    op.drop_column("travel_plans", "is_public")