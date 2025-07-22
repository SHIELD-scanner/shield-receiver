FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Generate gRPC code
RUN python -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    sync_service.proto

# Expose gRPC port
EXPOSE 50051

# Run the service
CMD ["python", "grpc_receiver_service.py"]
