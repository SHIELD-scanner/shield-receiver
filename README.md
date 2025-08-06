# Shield gRPC Receiver Service

[![trivy](https://github.com/SHIELD-scanner/shield-receiver/actions/workflows/trivy.yml/badge.svg)](https://github.com/SHIELD-scanner/shield-receiver/actions/workflows/trivy.yml)
[![Build and Push Docker image](https://github.com/SHIELD-scanner/shield-receiver/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/SHIELD-scanner/shield-receiver/actions/workflows/docker-publish.yml)

A gRPC service that receives security scan data from Shield Controllers and stores it in your choice of MongoDB or PostgreSQL.

## Overview

This service acts as a receiver for the Shield Controller's gRPC-based architecture. Instead of the controller directly connecting to a database, it sends data via gRPC to this receiver service, which then handles all database operations using a configurable database backend.

## Architecture

```
Shield Controller → gRPC Receiver Service → Database (MongoDB or PostgreSQL)
```

## Database Support

The service supports two database backends:

- **MongoDB** - Document-oriented NoSQL database (default)
- **PostgreSQL** - Relational SQL database with JSONB support

Choose your database by setting the `DATABASE_TYPE` environment variable. See [DATABASES_CONFIG.md](DATABASES_CONFIG.md) for detailed configuration instructions.

## Quick Start

### Prerequisites

- Python 3.8+
- Database instance (MongoDB or PostgreSQL)
- Access to Shield Controller's gRPC calls

### Installation

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your database connection details
   # See DATABASES_CONFIG.md for detailed configuration options
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

Configure the service using environment variables in a `.env` file. The service supports both MongoDB and PostgreSQL backends.

### Quick Configuration Examples

**MongoDB (Default):**

```bash
DATABASE_TYPE=mongo
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=shield
GRPC_PORT=50051
```

**PostgreSQL:**

```bash
DATABASE_TYPE=postgres
POSTGRES_URI=postgresql://username:password@localhost:5432/shield
GRPC_PORT=50051
```

For detailed configuration options, see [DATABASES_CONFIG.md](DATABASES_CONFIG.md).

### Environment Variables

| Variable        | Description                    | Default                      |
| --------------- | ------------------------------ | ---------------------------- |
| `DATABASE_TYPE` | Database type (mongo/postgres) | `mongo`                      |
| `MONGO_URI`     | MongoDB connection string      | `mongodb://localhost:27017/` |
| `MONGO_DB`      | MongoDB database name          | `shield`                     |
| `POSTGRES_URI`  | PostgreSQL connection string   | -                            |
| `GRPC_PORT`     | Port for gRPC server           | `50051`                      |

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

The service stores data using a consistent schema across both database backends:

### MongoDB Storage

Data is stored in collections:

- **Resource Collections**: `{resource_type}` (e.g., `pods`, `deployments`, `services`)
- **Namespace Collection**: `namespaces`

### PostgreSQL Storage

Data is stored in structured tables:

- **Resources Table**: Contains all resource types with JSONB data column
- **Namespaces Table**: Contains namespace information with JSONB data column

### Document Structure

Regardless of the database backend, documents follow this structure:

**Resource Documents:**

```json
{
  "_uid": "kubernetes-uid",
  "_event_type": "ADDED",
  "_resource_type": "vulnerabilityreports",
  "_namespace": "default",
  "_name": "resource-name",
  "_cluster": "cluster-name",
  "data": {
    /* original Kubernetes resource data */
  }
}
```

**Namespace Documents:**

```json
{
  "_uid": "kubernetes-uid",
  "_event_type": "ADDED",
  "_resource_type": "namespace",
  "_name": "namespace-name",
  "_cluster": "cluster-name",
  "data": {
    /* original Kubernetes namespace data */
  }
}
```

For detailed schema information and migration guides, see [DATABASES_CONFIG.md](DATABASES_CONFIG.md).

## Development

### Project Structure

```
grpc-receiver/
├── grpc_receiver_service.py    # Main service implementation
├── sync_service.proto          # gRPC service definition
├── database/                   # Database abstraction layer
│   ├── __init__.py
│   ├── base.py                # Database interface
│   ├── factory.py             # Database factory
│   ├── mongodb.py             # MongoDB implementation
│   └── postgresql.py          # PostgreSQL implementation
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── DATABASES_CONFIG.md        # Database configuration guide
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
4. If adding database operations, update the database interface in `database/base.py`
5. Implement the new operations in both `database/mongodb.py` and `database/postgresql.py`
6. Update documentation if needed

### Adding New Database Backends

1. Create a new file in the `database/` directory (e.g., `database/redis.py`)
2. Implement the `DatabaseClient` interface from `database/base.py`
3. Add the new backend to `database/factory.py`
4. Update documentation and configuration examples

## Deployment

### Docker

The included `Dockerfile` and `docker-compose.yml` support both database backends.

**With MongoDB (default):**

```bash
docker-compose up -d
```

**With PostgreSQL:**
Edit `docker-compose.yml` to uncomment the PostgreSQL service configuration, then:

```bash
docker-compose up -d
```

### Kubernetes

Example deployment with configurable database:

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
            - name: DATABASE_TYPE
              value: "mongo" # or "postgres"
            # MongoDB configuration
            - name: MONGO_URI
              valueFrom:
                secretKeyRef:
                  name: mongodb-secret
                  key: uri
            - name: MONGO_DB
              value: "shield"
            # PostgreSQL configuration (if using postgres)
            # - name: POSTGRES_URI
            #   valueFrom:
            #     secretKeyRef:
            #       name: postgres-secret
            #       key: uri
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

The service logs important events and supports both database backends:

- Successful/failed resource syncs
- Database connection status and type
- gRPC server startup/shutdown
- Database health checks

Example log output:

```
INFO:grpc-receiver:gRPC Receiver Service started on port 50051
INFO:grpc-receiver:Connected to MONGO database
INFO:grpc-receiver:Using MONGO database
INFO:grpc-receiver:Synced vulnerabilityreports test-resource (ADDED)
```

Or with PostgreSQL:

```
INFO:grpc-receiver:Connected to PostgreSQL
INFO:grpc-receiver:PostgreSQL tables created/verified
INFO:grpc-receiver:Using POSTGRES database
INFO:grpc-receiver:Synced vulnerabilityreports test-resource (ADDED)
```

## Troubleshooting

### Common Issues

**Service won't start:**

- Check database connection configuration in `.env`
- Verify the selected database is running and accessible
- Ensure port 50051 is available
- Confirm gRPC code is generated

**No data in database:**

- Check database credentials and network access
- Verify Shield Controller is configured with correct gRPC endpoint
- Review service logs for error messages
- Test database connectivity with health check

**Connection refused from controller:**

- Verify service is running and accessible
- Check firewall/network policies
- Confirm gRPC port configuration matches

**Database-specific issues:**

For detailed troubleshooting of MongoDB and PostgreSQL issues, see [DATABASES_CONFIG.md](DATABASES_CONFIG.md).

### Health Checks

Both database backends support health checks:

```python
# Example health check usage
if db_client.health_check():
    print("Database is healthy")
else:
    print("Database connection failed")
```

## Security Considerations

- Use database authentication in production for both MongoDB and PostgreSQL
- Consider TLS for gRPC communication
- Implement proper logging without exposing sensitive data
- Use network policies to restrict access to the service
- Secure database connection strings and credentials
- For PostgreSQL, ensure SSL connections in production environments

## Migration Between Databases

The service supports switching between database backends. See [DATABASES_CONFIG.md](DATABASES_CONFIG.md) for migration guides and best practices when switching from MongoDB to PostgreSQL or vice versa.

## License

This project follows the same license as the Shield Controller project.
