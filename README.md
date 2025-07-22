# Shield gRPC Receiver Service

A gRPC service that receives security scan data from Shield Controllers and stores it in MongoDB.

## Overview

This service acts as a receiver for the Shield Controller's gRPC-based architecture. Instead of the controller directly connecting to MongoDB, it sends data via gRPC to this receiver service, which then handles all MongoDB operations.

## Architecture

```
Shield Controller → gRPC Receiver Service → MongoDB
```

## Quick Start

### Prerequisites

- Python 3.8+
- MongoDB instance
- Access to Shield Controller's gRPC calls

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB connection details
   ```

3. **Generate gRPC code:**
   ```bash
   python -m grpc_tools.protoc \
       --proto_path=. \
       --python_out=. \
       --grpc_python_out=. \
       sync_service.proto
   ```

4. **Run the service:**
   ```bash
   python grpc_receiver_service.py
   ```

## Configuration

Configure the service using environment variables in a `.env` file:

```bash
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=shield

# gRPC Server Configuration  
GRPC_PORT=50051
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/` |
| `MONGO_DB` | MongoDB database name | `shield` |
| `GRPC_PORT` | Port for gRPC server | `50051` |

## API Reference

The service implements the gRPC service defined in `sync_service.proto`:

### SyncResource

Receives and stores Kubernetes security resources.

**Request:**
- `event_type`: Type of Kubernetes event (e.g., "ADDED", "MODIFIED", "DELETED")
- `resource_type`: Type of security resource (e.g., "vulnerabilityreports")
- `namespace`: Kubernetes namespace
- `name`: Resource name
- `cluster`: Cluster identifier
- `uid`: Kubernetes UID
- `data_json`: JSON-serialized resource data

**Response:**
- `success`: Boolean indicating success
- `message`: Status message

### SyncNamespace

Receives and stores Kubernetes namespace information.

**Request:**
- `event_type`: Type of Kubernetes event
- `name`: Namespace name
- `cluster`: Cluster identifier
- `uid`: Kubernetes UID
- `data_json`: JSON-serialized namespace data

**Response:**
- `success`: Boolean indicating success
- `message`: Status message

## Data Storage

The service stores data in MongoDB with the following structure:

### Resource Documents
```json
{
  "_uid": "kubernetes-uid",
  "_event_type": "ADDED",
  "_resource_type": "vulnerabilityreports",
  "_namespace": "default",
  "_name": "resource-name",
  "_cluster": "cluster-name",
  "data": { /* original Kubernetes resource data */ }
}
```

### Namespace Documents
```json
{
  "_uid": "kubernetes-uid",
  "_event_type": "ADDED", 
  "_resource_type": "namespace",
  "_name": "namespace-name",
  "_cluster": "cluster-name",
  "data": { /* original Kubernetes namespace data */ }
}
```

## Development

### Project Structure

```
grpc-receiver/
├── grpc_receiver_service.py    # Main service implementation
├── sync_service.proto          # gRPC service definition
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
└── README.md                  # This file
```

### Generated Files

After running the protoc command, these files will be generated:
- `sync_service_pb2.py` - Protobuf message classes
- `sync_service_pb2_grpc.py` - gRPC service classes

### Adding New Features

1. Update `sync_service.proto` if changing the gRPC interface
2. Regenerate gRPC code using the protoc command
3. Update `grpc_receiver_service.py` with new logic
4. Update MongoDB schema documentation if needed

## Deployment

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Generate gRPC code
RUN python -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    sync_service.proto

EXPOSE 50051

CMD ["python", "grpc_receiver_service.py"]
```

### Kubernetes

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shield-grpc-receiver
spec:
  replicas: 2
  selector:
    matchLabels:
      app: shield-grpc-receiver
  template:
    metadata:
      labels:
        app: shield-grpc-receiver
    spec:
      containers:
      - name: receiver
        image: shield-grpc-receiver:latest
        ports:
        - containerPort: 50051
        env:
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: mongodb-secret
              key: uri
        - name: MONGO_DB
          value: "shield"
---
apiVersion: v1
kind: Service
metadata:
  name: shield-grpc-receiver
spec:
  selector:
    app: shield-grpc-receiver
  ports:
  - port: 50051
    targetPort: 50051
  type: ClusterIP
```

## Monitoring

The service logs important events:
- Successful/failed resource syncs
- MongoDB connection status
- gRPC server startup/shutdown

Example log output:
```
INFO:grpc-receiver:gRPC Receiver Service started on port 50051
INFO:grpc-receiver:Connected to MongoDB: mongodb://localhost:27017/
INFO:grpc-receiver:Synced vulnerabilityreports test-resource (ADDED)
```

## Troubleshooting

### Common Issues

**Service won't start:**
- Check MongoDB connection string in `.env`
- Verify port 50051 is available
- Ensure gRPC code is generated

**No data in MongoDB:**
- Check MongoDB credentials and network access
- Verify Shield Controller is configured with correct gRPC endpoint
- Review service logs for error messages

**Connection refused from controller:**
- Verify service is running and accessible
- Check firewall/network policies
- Confirm gRPC port configuration matches

## Security Considerations

- Use MongoDB authentication in production
- Consider TLS for gRPC communication
- Implement proper logging without exposing sensitive data
- Use network policies to restrict access to the service

## License

This project follows the same license as the Shield Controller project.
