"""Migration integrity tests.

These tests run against a throwaway Postgres database on the local instance —
they never touch the dev database.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = os.path.join(os.path.dirname(__file__), os.pardir)

# Base connection for creating/dropping temp databases
_ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DB_URL",
    # Default assumes running inside Docker compose where Postgres is at 'db'
    "postgresql+psycopg2://postgres:postgres@db:5432/postgres",
)


def _temp_db_name() -> str:
    return f"test_migrations_{uuid.uuid4().hex[:8]}"


def _alembic_cmd(db_url: str, *args: str) -> None:
    """Run alembic in a subprocess with DATABASE_URL overridden."""
    env = {**os.environ, "DATABASE_URL": db_url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.path.abspath(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} failed:\n{result.stderr}"
        )


@pytest.fixture()
def migration_db():
    """Create a throwaway Postgres database, yield engine + url, then drop it."""
    db_name = _temp_db_name()
    admin_engine = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name}"))
    admin_engine.dispose()

    db_url = _ADMIN_URL.rsplit("/", 1)[0] + f"/{db_name}"
    engine = create_engine(db_url)
    yield engine, db_url

    engine.dispose()
    # Drop the temp database
    admin_engine = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
        ))
        conn.execute(text(f"DROP DATABASE {db_name}"))
    admin_engine.dispose()


class TestMigrationIntegrity:
    """Verify that Alembic migrations alone produce the expected schema."""

    def test_upgrade_creates_scrape_jobs(self, migration_db):
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "scrape_jobs" in tables, (
            "scrape_jobs table should exist after alembic upgrade head"
        )

    def test_scrape_jobs_columns(self, migration_db):
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("scrape_jobs")}
        expected = {
            "id", "work_id", "start", "end", "status",
            "progress", "total", "created_at", "updated_at",
        }
        assert expected <= columns, (
            f"Missing columns: {expected - columns}"
        )

    def test_scrape_jobs_indexes(self, migration_db):
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        indexed_columns = set()
        for idx in inspector.get_indexes("scrape_jobs"):
            for col in idx["column_names"]:
                indexed_columns.add(col)
        assert "work_id" in indexed_columns
        assert "status" in indexed_columns

    def test_downgrade_removes_scrape_jobs(self, migration_db):
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")
        _alembic_cmd(db_url, "downgrade", "a21635cef4ae")

        inspector = inspect(engine)
        assert "scrape_jobs" not in inspector.get_table_names()

    def test_upgrade_downgrade_upgrade_cycle(self, migration_db):
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")
        _alembic_cmd(db_url, "downgrade", "a21635cef4ae")
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        assert "scrape_jobs" in inspector.get_table_names()

    def test_upgrade_idempotent_when_table_exists(self, migration_db):
        """Simulate a DB where create_all() already created scrape_jobs."""
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "a21635cef4ae")
        # Manually create the table (simulating prior create_all behavior)
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE scrape_jobs (
                    id SERIAL PRIMARY KEY,
                    work_id INTEGER NOT NULL,
                    start NUMERIC(12,4) NOT NULL,
                    "end" NUMERIC(12,4) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    progress INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                )
            """))
        # Now run the migration — should not fail
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        assert "scrape_jobs" in inspector.get_table_names()

    def test_all_expected_tables_exist(self, migration_db):
        """Smoke test: all core tables are created by migrations alone."""
        engine, db_url = migration_db
        _alembic_cmd(db_url, "upgrade", "head")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "works", "chapters", "scrape_jobs",
            "chapter_translations", "translation_segments",
        }
        missing = expected_tables - tables
        assert not missing, f"Tables missing from Alembic-only DB: {missing}"
