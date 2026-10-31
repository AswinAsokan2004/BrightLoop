# BrightLoop test suite

## Fast checks (no running database required)

From the repository root:

```bash
uv run pytest
```

In this prepared local checkout, `../analysis-venv/bin/python -m pytest` is equivalent.
The default suite covers pricing, calendar anchors, and API workflows using SQLite. PostgreSQL
checks are collected but skipped by default. The SQLite adapter is test-only; production uses
the existing PostgreSQL database layer.

From `frontend/`:

```bash
npm test
npm run build
```

The client tests exercise token refresh deduplication, expired sessions, public auth requests,
server validation, HTTP 204 responses, reference pagination, decimal strings and connection errors.
The build also runs TypeScript validation.

## Real PostgreSQL startup and workflow checks

Start PostgreSQL, then run:

```bash
uv run pytest --postgres
```

This includes the normal tests and five PostgreSQL cases:

1. Apply `alembic upgrade head`; verify schema, seed records, billing uniqueness constraint and
   safe repeat migration execution.
2. Run `app.scripts.create_admin`; claim the seeded admin, create a new admin, verify password
   hashing and email normalization, and reject weak passwords without creating an account.
3. Launch the actual Uvicorn command on a temporary local port; check `/health`, authentication
   requirements, HTTP login and `/api/auth/me`; stop the process afterward.
4. Complete the API lifecycle on PostgreSQL: signup, catalog/tax/discount setup, subscription
   activation, invoice, partial/full payment, printable invoice, scoped reports, customer access,
   refresh rotation and logout.
5. Race four billing runs and two payments. Assert each billing period is invoiced exactly once
   and concurrent payment attempts cannot exceed the outstanding balance.

The fixture reads admin connection settings from `.env`, creates a random
`brightloop_test_<uuid>` database for each test, and always closes/removes it in fixture cleanup.
It never runs migrations, admin commands, or workflow requests against the application database.
Database deletion is restricted to the exact generated test name. Credentials are not printed.
PostgreSQL workers run in separate processes to prevent SQLite compiler overrides leaking into
these checks.

The connecting database role needs `CREATEDB` permission. CI can supply `TEST_POSTGRES_HOST`,
`TEST_POSTGRES_PORT`, `TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD`, and `TEST_POSTGRES_DB`.
The last variable identifies the existing database used for the administrative connection;
all test operations use new databases created alongside it.

Connection, migration and permission failures fail the explicitly requested PostgreSQL suite;
they are not silently converted to passes or skips. Tests do not start or stop the user's Docker
containers and do not change the user's admin password.

## Browser checks

Install dependencies with `npm ci` in `frontend/`. Install Chromium once:

```bash
npx playwright install chromium
npm run test:e2e
```

Alternatively set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` to an installed browser executable.
`BRIGHTLOOP_TEST_PYTHON` can select a Python environment with backend dependencies installed.

Playwright manages both test servers automatically: isolated fixture API on 8100 and Vite on 5174.
It does not reuse running servers and does not connect to the application API on 8000. The fixture
uses a temporary SQLite database with known fake accounts and deletes it when the server exits.
The special `/__test__/health` route exists only in the test fixture entrypoint, not production.

The browser cases cover persisted customer creation, subscription state changes, invoice creation,
confirmation and payment, printable invoice opening, payment/report/billing screens, session reload,
customer navigation, staff write restrictions, and failed-form validation/input retention.

Ports 8100 and 5174 must be free. These checks validate browser interactions with actual backend
services, but they do not validate PostgreSQL locks; those are covered separately by `--postgres`.
