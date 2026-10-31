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

This includes the normal tests and six PostgreSQL cases:

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

6. Reproduce the seeded admin’s placeholder-password login rejection, set a real password through
   the prompted CLI, verify successful admin login, then change the password and verify the old
   password is rejected without creating a duplicate user.

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

## Subscription workspace coverage

`tests/test_subscription_workspace.py` verifies named detail data, readable plan policies for
portal owners, restricted related-invoice filtering, expired quotation revision and line tax
information. The PostgreSQL suite also exercises the expanded read schemas against real PostgreSQL.

`frontend/tests/subscriptions.test.mjs` checks plan/role/state action availability, inclusive quote
validity dates, renewal eligibility, and exact Decimal-string preview arithmetic. The browser suite
covers the full-page route/reload/back behavior, template-based pricing, editing without losing
custom descriptions/taxes, linked invoices, actor history, pause/resume/renew/close confirmations,
expired-quote blocking and customer-only scoped reads. The expiry display case intercepts a detail
response to exercise the UI; backend expiry rejection is tested separately against actual services.

## Login regression coverage

The browser suite checks that an incorrect password produces the API’s `Invalid email or password`
message, leaves the user signed out, retains the email, and allows a successful retry. The real
PostgreSQL setup regression above uses only disposable test accounts and databases.

GitHub login and commit-author configuration are developer workstation settings, rather than
application behavior; they are verified separately and are not embedded in automated app tests.

## Invoice workspace coverage

`frontend/tests/invoice-details.spec.ts` exercises the full invoice route, reload and browser back,
customer names and subscription links, partial and full payment, overpayment rejection with form
retention, payment notes, cancellation confirmation and cancelled-state restrictions. It also checks
customer-scoped reads, hidden write actions, rejection of another customer's invoice and mobile
page overflow. The existing integration flow continues to verify printable invoices and collections.
Invoice lines and totals use server-calculated invoice amounts; customer contact information is read
from the linked subscription's current customer record.

Additional invoice regressions cover the overdue warning, customer invoice printing, and email
confirmation/cancellation, failure display and successful retry. Email responses are intercepted
in the browser test so no real email is sent; invoice/payment/ownership flows use the isolated API.
