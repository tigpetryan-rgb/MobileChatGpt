"""project agent budget guardrails

Revision ID: 0003_project_budgets
Revises: 0002_agent_run_payloads
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_project_budgets"
down_revision = "0002_agent_run_payloads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("reserved_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "project_budgets",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("max_total_tokens", sa.Integer(), nullable=False),
        sa.Column("max_run_tokens", sa.Integer(), nullable=False),
        sa.Column("max_concurrent_runs", sa.Integer(), nullable=False),
        sa.Column("used_tokens", sa.Integer(), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("project_budgets")
    op.drop_column("agent_runs", "reserved_tokens")
