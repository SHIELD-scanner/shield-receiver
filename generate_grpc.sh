#!/bin/bash

# Generate gRPC client code from proto file for the receiver service
echo "Generating gRPC code for receiver service..."

python -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    sync_service.proto

echo "gRPC code generated successfully!"
echo "Generated files:"
echo "  - sync_service_pb2.py"
echo "  - sync_service_pb2_grpc.py"
