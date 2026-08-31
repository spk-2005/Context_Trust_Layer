import asyncio
import os
from datetime import datetime, timezone
from uuid import UUID

import psycopg

# Database connection params from environment or defaults
DB_HOST = os.getenv("POSTGRES_SERVER", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5433" if DB_HOST == "localhost" else "5432"))
DB_USER = os.getenv("POSTGRES_USER", "context_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "context_password")
DB_NAME = os.getenv("POSTGRES_DB", "context_trust")


def seed_database():
    """Seeds sample data into all 14 Context Trust Layer tables."""
    conn_str = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"
    print(f"Connecting to database: {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}...")

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Read and execute database/init.sql if available
            init_sql_path = os.path.join(os.path.dirname(__file__), "..", "..", "database", "init.sql")
            if os.path.exists(init_sql_path):
                with open(init_sql_path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                print("Executing schema DDL and seed data...")
                cur.execute(sql_content)
                conn.commit()
                print("Successfully populated all 14 tables with sample data!")
            else:
                print(f"Error: init.sql not found at {init_sql_path}")


if __name__ == "__main__":
    seed_database()
