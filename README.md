# BrightLoop

Python project managed with [uv](https://docs.astral.sh/uv/), using PostgreSQL in Docker.

## Setup

```bash
cp .env.example .env        # then edit credentials
uv sync                     # create .venv and install dependencies
docker compose up -d        # start Postgres
uv run main.py              # check the database connection
uv run alembic upgrade head # create tables (+ sample data)
```

## Common commands

| Task | Command |
|---|---|
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
