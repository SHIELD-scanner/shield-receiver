import os
from unittest.mock import MagicMock, patch

import pytest

from database import MongoDatabaseClient


@patch("database.MongoClient")
def test_mongo_connect_and_upsert(mock_mongo_client):
    # Setup a fake pymongo client and collection
    mock_client_instance = MagicMock()
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_client_instance.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    mock_mongo_client.return_value = mock_client_instance

    os.environ["MONGO_URI"] = "mongodb://localhost:27017"
    os.environ["MONGO_DB"] = "shield_test"

    client = MongoDatabaseClient()
    client.connect()

    # Test upsert_resource
    res = client.upsert_resource("pods", "uid-1", {"a": 1})
    assert res is True
    mock_coll.replace_one.assert_called()

    # Test delete_resource
    mock_coll.delete_one.return_value.deleted_count = 1
    res = client.delete_resource("pods", "uid-1")
    assert res is True


def test_mongo_connect_missing_uri():
    if "MONGO_URI" in os.environ:
        del os.environ["MONGO_URI"]
    client = MongoDatabaseClient(uri=None)
    with pytest.raises(RuntimeError):
        client.connect()


@patch("database.MongoClient")
def test_namespace_upsert_and_delete(mock_mongo_client):
    mock_client_instance = MagicMock()
    mock_db = MagicMock()
    mock_coll = MagicMock()
    mock_client_instance.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_coll
    mock_mongo_client.return_value = mock_client_instance

    os.environ["MONGO_URI"] = "mongodb://localhost:27017"
    os.environ["MONGO_DB"] = "shield_test"

    client = MongoDatabaseClient()
    client.connect()

    # upsert namespace
    res = client.upsert_namespace("ns-1", {"_name": "default"})
    assert res is True
    mock_coll.replace_one.assert_called()

    # delete namespace
    mock_coll.delete_one.return_value.deleted_count = 1
    res = client.delete_namespace("ns-1")
    assert res is True
