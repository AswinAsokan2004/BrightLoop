# BrightLoop

Subscription management for Brightloop Software: a React frontend connected to the existing
FastAPI/PostgreSQL backend for plans, subscriptions, recurring billing, payments and reports.
Python dependencies are managed with [uv](https://docs.astral.sh/uv/); the frontend uses Node.js 22+ and npm.

## Backend setup

Start Docker Desktop or Colima before running Docker Compose. Run these from the repository root.

```bash
cp .env.example .env        # then set POSTGRES_PASSWORD and JWT_SECRET
uv sync                     # create .venv and install dependencies
docker compose up -d        # start Postgres
uv run alembic upgrade head # create tables (+ sample data)

# Sign-up only creates customers, so create the first admin from the command line
uv run python -m app.scripts.create_admin --name "Your Name" --email admin@brightloop.com

uv run fastapi dev app/main.py   # API on http://localhost:8000
```

## Frontend setup

Keep the backend running on port 8000. Open a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 and sign in with the admin account created above. Public signup creates
customer accounts, whose navigation is restricted to their profile, subscriptions and invoices.
Seeded accounts have placeholder hashes and cannot log in until a real password is set.

Vite proxies `/api` requests to `http://127.0.0.1:8000`. The Figma configuration file is no longer
required. If an earlier Vite server was running, stop it with Control+C and restart it.
For a different API server, set `API_PROXY_TARGET` in `frontend/.env` or the shell. For a deployed
frontend use a reverse proxy for `/api`, or set `VITE_API_BASE_URL` to the full backend `/api` URL
and configure backend `CORS_ORIGINS` accordingly. Never put JWT secrets or DB credentials in Vite variables.

The frontend includes authentication/refresh/reset, role-based navigation, record creation/editing,
variants and attributes, quotation templates, subscription transitions and renewal, billing runs,
invoice confirmation/cancellation/email/printing, payment recording and live revenue reports.
Invoice amounts are taken from backend Decimal strings. Payment entry records an existing payment;
it does not charge a card or integrate a payment gateway.

## Checks

```bash
uv run pytest                  # pricing/date tests plus isolated API workflow tests
cd frontend
npm test                       # API client tests, including concurrent token refresh
npm run build                  # TypeScript check and production bundle
```

Default API workflow tests use a disposable SQLite adapter. To verify the actual documented
PostgreSQL setup and locking behavior, start PostgreSQL and run from the root:

```bash
uv run pytest --postgres
# In this prepared workspace, the equivalent command is:
../analysis-venv/bin/python -m pytest --postgres
```

These tests create uniquely named `brightloop_test_*` databases, run the migrations and admin
CLI there, exercise the API, then remove only those test databases. Your normal application's
records are not changed. The database role must have permission to create databases. Connection
settings come from `.env`; CI can override them with `TEST_POSTGRES_HOST`, `TEST_POSTGRES_PORT`,
`TEST_POSTGRES_USER`, `TEST_POSTGRES_PASSWORD` and `TEST_POSTGRES_DB` (the existing admin connection DB).
PostgreSQL tests are explicitly skipped unless `--postgres` is supplied.

For browser automation, run in `frontend/`:

```bash
npx playwright install chromium
npm run test:e2e
```

Playwright automatically starts and stops a disposable SQLite-backed fixture API on 8100 and
Vite on 5174. It refuses to reuse already-running servers on those ports and does not use your
API on 8000. No manual fixture server startup is needed. `BRIGHTLOOP_TEST_PYTHON` can point to a
Python environment with the backend dependencies (otherwise it checks `.venv`, this workspace's
prepared environment, then `python3`). With an existing Chrome installation on this Mac:

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run test:e2e
```

The test-only admin is `integration@example.com` / `Integration!Pass123`; customer and staff
credentials are in `tests/browser_api.py`. Those accounts exist only in the fixture database.
Read [the testing guide](docs/TESTING.md) for coverage and isolation details.

New to the project? Read the [knowledge transfer guide](docs/KNOWLEDGE_TRANSFER.md): why each API
exists and how the code is layered.

Interactive API docs: http://localhost:8000/docs. Log in with `POST /api/auth/login`, then click
**Authorize** and paste the `access_token`.

## Project layout

```
frontend/        React UI, API client and browser/client tests
app/
  routes/        HTTP layer: role checks, request/response shapes, calls a service
  services/      Business rules and transactions (billing engine, state machine, pricing)
  repositories/  Database queries only, no business rules or commits
  models/        SQLAlchemy models (mirror the Alembic migrations)
  schemas/       Pydantic request/response models and validation
  core/          Settings, database session, security, email, error handling
  scripts/       create_admin, run_billing (for cron)
migrations/      Alembic migrations
tests/           Pricing/period tests and isolated API workflow tests
```

## Roles

| Role | Can do |
|---|---|
| Admin | Everything, including staff accounts, products, plans, taxes and discounts |
| Staff | Customers, quotations, subscriptions, invoices, payments, billing runs, reports |
| Customer | Portal only (`/api/portal/...`): own subscriptions and invoices; pause, resume or close own subscriptions |

## Billing

`POST /api/billing/run` (or `uv run python -m app.scripts.run_billing` from cron) invoices every
active subscription whose `next_invoice_date` has arrived.

- **Never twice:** a unique `(subscription_id, period_start)` constraint, plus a row lock per
  subscription. Running it repeatedly, or several runs at once, is safe.
- **Never skipped:** after downtime, one run creates every missed period.
- **Discounts** apply automatically while valid and stop when expired or used up.
- **Invoice lines snapshot** prices, names and tax rates, so later catalog changes never alter
  old invoices.

Example cron entry (every night at 01:00):

```
0 1 * * *  cd /path/to/BrightLoop && uv run python -m app.scripts.run_billing
```

## Email

With `SMTP_HOST` unset (the default in development), emails such as password resets and invoices
are printed to the server log instead of being sent. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`
and `SMTP_PASSWORD` in `.env` to send real email.

## Common commands

| Task | Command |
|---|---|
| Run the API (auto-reload) | `uv run fastapi dev app/main.py` |
| Run tests | `uv run pytest` |
| Run billing now | `uv run python -m app.scripts.run_billing` |
| Add a dependency | `uv add <package>` |
| Add a dev dependency | `uv add --dev <package>` |
| Run a script | `uv run <file.py>` |
| Stop Postgres | `docker compose down` |
| Stop and delete DB data | `docker compose down -v` |
| Postgres shell | `docker compose exec db psql -U brightloop -d brightloop` |
| Apply all migrations | `uv run alembic upgrade head` |
| Schema only, no sample data | `uv run alembic upgrade 0001` |
| Undo last migration | `uv run alembic downgrade -1` |
| Drop everything | `uv run alembic downgrade base` |
| New migration | `uv run alembic revision -m "message"` |
| Current version | `uv run alembic current` |

## Viewing the database in DBeaver

1. Start DBeaver from the app menu, or run `dbeaver-ce &` in a terminal.
2. Click **Database → New Database Connection**, choose **PostgreSQL**, click **Next**, and enter:

   | Field | Value |
   |---|---|
   | Host | `localhost` |
   | Port | `5432` |
   | Database | `brightloop` |
   | Username | `brightloop` |
   | Password | the `POSTGRES_PASSWORD` value from your `.env` |

3. Tick **Save password**, click **Test Connection** (download the driver if asked), then click **Finish**.
4. Browse the tables under **brightloop → Databases → brightloop → Schemas → public → Tables**. To see the diagram, right-click **Tables** and choose **View Diagram**.

If you changed the values in `.env`, use those instead. Postgres must be running (`docker compose up -d`).

## Quotation and subscription workspace

Open **Subscriptions** and select a record to view `/subscriptions/{id}`. Customer accounts use
`/portal/subscriptions/{id}`. The workspace shows named customer/plan information, quotation
validity, agreed product/variant lines with tax and discount breakdowns, plan policies and billing
dates. Overview, Invoices and Activity tabs keep contract details, linked invoices and state
history together. Quotation Templates remains a separate configuration screen.

Available actions follow state, role and plan policy. Confirmation, activation, pause/resume,
closure, renewal and next-period invoicing use the existing service rules. Confirmation dialogs
explain consequential actions. Quotes can be edited only in draft/quotation, and expired quotes
must return to draft before a fresh quotation can be confirmed. Preview totals reflect the last
saved calculation; invoices remain authoritative and recalculate discounts/taxes at billing time.

Subscription read responses now include named, scoped customer/plan/payment-term context and
product/variant/actor labels. The portal invoice list accepts `subscription_id` while retaining
customer ownership filters. These changes are additive and require no database migration.

### Invoice details workspace

Open **Invoices** and select an invoice to view its full page at `/invoices/{id}`.
Customers use `/portal/invoices/{id}` and have read-only access to their own invoices.
The page shows billing dates, customer contact details, the linked subscription, itemized
amounts/taxes, balances, payment history and invoice timestamps. Internal users can confirm,
cancel, send or print an invoice and record partial or full payments according to its state.
Email delivery uses the existing server email configuration. No database migration is required.

### Finance overview

Internal users can open **Overview** or **Reports** for a unified finance workspace.
Search customer/plan names, choose a currency and date range, and click **Apply filters**.
Summary cards drill into paginated invoice balances, recent payments and active subscriptions.
Invoice and subscription links open their full detail pages; the applied filters and page positions
are saved in the URL for reload/back navigation. **Clear filters** restores the unfiltered view.

Totals are separated by currency, without exchange-rate conversion. Invoice dates filter invoiced,
outstanding and overdue amounts; receipt dates filter collections. Active subscriptions and
normalized untaxed MRR reflect the current portfolio, independently of the date range.
New read-only endpoints: `/api/reports/finance` and `/api/reports/options` (admin/staff only).
Restart the backend to load the new routes. No database migration is needed.
