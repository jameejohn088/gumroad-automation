"""Database migration test: alembic upgrade head on a FRESH database creates
every table. This proves the migration chain is complete and runnable."""
import os

from alembic import command
from alembic.config import Config


def test_alembic_upgrade_head_fresh_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "fresh.db")
    url = "sqlite:" + "///" + db_path
    monkeypatch.setenv("DATABASE_URL", url)

    cfg = Config(os.path.join(os.getcwd(), "alembic.ini"))
    command.upgrade(cfg, "head")

    from sqlalchemy import create_engine, inspect
    eng = create_engine(url)
    try:
        tables = set(inspect(eng).get_table_names())
    finally:
        eng.dispose()
    expected = {
        "users", "refresh_tokens", "password_reset_tokens",
        "email_verification_tokens", "gumroad_accounts", "gumroad_credentials",
        "products", "variants", "offer_codes", "sales", "customers",
        "subscribers", "licenses", "webhook_subscriptions", "webhook_events",
        "automation_rules", "automation_conditions", "automation_actions",
        "automation_executions", "scheduled_jobs", "job_executions",
        "sync_history", "notifications", "activity_logs", "error_logs",
        "app_settings", "email_verification_codes", "alembic_version",
    }
    missing = expected - tables
    assert not missing, f"missing tables: {missing}"
