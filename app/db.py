"""Tiny SQL migration runner (given): applies migrations/NNN_*.sql once each, in order.

python -m app.db          (or: make migrate)
"""

import glob
import os

from app.config import get_settings

MIGRATIONS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")


def migrate(database_url=None):
    import psycopg

    url = database_url or get_settings().database_url
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at timestamptz DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
        for path in sorted(glob.glob(os.path.join(MIGRATIONS, "*.sql"))):
            version = os.path.basename(path).split("_")[0]
            if version in done:
                continue
            with conn.transaction():
                conn.execute(open(path, encoding="utf-8").read())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            print(f"applied migration {os.path.basename(path)}")


if __name__ == "__main__":
    migrate()
