import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_creates_static_schema(tmp_path):
    db_path = tmp_path / "migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{db_path}")
    tables = set(inspect(engine).get_table_names())
    expected = {
        "projects",
        "plans",
        "tasks",
        "task_dependencies",
        "approvals",
        "checkpoints",
        "agent_runs",
        "tool_calls",
        "audit_events",
        "project_budgets",
        "device_pairings",
        "devices",
        "device_commands",
        "alembic_version",
    }
    assert expected.issubset(tables)
    columns = {c["name"] for c in inspect(engine).get_columns("agent_runs")}
    assert {"input_snapshot", "output", "usage", "error", "reserved_tokens"}.issubset(columns)
    command_columns = {c["name"] for c in inspect(engine).get_columns("device_commands")}
    assert {"device_id", "tool_call_id", "lease_expires_at", "attempt_count"}.issubset(command_columns)
    with engine.connect() as conn:
        revision = conn.execute(text("select version_num from alembic_version")).scalar_one()
    assert revision == "0004_device_bridge"
