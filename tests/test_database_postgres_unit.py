import os
from unittest.mock import MagicMock, patch

import pytest

from database import PostgresDatabaseClient


@patch("database.psycopg2.connect")
def test_postgres_connect_creates_tables(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    os.environ["POSTGRES_HOST"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "shield_test"
    os.environ["POSTGRES_USER"] = "user"
    os.environ["POSTGRES_PASSWORD"] = "pass"

    client = PostgresDatabaseClient()
    client.connect()

    # Ensure connect called
    mock_connect.assert_called()
    # Ensure table creation executed (cursor.execute called at least twice)
    assert mock_cursor.execute.call_count >= 2


@patch("database.psycopg2.connect")
def test_postgres_upsert_and_delete(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    client = PostgresDatabaseClient(host="h", port=1, db_name="d", user="u", password="p")
    client.connect()

    # Upsert returns True when no exception
    assert client.upsert_resource("pod", "uid-1", {"a": 1}) is True
    mock_cursor.execute.assert_called()

    # delete returns True when rowcount > 0
    mock_cursor.rowcount = 1
    assert client.delete_resource("pod", "uid-1") is True

    # delete returns False when rowcount == 0
    mock_cursor.rowcount = 0
    assert client.delete_resource("pod", "uid-1") is False


@patch("database.psycopg2.connect")
def test_postgres_namespace_upsert_delete(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    client = PostgresDatabaseClient(host="h", port=1, db_name="d", user="u", password="p")
    client.connect()

    assert client.upsert_namespace("ns-1", {"n": "v"}) is True

    mock_cursor.rowcount = 1
    assert client.delete_namespace("ns-1") is True


@patch("database.psycopg2.connect")
def test_postgres_connect_failure_propagates(mock_connect):
    mock_connect.side_effect = Exception("boom")
    client = PostgresDatabaseClient(host="h", port=1, db_name="d", user="u", password="p")
    with pytest.raises(RuntimeError):
        client.connect()
