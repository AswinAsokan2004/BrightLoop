import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_conninfo() -> str:
    return (
        f"host={os.environ['POSTGRES_HOST']} "
        f"port={os.environ['POSTGRES_PORT']} "
        f"dbname={os.environ['POSTGRES_DB']} "
        f"user={os.environ['POSTGRES_USER']} "
        f"password={os.environ['POSTGRES_PASSWORD']}"
    )


def main():
    with psycopg.connect(get_conninfo()) as conn:
        version = conn.execute("SELECT version()").fetchone()[0]
        print(f"Connected to Postgres: {version}")


if __name__ == "__main__":
    main()
