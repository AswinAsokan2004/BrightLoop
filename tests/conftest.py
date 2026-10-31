"""PostgreSQL tests opt in explicitly and use disposable databases, never application data."""
import os
import re
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from dotenv import dotenv_values
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
TEST_PASSWORD = "Test!Bootstrap123"


def pytest_addoption(parser):
    parser.addoption("--postgres", action="store_true", help="Run isolated PostgreSQL migration/startup/workflow tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--postgres"):
        for item in items:
            if item.get_closest_marker("postgres"):
                item.add_marker(pytest.mark.skip(reason="Pass --postgres to run disposable PostgreSQL tests"))


def run_command(env, *args, input_text=None):
    result = subprocess.run(
        [sys.executable, *args], cwd=ROOT, env=env, input=input_text,
        text=True, capture_output=True, timeout=90, start_new_session=input_text is not None,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture
def postgres_env():
    # SQLite tests set process-wide test defaults. Read .env independently so they cannot
    # redirect this connection; explicit TEST_POSTGRES_* values allow CI configuration.
    local = dotenv_values(ROOT / ".env")
    values = {
        key: os.environ.get("TEST_" + key) or local.get(key) or default
        for key, default in {
            "POSTGRES_HOST": "localhost", "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "brightloop", "POSTGRES_PASSWORD": "",
            "POSTGRES_DB": "brightloop",
        }.items()
    }
    try:
        admin = psycopg.connect(
            host=values["POSTGRES_HOST"], port=values["POSTGRES_PORT"],
            user=values["POSTGRES_USER"], password=values["POSTGRES_PASSWORD"],
            dbname=values["POSTGRES_DB"], autocommit=True, connect_timeout=5,
        )
    except psycopg.Error as exc:
        pytest.fail(f"Cannot reach PostgreSQL for --postgres tests: {exc}", pytrace=False)
    database = "brightloop_test_" + uuid.uuid4().hex
    created = False
    try:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
        created = True
        env = {**os.environ, **values, "POSTGRES_DB": database, "JWT_SECRET": secrets.token_urlsafe(48)}
        yield env
    finally:
        try:
            if created:
                # Do not turn this into a generic drop helper. Only our unique test DB may be dropped.
                assert re.fullmatch(r"brightloop_test_[0-9a-f]{32}", database)
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))
        finally:
            admin.close()


@pytest.fixture
def migrated_postgres(postgres_env):
    run_command(postgres_env, "-m", "alembic", "upgrade", "head")
    return postgres_env


@pytest.fixture
def bootstrapped_postgres(migrated_postgres):
    run_command(
        migrated_postgres, "-m", "app.scripts.create_admin", "--name", "Startup Test Admin",
        "--email", "admin@brightloop.com", "--password", TEST_PASSWORD,
    )
    return migrated_postgres
