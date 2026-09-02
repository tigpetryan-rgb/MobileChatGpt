"""device registration and command bridge

Revision ID: 0004_device_bridge
Revises: 0003_project_budgets
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_device_bridge"
down_revision = "0003_project_budgets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_pairings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_device_pairings_code_hash", "device_pairings", ["code_hash"])
    op.create_index("ix_device_pairings_expires_at", "device_pairings", ["expires_at"])

    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_devices_token_hash", "devices", ["token_hash"])
    op.create_index("ix_devices_status", "devices", ["status"])

    op.create_table(
        "device_commands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("tool_call_id", sa.String(length=36), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_call_id"], ["tool_calls.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_call_id", name="uq_device_command_tool_call"),
    )
    op.create_index("ix_device_commands_device_id", "device_commands", ["device_id"])
    op.create_index("ix_device_commands_project_id", "device_commands", ["project_id"])
    op.create_index("ix_device_commands_tool_call_id", "device_commands", ["tool_call_id"])
    op.create_index("ix_device_commands_status", "device_commands", ["status"])
    op.create_index("ix_device_commands_lease_expires_at", "device_commands", ["lease_expires_at"])


def downgrade() -> None:
    op.drop_index("ix_device_commands_lease_expires_at", table_name="device_commands")
    op.drop_index("ix_device_commands_status", table_name="device_commands")
    op.drop_index("ix_device_commands_tool_call_id", table_name="device_commands")
    op.drop_index("ix_device_commands_project_id", table_name="device_commands")
    op.drop_index("ix_device_commands_device_id", table_name="device_commands")
    op.drop_table("device_commands")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_index("ix_devices_token_hash", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_device_pairings_expires_at", table_name="device_pairings")
    op.drop_index("ix_device_pairings_code_hash", table_name="device_pairings")
    op.drop_table("device_pairings")
