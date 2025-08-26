import json
from unittest.mock import MagicMock, patch
import sync_service_pb2
import sync_service_pb2_grpc
from grpc_receiver_service import SyncServiceServicer


class DummyContext:
    def __init__(self):
        self._code = None
        self._details = None

    def set_code(self, code):
        self._code = code

    def set_details(self, details):
        self._details = details


@patch("grpc_receiver_service.db_client")
def test_syncresource_added(mock_db_client):
    # Setup request
    req = sync_service_pb2.SyncResourceRequest(
        event_type="ADDED",
        resource_type="pod",
        namespace="default",
        name="mypod",
        cluster="test-cluster",
        uid="uid-123",
        data_json=json.dumps({"foo": "bar"}),
    )

    # mock upsert_resource to return True
    mock_db_client.upsert_resource.return_value = True

    servicer = SyncServiceServicer()
    resp = servicer.SyncResource(req, DummyContext())

    assert resp.success is True
    assert "Successfully synced" in resp.message


@patch("grpc_receiver_service.db_client")
def test_syncresource_deleted(mock_db_client):
    req = sync_service_pb2.SyncResourceRequest(
        event_type="DELETED",
        resource_type="pod",
        namespace="default",
        name="mypod",
        cluster="test-cluster",
        uid="uid-123",
        data_json=json.dumps({}),
    )

    mock_db_client.delete_resource.return_value = True

    servicer = SyncServiceServicer()
    resp = servicer.SyncResource(req, DummyContext())

    assert resp.success is True
    assert "Successfully deleted" in resp.message


@patch("grpc_receiver_service.db_client")
def test_syncresource_no_uid(mock_db_client):
    req = sync_service_pb2.SyncResourceRequest(
        event_type="ADDED",
        resource_type="pod",
        namespace="default",
        name="mypod",
        cluster="test-cluster",
        uid="",
        data_json=json.dumps({}),
    )

    servicer = SyncServiceServicer()
    resp = servicer.SyncResource(req, DummyContext())

    assert resp.success is False
    assert resp.message == "No UID provided"


@patch("grpc_receiver_service.db_client")
def test_syncnamespace_added(mock_db_client):
    req = sync_service_pb2.SyncNamespaceRequest(
        event_type="ADDED",
        name="default",
        cluster="test-cluster",
        uid="ns-1",
        data_json=json.dumps({"n": "v"}),
    )

    mock_db_client.upsert_namespace.return_value = True

    servicer = SyncServiceServicer()
    resp = servicer.SyncNamespace(req, DummyContext())

    assert resp.success is True
    assert "Successfully synced namespace" in resp.message


@patch("grpc_receiver_service.db_client")
def test_syncnamespace_deleted(mock_db_client):
    req = sync_service_pb2.SyncNamespaceRequest(
        event_type="DELETED",
        name="default",
        cluster="test-cluster",
        uid="ns-1",
        data_json=json.dumps({}),
    )

    mock_db_client.delete_namespace.return_value = True

    servicer = SyncServiceServicer()
    resp = servicer.SyncNamespace(req, DummyContext())

    assert resp.success is True
    assert "Successfully deleted namespace" in resp.message


@patch("grpc_receiver_service.db_client")
def test_syncnamespace_no_uid(mock_db_client):
    req = sync_service_pb2.SyncNamespaceRequest(
        event_type="ADDED",
        name="default",
        cluster="test-cluster",
        uid="",
        data_json=json.dumps({}),
    )

    servicer = SyncServiceServicer()
    resp = servicer.SyncNamespace(req, DummyContext())

    assert resp.success is False
    assert resp.message == "No UID provided"
