"""add license management fields

Revision ID: 20260728_0003
Revises: 20260724_0002
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260728_0003"
down_revision = "20260724_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("licenses") as batch_op:
        batch_op.alter_column("order_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("activation_type", sa.String(length=30), nullable=True, server_default="ea_account"))
        batch_op.add_column(sa.Column("allowed_mt_account_number", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("allowed_broker_server", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("device_fingerprint", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("activated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("mt_account_updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_checked_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_check_status", sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column("last_check_message", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.create_index("idx_licenses_status", "licenses", ["status"], unique=False)
    op.create_index("idx_licenses_user_product", "licenses", ["user_id", "product_id"], unique=False)

    op.create_table(
        "license_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("license_id", sa.Integer(), nullable=True),
        sa.Column("product_code", sa.String(length=255), nullable=True),
        sa.Column("mt_account_number", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("client_version", sa.String(length=50), nullable=True),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["license_id"], ["licenses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_license_checks_id"), "license_checks", ["id"], unique=False)
    op.create_index("idx_license_checks_lookup", "license_checks", ["license_id", "checked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_license_checks_lookup", table_name="license_checks")
    op.drop_index(op.f("ix_license_checks_id"), table_name="license_checks")
    op.drop_table("license_checks")

    op.drop_index("idx_licenses_user_product", table_name="licenses")
    op.drop_index("idx_licenses_status", table_name="licenses")

    with op.batch_alter_table("licenses") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("last_check_message")
        batch_op.drop_column("last_check_status")
        batch_op.drop_column("last_checked_at")
        batch_op.drop_column("mt_account_updated_at")
        batch_op.drop_column("activated_at")
        batch_op.drop_column("device_fingerprint")
        batch_op.drop_column("allowed_broker_server")
        batch_op.drop_column("allowed_mt_account_number")
        batch_op.drop_column("activation_type")
        batch_op.alter_column("order_id", existing_type=sa.Integer(), nullable=False)
