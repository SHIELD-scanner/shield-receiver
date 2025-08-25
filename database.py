"""Minimal database abstraction for the gRPC receiver service.

Provides DatabaseFactory.create_client() and a MongoDB client implementation
used by `grpc_receiver_service.py`.

This keeps the interface used in the service:
- connect()
- disconnect()
- upsert_resource(resource_type, uid, doc)
- delete_resource(resource_type, uid)
- upsert_namespace(uid, doc)
- delete_namespace(uid)

The implementation uses MONGO_URI and MONGO_DB environment variables.
"""

import os
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError
import psycopg2
from psycopg2.extras import Json


# Shared error messages
DB_NOT_CONNECTED = "Database not connected"


class MongoDatabaseClient:
    def __init__(self, uri: str | None = None, db_name: str | None = None):
        self.uri = uri or os.getenv("MONGO_URI")
        self.db_name = db_name or os.getenv("MONGO_DB", "shield")
        self.client: MongoClient | None = None
        self.db = None

    def connect(self) -> None:
        if self.client is not None:
            return
        if self.uri is None:
            raise RuntimeError("MONGO_URI is not set")

        # Short timeout so failures surface quickly during service startup
        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        # Verify connection
        self.client.admin.command("ping")
        self.db = self.client[self.db_name]

    def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None

    def upsert_resource(
        self, resource_type: str, uid: str, doc: dict[str, Any]
    ) -> bool:
        if self.db is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            coll = self.db[resource_type]
            # Use uid as the document _id so deletes/upserts are straightforward
            doc_to_save = dict(doc)
            doc_to_save["_id"] = uid
            coll.replace_one({"_id": uid}, doc_to_save, upsert=True)
            return True
        except PyMongoError:
            return False

    def delete_resource(self, resource_type: str, uid: str) -> bool:
        if self.db is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            coll = self.db[resource_type]
            res = coll.delete_one({"_id": uid})
            return res.deleted_count > 0
        except PyMongoError:
            return False

    def upsert_namespace(self, uid: str, doc: dict[str, Any]) -> bool:
        # Namespace documents are stored in a dedicated collection named "namespace"
        return self.upsert_resource("namespace", uid, doc)

    def delete_namespace(self, uid: str) -> bool:
        return self.delete_resource("namespace", uid)


class DatabaseFactory:
    @staticmethod
    def create_client():
        db_type = os.getenv("DATABASE_TYPE", "mongo").lower()
        if db_type == "mongo":
            return MongoDatabaseClient()
        if db_type == "postgres" or db_type == "postgresql":
            return PostgresDatabaseClient()
        raise RuntimeError(f"Unsupported DATABASE_TYPE: {db_type}")


class PostgresDatabaseClient:

    """Postgres implementation of the simple database client used by the service.

    This stores resource documents as JSONB in a `resources` table and
    namespaces in a `namespaces` table. The client will create the tables
    on first connect if they do not exist.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db_name: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.host = host or os.getenv("POSTGRES_HOST", "localhost")
        self.port = port or int(os.getenv("POSTGRES_PORT", "5432"))
        self.db_name = db_name or os.getenv("POSTGRES_DB", "shield")
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "")

        self.conn: psycopg2.extensions.connection | None = None

    def connect(self) -> None:
        if self.conn is not None:
            return
        if not self.db_name:
            raise RuntimeError("POSTGRES_DB is not set")

        # Short connect timeout so failures surface quickly
        conn_str = (
            f"host={self.host} port={self.port} dbname={self.db_name} user={self.user} password={self.password}"
        )
        try:
            self.conn = psycopg2.connect(conn_str, connect_timeout=5)
            self.conn.autocommit = True
            # Ensure tables exist
            with self.conn.cursor() as cur:
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
        except Exception as e:
            # Normalize exceptions to RuntimeError so callers behave similarly
            raise RuntimeError(f"Failed to connect to Postgres: {e}") from e

    def disconnect(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def upsert_resource(self, resource_type: str, uid: str, doc: dict[str, Any]) -> bool:
        if self.conn is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO resources (uid, resource_type, data)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (uid) DO UPDATE SET
                        resource_type = EXCLUDED.resource_type,
                        data = EXCLUDED.data
                    """,
                    (uid, resource_type, Json(doc)),
                )
            return True
        except Exception:
            return False

    def delete_resource(self, resource_type: str, uid: str) -> bool:
        if self.conn is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            with self.conn.cursor() as cur:
                # Ensure we only delete the intended resource type
                cur.execute(
                    "DELETE FROM resources WHERE uid = %s AND resource_type = %s",
                    (uid, resource_type),
                )
                return cur.rowcount > 0
        except Exception:
            return False

    def upsert_namespace(self, uid: str, doc: dict[str, Any]) -> bool:
        if self.conn is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO namespaces (uid, data)
                    VALUES (%s, %s)
                    ON CONFLICT (uid) DO UPDATE SET data = EXCLUDED.data
                    """,
                    (uid, Json(doc)),
                )
            return True
        except Exception:
            return False

    def delete_namespace(self, uid: str) -> bool:
        if self.conn is None:
            raise RuntimeError(DB_NOT_CONNECTED)
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM namespaces WHERE uid = %s", (uid,))
                return cur.rowcount > 0
        except Exception:
            return False
