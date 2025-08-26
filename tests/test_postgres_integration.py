import os
import time

import pytest
import psycopg2
from psycopg2.extras import Json


def wait_for_postgres(dsn, timeout=30):
    start = time.time()
    while True:
        try:
            conn = psycopg2.connect(dsn, connect_timeout=1)
            conn.close()
            return True
        except Exception:
            if time.time() - start > timeout:
                return False
            time.sleep(0.5)


def test_upsert_and_delete_resource_with_postgres():
    # Use docker-compose postgres service defaults
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    db = os.getenv("POSTGRES_DB", "shield")
    user = os.getenv("POSTGRES_USER", "shield")
    password = os.getenv("POSTGRES_PASSWORD", "password")

    dsn = f"host={host} port={port} dbname={db} user={user} password={password}"

    if not wait_for_postgres(dsn, timeout=3):
        pytest.skip("Postgres not available, skipping integration test")

    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            # Create tables if not present (same schema as runtime client)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS resources (
                    uid TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    data JSONB NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS namespaces (
                    uid TEXT PRIMARY KEY,
                    data JSONB NOT NULL
                )
                """
            )

            uid = "test-resource-1"
            resource_type = "pod"
            doc = {"_name": "testpod", "data": {"k": "v"}}

            # Upsert
            cur.execute(
                "INSERT INTO resources (uid, resource_type, data) VALUES (%s, %s, %s) "
                "ON CONFLICT (uid) DO UPDATE SET resource_type = EXCLUDED.resource_type, data = EXCLUDED.data",
                (uid, resource_type, Json(doc)),
            )

            # Verify
            cur.execute("SELECT data FROM resources WHERE uid = %s", (uid,))
            row = cur.fetchone()
            assert row is not None
            assert row[0]["_name"] == "testpod"

            # Delete
            cur.execute("DELETE FROM resources WHERE uid = %s AND resource_type = %s", (uid, resource_type))
            assert cur.rowcount == 1

    finally:
        conn.close()
