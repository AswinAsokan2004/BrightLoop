# BrightLoop

Subscription management API for Brightloop Software: plans, subscriptions, recurring billing,
payments and revenue reporting. Built with FastAPI and PostgreSQL, managed with [uv](https://docs.astral.sh/uv/).

## Branch

Dev

## Setup

```bash
cp .env.example .env        # then set POSTGRES_PASSWORD and JWT_SECRET
uv sync                     # create .venv and install dependencies
docker compose up -d        # start Postgres
uv run alembic upgrade head # create tables (+ sample data)

# Sign-up only creates customers, so create the first admin from the command line
uv run python -m app.scripts.create_admin --name "Your Name" --email admin@brightloop.com

uv run fastapi dev app/main.py   # API on http://localhost:8000
```

New to the project? Read the [knowledge transfer guide](docs/KNOWLEDGE_TRANSFER.md): why each API
exists and how the code is layered.

Interactive API docs: http://localhost:8000/docs. Log in with `POST /api/auth/login`, then click
**Authorize** and paste the `access_token`.

## Project layout

```
app/
  routes/        HTTP layer: role checks, request/response shapes, calls a service
  services/      Business rules and transactions (billing engine, state machine, pricing)
  repositories/  Database queries only, no business rules or commits
  models/        SQLAlchemy models (mirror the Alembic migrations)
  schemas/       Pydantic request/response models and validation
  core/          Settings, database session, security, email, error handling
  scripts/       create_admin, run_billing (for cron)
migrations/      Alembic migrations
tests/           Unit tests for pricing and billing-period maths
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
