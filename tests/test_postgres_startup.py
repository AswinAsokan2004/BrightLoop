"""Exercises the documented migration/admin/API commands against real PostgreSQL."""
import json
import socket
import subprocess
import sys
import time

import bcrypt
import httpx
import psycopg
import pytest

from tests.conftest import ROOT, TEST_PASSWORD, run_command

pytestmark = pytest.mark.postgres


def connect(env):
    return psycopg.connect(
        host=env["POSTGRES_HOST"], port=env["POSTGRES_PORT"],
        user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"], dbname=env["POSTGRES_DB"],
    )


def test_migrations_create_schema_and_seed_once(migrated_postgres):
    with connect(migrated_postgres) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0002"
        tables = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'").fetchone()[0]
        assert tables == 33  # 32 domain tables plus Alembic's version table
        before = db.execute("SELECT count(*) FROM invoices").fetchone()[0]
        assert before > 0
        assert db.execute("SELECT count(*) FROM pg_constraint WHERE conname='uq_invoices_subscription_id_period_start'").fetchone()[0] == 1
    run_command(migrated_postgres, "-m", "alembic", "upgrade", "head")
    with connect(migrated_postgres) as db:
        assert db.execute("SELECT count(*) FROM invoices").fetchone()[0] == before


def test_admin_command_claims_seeded_account_and_creates_new_admin(bootstrapped_postgres):
    env = bootstrapped_postgres
    with connect(env) as db:
        name, role, active, password_hash = db.execute(
            "SELECT name, role, is_active, password_hash FROM users WHERE email=%s", ("admin@brightloop.com",)
        ).fetchone()
        assert (name, role, active) == ("Startup Test Admin", "admin", True)
        assert bcrypt.checkpw(TEST_PASSWORD.encode(), password_hash.encode())
    # Exercise the documented prompted-password path as well as the --password setup above.
    run_command(env, "-m", "app.scripts.create_admin", "--name", "New Admin", "--email", "NEW@Example.com", input_text=TEST_PASSWORD + "\n")
    with connect(env) as db:
        assert db.execute("SELECT role FROM users WHERE email=%s", ("new@example.com",)).fetchone()[0] == "admin"
    rejected = subprocess.run(
        [sys.executable, "-m", "app.scripts.create_admin", "--name", "Invalid", "--email", "invalid@example.com", "--password", "weak"],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=30,
    )
    assert rejected.returncode != 0
    assert "Password must have" in rejected.stderr
    with connect(env) as db:
        assert db.execute("SELECT count(*) FROM users WHERE email=%s", ("invalid@example.com",)).fetchone()[0] == 0


def test_uvicorn_startup_health_and_admin_login(bootstrapped_postgres, tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (tmp_path / "uvicorn.log").open("w+") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=bootstrapped_postgres, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False) as client:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if server.poll() is not None:
                        log.seek(0)
                        pytest.fail("Uvicorn exited before startup:\n" + log.read())
                    try:
                        response = client.get("/health")
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
                else:
                    pytest.fail("Uvicorn did not become healthy within 15 seconds")
                assert response.json() == {"status": "ok"}
                assert client.get("/api/customers").status_code == 401
                login = client.post("/api/auth/login", json={"email": "admin@brightloop.com", "password": TEST_PASSWORD})
                assert login.status_code == 200, login.text
                me = client.get("/api/auth/me", headers={"Authorization": "Bearer " + login.json()["access_token"]})
                assert me.status_code == 200 and me.json()["role"] == "admin"
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


@pytest.mark.parametrize("mode", ["workflow", "concurrency"])
def test_real_postgres_api(bootstrapped_postgres, mode):
    # Separate processes avoid leaking SQLite compiler/type overrides into PostgreSQL checks.
    result = run_command(bootstrapped_postgres, "-m", "tests.postgres_workflow", mode)
    assert json.loads(result.stdout)["passed"] == mode


def test_seeded_admin_login_requires_password_setup(migrated_postgres):
    """Reproduce the placeholder-password failure, then exercise the documented repair."""
    probe = '''
import json, os
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    response = client.post('/api/auth/login', json={
        'email': 'admin@brightloop.com', 'password': os.environ['LOGIN_PROBE_PASSWORD'],
    })
    result = {'status': response.status_code}
    if response.status_code == 200:
        me = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer ' + response.json()['access_token'],
        })
        result['role'] = me.json()['role']
    else:
        assert 'Invalid email or password' in response.text
        assert 'access_token' not in response.text
    print(json.dumps(result))
'''
    def login(password):
        result = run_command({**migrated_postgres, 'LOGIN_PROBE_PASSWORD': password}, '-c', probe)
        return json.loads(result.stdout)

    assert login(TEST_PASSWORD) == {'status': 401}
    run_command(
        migrated_postgres, '-m', 'app.scripts.create_admin',
        '--name', 'Claimed Admin', '--email', 'admin@brightloop.com',
        input_text=TEST_PASSWORD + '\n',
    )
    assert login(TEST_PASSWORD) == {'status': 200, 'role': 'admin'}
    replacement = 'Replacement!Pass456'
    run_command(
        migrated_postgres, '-m', 'app.scripts.create_admin',
        '--name', 'Claimed Admin', '--email', 'admin@brightloop.com',
        input_text=replacement + '\n',
    )
    assert login(TEST_PASSWORD) == {'status': 401}
    assert login(replacement) == {'status': 200, 'role': 'admin'}
    with connect(migrated_postgres) as db:
        assert db.execute("SELECT count(*) FROM users WHERE email='admin@brightloop.com'").fetchone()[0] == 1


def test_finance_with_thousands_of_records_responds_under_two_seconds(bootstrapped_postgres):
    result = run_command(bootstrapped_postgres, '-m', 'tests.finance_performance')
    measured = json.loads(result.stdout)
    assert measured['records_per_domain'] == 3000
    assert all(seconds < 2 for seconds in measured['seconds'])
    print('Finance PostgreSQL timings:', measured['seconds'])
