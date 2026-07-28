"""add protected product file metadata

Revision ID: 20260728_0004
Revises: 20260728_0003
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0004"
down_revision = "20260728_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("product_file_path", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("product_file_name", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("product_file_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("product_file_uploaded_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("product_file_uploaded_at")
        batch_op.drop_column("product_file_size")
        batch_op.drop_column("product_file_name")
        batch_op.drop_column("product_file_path")
