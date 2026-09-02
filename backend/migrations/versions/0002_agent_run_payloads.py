"""persist manager run input/output metadata

Revision ID: 0002_agent_run_payloads
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_agent_run_payloads"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("input_snapshot", sa.JSON(), nullable=True))
    op.add_column("agent_runs", sa.Column("output", sa.JSON(), nullable=True))
    op.add_column("agent_runs", sa.Column("usage", sa.JSON(), nullable=True))
    op.add_column("agent_runs", sa.Column("error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "error")
    op.drop_column("agent_runs", "usage")
    op.drop_column("agent_runs", "output")
    op.drop_column("agent_runs", "input_snapshot")
