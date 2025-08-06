"""Example gRPC Receiver Service.

This is a sample implementation of the gRPC receiver service that handles
the data sent from the shield controller and writes it to the configured database.

This service should be deployed separately from the controller.
"""

import sentry_sdk

import json
import logging
import os
from concurrent import futures

import grpc
from dotenv import load_dotenv

import sync_service_pb2
import sync_service_pb2_grpc
from database import DatabaseFactory

# Load environment variables from .env file
load_dotenv()

sentry_dsn = os.environ.get("DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grpc-receiver")

# Initialize database client
try:
    db_client = DatabaseFactory.create_client()
    db_client.connect()
    logger.info(f"Connected to {os.environ.get('DATABASE_TYPE', 'mongo').upper()} database")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    raise


class SyncServiceServicer(sync_service_pb2_grpc.SyncServiceServicer):

    """gRPC service implementation that receives data and stores it in the configured database"""

    def SyncResource(self, request, context):
        """Handle resource sync requests"""
        try:
            # Parse the JSON data
            data = json.loads(request.data_json)
            
            if request.event_type == "DELETED": 
                success = db_client.delete_resource(request.resource_type, request.uid)
                if success:
                    logger.info(f"Deleted {request.resource_type} {request.name} ({request.event_type})")
                    return sync_service_pb2.SyncResourceResponse(
                        success=True,
                        message=f"Successfully deleted {request.resource_type} {request.name}"
                    )
                else:
                    return sync_service_pb2.SyncResourceResponse(
                        success=False,
                        message=f"Failed to delete {request.resource_type} {request.name}"
                    )

            # Create the document structure (same as original controller)
            doc = {
                "_event_type": request.event_type,
                "_resource_type": request.resource_type,
                "_namespace": request.namespace,
                "_name": request.name,
                "_cluster": request.cluster,
                "data": data,
            }

            # Store in database
            uid = request.uid
            if not uid:
                logger.warning(f"No UID for {request.resource_type} {request.name}")
                return sync_service_pb2.SyncResourceResponse(
                    success=False,
                    message="No UID provided"
                )

            # Upsert the document
            success = db_client.upsert_resource(request.resource_type, uid, doc)
            
            if success:
                logger.info(f"Synced {request.resource_type} {request.name} ({request.event_type})")
                return sync_service_pb2.SyncResourceResponse(
                    success=True,
                    message=f"Successfully synced {request.resource_type} {request.name}"
                )
            else:
                return sync_service_pb2.SyncResourceResponse(
                    success=False,
                    message=f"Failed to sync {request.resource_type} {request.name}"
                )

        except Exception as e:
            logger.error(f"Error syncing resource: {e}")
            return sync_service_pb2.SyncResourceResponse(
                success=False,
                message=f"Error: {str(e)}"
            )

    def SyncNamespace(self, request, context):
        """Handle namespace sync requests"""
        try:
            # Parse the JSON data
            data = json.loads(request.data_json)
            
            if request.event_type == "DELETED": 
                success = db_client.delete_namespace(request.uid)
                if success:
                    logger.info(f"Deleted namespace {request.name} ({request.event_type})")
                    return sync_service_pb2.SyncNamespaceResponse(
                        success=True,
                        message=f"Successfully deleted namespace {request.name}"
                    )
                else:
                    return sync_service_pb2.SyncNamespaceResponse(
                        success=False,
                        message=f"Failed to delete namespace {request.name}"
                    )

            # Create the document structure (same as original controller)
            doc = {
                "_event_type": request.event_type,
                "_resource_type": "namespace",
                "_name": request.name,
                "_cluster": request.cluster,
                "data": data,
            }

            # Store in database
            uid = request.uid
            if not uid:
                logger.warning(f"No UID for namespace {request.name}")
                return sync_service_pb2.SyncNamespaceResponse(
                    success=False,
                    message="No UID provided"
                )

            # Upsert the document
            success = db_client.upsert_namespace(uid, doc)
            
            if success:
                logger.info(f"Synced namespace {request.name} ({request.event_type})")
                return sync_service_pb2.SyncNamespaceResponse(
                    success=True,
                    message=f"Successfully synced namespace {request.name}"
                )
            else:
                return sync_service_pb2.SyncNamespaceResponse(
                    success=False,
                    message=f"Failed to sync namespace {request.name}"
                )

        except Exception as e:
            logger.error(f"Error syncing namespace: {e}")
            return sync_service_pb2.SyncNamespaceResponse(
                success=False,
                message=f"Error: {str(e)}"
            )


def serve():
    """Start the gRPC server"""
    port = os.environ.get("GRPC_PORT", "50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the servicer to the server
    sync_service_pb2_grpc.add_SyncServiceServicer_to_server(
        SyncServiceServicer(), server
    )

    # Listen on all interfaces
    server.add_insecure_port(f'[::]:{port}')

    # Start the server
    server.start()
    logger.info(f"gRPC Receiver Service started on port {port}")
    logger.info(f"Using {os.environ.get('DATABASE_TYPE', 'mongo').upper()} database")

    # Keep the server running
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        db_client.disconnect()
        server.stop(0)


if __name__ == "__main__":
    serve()