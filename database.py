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
            raise RuntimeError("Database not connected")
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
            raise RuntimeError("Database not connected")
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
        raise RuntimeError(f"Unsupported DATABASE_TYPE: {db_type}")
