"""add email otp table

Revision ID: 20260724_0002
Revises: 20260718_0001
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260724_0002"
down_revision = "20260718_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_otps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_otps_id"), "email_otps", ["id"], unique=False)
    op.create_index(op.f("ix_email_otps_email"), "email_otps", ["email"], unique=False)
    op.create_index(op.f("ix_email_otps_purpose"), "email_otps", ["purpose"], unique=False)
    op.create_index("idx_email_otps_lookup", "email_otps", ["email", "purpose", "consumed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_email_otps_lookup", table_name="email_otps")
    op.drop_index(op.f("ix_email_otps_purpose"), table_name="email_otps")
    op.drop_index(op.f("ix_email_otps_email"), table_name="email_otps")
    op.drop_index(op.f("ix_email_otps_id"), table_name="email_otps")
    op.drop_table("email_otps")
