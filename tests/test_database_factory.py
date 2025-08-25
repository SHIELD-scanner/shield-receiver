import os

from database import DatabaseFactory, MongoDatabaseClient, PostgresDatabaseClient


def test_factory_defaults_to_mongo():
    if "DATABASE_TYPE" in os.environ:
        del os.environ["DATABASE_TYPE"]
    client = DatabaseFactory.create_client()
    assert isinstance(client, MongoDatabaseClient)


def test_factory_returns_postgres():
    os.environ["DATABASE_TYPE"] = "postgres"
    client = DatabaseFactory.create_client()
    assert isinstance(client, PostgresDatabaseClient)
