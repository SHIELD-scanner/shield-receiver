"""
Example gRPC Receiver Service

This is a sample implementation of the gRPC receiver service that handles
the data sent from the shield controller and writes it to MongoDB.

This service should be deployed separately from the controller.
"""

import grpc
import json
import logging
from concurrent import futures
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import the generated gRPC classes
import sync_service_pb2
import sync_service_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grpc-receiver")

# MongoDB configuration from environment variables
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.environ.get("MONGO_DB", "shield")

# Initialize MongoDB client
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]


class SyncServiceServicer(sync_service_pb2_grpc.SyncServiceServicer):
    """gRPC service implementation that receives data and stores it in MongoDB"""

    def SyncResource(self, request, context):
        """Handle resource sync requests"""
        try:
            # Parse the JSON data
            data = json.loads(request.data_json)
            
            # Create the document structure (same as original controller)
            doc = {
                "_event_type": request.event_type,
                "_resource_type": request.resource_type,
                "_namespace": request.namespace,
                "_name": request.name,
                "_cluster": request.cluster,
                "data": data,
            }
            
            # Store in MongoDB
            uid = request.uid
            if not uid:
                logger.warning(f"No UID for {request.resource_type} {request.name}")
                return sync_service_pb2.SyncResourceResponse(
                    success=False,
                    message="No UID provided"
                )
            
            # Replace/upsert the document
            db[request.resource_type].replace_one(
                {"_uid": uid}, 
                {"_uid": uid, **doc}, 
                upsert=True
            )
            
            logger.info(f"Synced {request.resource_type} {request.name} ({request.event_type})")
            
            return sync_service_pb2.SyncResourceResponse(
                success=True,
                message=f"Successfully synced {request.resource_type} {request.name}"
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
            
            # Create the document structure (same as original controller)
            doc = {
                "_event_type": request.event_type,
                "_resource_type": "namespace",
                "_name": request.name,
                "_cluster": request.cluster,
                "data": data,
            }
            
            # Store in MongoDB
            uid = request.uid
            if not uid:
                logger.warning(f"No UID for namespace {request.name}")
                return sync_service_pb2.SyncNamespaceResponse(
                    success=False,
                    message="No UID provided"
                )
            
            # Replace/upsert the document
            db["namespaces"].replace_one(
                {"_uid": uid}, 
                {"_uid": uid, **doc}, 
                upsert=True
            )
            
            logger.info(f"Synced namespace {request.name} ({request.event_type})")
            
            return sync_service_pb2.SyncNamespaceResponse(
                success=True,
                message=f"Successfully synced namespace {request.name}"
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
    logger.info(f"Connected to MongoDB: {MONGO_URI}")
    
    # Keep the server running
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
