# HTTPy Performance Tuning Guide

This guide provides strategies and best practices for optimizing the performance of your HTTPy applications.

## Table of Contents

1. [Understanding HTTPy Performance](#understanding-httpy-performance)
2. [Server Configuration](#server-configuration)
3. [Protocol Selection](#protocol-selection)
4. [Connection Management](#connection-management)
5. [Route Optimization](#route-optimization)
6. [Response Optimization](#response-optimization)
7. [WebSocket Optimization](#websocket-optimization)
8. [Benchmarking and Profiling](#benchmarking-and-profiling)
9. [Deployment Considerations](#deployment-considerations)

## Understanding HTTPy Performance

HTTPy is designed to be a high-performance asynchronous HTTP server. It leverages Python's asyncio framework to handle multiple connections concurrently without the overhead of threads or processes. Understanding the following key concepts will help you optimize your application:

- **Asynchronous I/O**: HTTPy uses non-blocking I/O operations, allowing it to handle many connections with minimal resources.
- **Event Loop**: The asyncio event loop manages all concurrent tasks. Blocking the event loop will degrade performance.
- **Connection Pooling**: HTTPy reuses connections when possible to reduce the overhead of establishing new connections.
- **Protocol Efficiency**: HTTP/2 and HTTP/3 provide significant performance improvements over HTTP/1.1 for many use cases.

## Server Configuration

### Worker Configuration

When running HTTPy in production, configure the appropriate number of worker processes based on your server's CPU cores:

```python
import multiprocessing
import asyncio
from httpy import run

def start_server():
    asyncio.run(run(host="0.0.0.0", port=8080))

if __name__ == "__main__":
    # Use one worker per CPU core
    num_workers = multiprocessing.cpu_count()
    workers = []
    
    for _ in range(num_workers):
        worker = multiprocessing.Process(target=start_server)
        worker.start()
        workers.append(worker)
    
    # Wait for all workers
    for worker in workers:
        worker.join()
```

### Buffer Sizes

Adjust buffer sizes based on your application's needs:

```python
asyncio.run(run(
    host="0.0.0.0",
    port=8080,
    read_buffer_size=65536,  # 64KB read buffer (default: 16KB)
    write_buffer_size=65536,  # 64KB write buffer (default: 16KB)
))
```

### Timeouts

Configure appropriate timeouts to prevent resource exhaustion:

```python
asyncio.run(run(
    host="0.0.0.0",
    port=8080,
    keep_alive_timeout=60,  # 60 seconds (default: 5)
    request_timeout=30,     # 30 seconds (default: 60)
))
```

## Protocol Selection

### HTTP/1.1 vs HTTP/2 vs HTTP/3

Choose the appropriate protocol based on your application's needs:

- **HTTP/1.1**: Good for simple applications with few resources per page.
- **HTTP/2**: Excellent for applications with many resources per page due to multiplexing.
- **HTTP/3**: Best for unreliable networks or high-latency connections.

Enable all protocols for optimal client compatibility:

```python
import ssl
from httpy import run, AIOQUIC_AVAILABLE

# Create SSL context
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Run with all protocols
if AIOQUIC_AVAILABLE:
    asyncio.run(run(
        host="0.0.0.0",
        port=443,
        ssl_context=ssl_context,
        http3_port=443
    ))
else:
    # Fallback to HTTP/1.1 and HTTP/2
    asyncio.run(run(
        host="0.0.0.0",
        port=443,
        ssl_context=ssl_context
    ))
```

### HTTP/2 Specific Optimizations

When using HTTP/2, take advantage of server push for critical resources:

```python
@get("/")
async def homepage(req: Request) -> Response:
    response = Response.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>My App</title>
        <link rel="stylesheet" href="/static/style.css">
        <script src="/static/app.js" defer></script>
    </head>
    <body>
        <h1>Welcome</h1>
    </body>
    </html>
    """)
    
    # Push critical resources
    response.push_resources = [
        ("/static/style.css", "style"),
        ("/static/app.js", "script")
    ]
    
    return response
```

### HTTP/3 Specific Optimizations

For HTTP/3, optimize QUIC parameters:

```python
http3_config = {
    "max_datagram_size": 1350,  # Optimize for typical MTU
    "quic_max_stream_data": 1024 * 1024,  # 1MB per stream
    "quic_max_data": 5 * 1024 * 1024,     # 5MB total
    "quic_max_streams_bidi": 100,         # Max concurrent streams
    "quic_idle_timeout": 30.0,            # 30 seconds
}

asyncio.run(run(
    host="0.0.0.0",
    port=443,
    ssl_context=ssl_context,
    http3_port=443,
    http3_config=http3_config
))
```

## Connection Management

### Keep-Alive Settings

Optimize keep-alive settings based on your traffic patterns:

```python
asyncio.run(run(
    host="0.0.0.0",
    port=8080,
    keep_alive=True,                # Enable keep-alive (default)
    keep_alive_timeout=120,         # 2 minutes
    max_keep_alive_requests=1000,   # Max requests per connection
))
```

### Connection Pooling

HTTPy automatically pools connections, but you can tune the pool size:

```python
asyncio.run(run(
    host="0.0.0.0",
    port=8080,
    max_connections=10000,  # Maximum concurrent connections
))
```

## Route Optimization

### Route Matching

Organize routes from most specific to least specific to optimize route matching:

```python
# More specific routes first
@get("/api/users/{id}/profile")
async def user_profile(req: Request) -> Response:
    # ...

# Less specific routes later
@get("/api/users/{id}")
async def get_user(req: Request) -> Response:
    # ...

@get("/api/users")
async def list_users(req: Request) -> Response:
    # ...
```

### Route Caching

Implement caching for expensive routes:

```python
import time
import functools

# Simple in-memory cache
cache = {}

def cached(ttl_seconds=60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(req: Request) -> Response:
            # Create cache key from path and query params
            cache_key = f"{req.path}?{req.query_string}"
            
            # Check if result is in cache and not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl_seconds:
                    return result
            
            # Call original function
            result = await func(req)
            
            # Cache the result
            cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator

# Use the cache decorator
@get("/api/expensive-operation")
@cached(ttl_seconds=300)  # Cache for 5 minutes
async def expensive_operation(req: Request) -> Response:
    # Simulate expensive operation
    await asyncio.sleep(2)
    return Response.json({"result": "expensive calculation"})
```

## Response Optimization

### Response Compression

Enable compression for text-based responses:

```python
import gzip

def compress_response(response, min_size=1024):
    """Compress response body if it's compressible and large enough."""
    # Check if response is already compressed
    if "Content-Encoding" in response.headers:
        return response
    
    # Check content type
    content_type = response.headers.get("Content-Type", "")
    compressible = (
        content_type.startswith("text/") or
        content_type == "application/json" or
        content_type == "application/xml" or
        content_type == "application/javascript"
    )
    
    if compressible and len(response.body) >= min_size:
        # Compress body
        compressed_body = gzip.compress(response.body)
        
        # Update headers
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed_body))
        response.body = compressed_body
    
    return response

# Middleware to apply compression
async def compression_middleware(request, handler):
    response = await handler(request)
    return compress_response(response)

# Register middleware
from httpy import add_middleware
add_middleware(compression_middleware)
```

### JSON Serialization

Optimize JSON serialization for large responses:

```python
import orjson  # Faster JSON library

@get("/api/large-dataset")
async def large_dataset(req: Request) -> Response:
    # Generate large dataset
    data = [{"id": i, "name": f"Item {i}"} for i in range(10000)]
    
    # Use orjson for faster serialization
    json_bytes = orjson.dumps(data)
    
    # Create response with pre-serialized JSON
    return Response(
        body=json_bytes,
        headers={"Content-Type": "application/json"}
    )
```

### Static File Serving

Optimize static file serving with caching headers:

```python
@get("/static/{path:path}")
async def serve_static(req: Request) -> Response:
    path = req.path_params.get('path', '')
    file_path = os.path.join(STATIC_DIR, path)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return Response.json({"error": "File not found"}, status=404)
    
    # Read the file
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    content_type = "application/octet-stream"
    if path.endswith(".css"):
        content_type = "text/css"
    elif path.endswith(".js"):
        content_type = "application/javascript"
    # Add more content types as needed
    
    # Calculate ETag
    etag = f'"{hash(content)}"'
    
    # Check If-None-Match header
    if req.headers.get("If-None-Match") == etag:
        return Response(status=304)  # Not Modified
    
    # Set caching headers
    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(content)),
        "ETag": etag,
        "Cache-Control": "max-age=86400",  # 1 day
    }
    
    return Response(content, headers=headers)
```

## WebSocket Optimization

### Message Batching

Batch WebSocket messages when possible:

```python
import json

# Instead of sending many small messages
for item in items:
    await ws.send_text(json.dumps(item))  # Inefficient

# Batch messages
await ws.send_text(json.dumps(items))  # More efficient
```

### Binary Messages

Use binary messages for efficiency when appropriate:

```python
import msgpack  # More efficient than JSON for binary data

# Serialize data with MessagePack
binary_data = msgpack.packb(data)

# Send as binary message
await ws.send_binary(binary_data)
```

### Heartbeat Mechanism

Implement a heartbeat to keep connections alive:

```python
import asyncio

@websocket("/ws")
async def websocket_handler(ws: WebSocketConnection) -> None:
    # Start heartbeat task
    heartbeat_task = asyncio.create_task(send_heartbeat(ws))
    
    try:
        while True:
            msg = await ws.receive()
            # Process message...
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Cancel heartbeat task
        heartbeat_task.cancel()
        if not ws.closed:
            await ws.close()

async def send_heartbeat(ws: WebSocketConnection):
    """Send a ping every 30 seconds to keep the connection alive."""
    while True:
        await asyncio.sleep(30)
        if not ws.closed:
            await ws.ping(b'ping')
```

## Benchmarking and Profiling

### Benchmarking Your Application

Use the built-in benchmarking tools to measure performance:

```python
from httpy.benchmark import benchmark_route

# Benchmark a specific route
results = await benchmark_route(
    route="/api/users",
    method="GET",
    num_requests=1000,
    concurrency=100
)

print(f"Requests per second: {results.requests_per_second:.2f}")
print(f"Average response time: {results.avg_response_time * 1000:.2f}ms")
print(f"95th percentile: {results.p95_response_time * 1000:.2f}ms")
```

### Profiling with cProfile

Profile your application to identify bottlenecks:

```python
import cProfile
import pstats
import io

def profile_route(route_handler, request):
    """Profile a route handler."""
    pr = cProfile.Profile()
    pr.enable()
    
    # Run the route handler
    result = asyncio.run(route_handler(request))
    
    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Print top 20 functions
    
    print(s.getvalue())
    return result

# Use in development
if os.environ.get("PROFILE") == "1":
    original_handler = get_user
    @get("/api/users/{id}")
    async def get_user(req: Request) -> Response:
        return await profile_route(original_handler, req)
```

## Deployment Considerations

### Running Behind a Reverse Proxy

For production deployments, run HTTPy behind a reverse proxy like Nginx:

```
# Nginx configuration example
server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Docker Container Optimization

Optimize your Docker containers:

```dockerfile
# Use multi-stage build
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM gcr.io/distroless/python3-debian12

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY . /app
WORKDIR /app

# Run with optimized settings
CMD ["python", "-OO", "app.py"]
```

### Kubernetes Resource Limits

Set appropriate resource limits in Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: httpy-app
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: httpy-app
        image: httpy-app:latest
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "0.5"
            memory: "256Mi"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: PYTHONOPTIMIZE
          value: "2"  # Equivalent to -OO flag
```

### Monitoring and Metrics

Implement metrics collection for performance monitoring:

```python
import time
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP Request Latency', ['method', 'endpoint'])

# Middleware to collect metrics
async def metrics_middleware(request, handler):
    start_time = time.time()
    
    # Process request
    response = await handler(request)
    
    # Record metrics
    duration = time.time() - start_time
    REQUEST_COUNT.labels(request.method, request.path, response.status).inc()
    REQUEST_LATENCY.labels(request.method, request.path).observe(duration)
    
    return response

# Start metrics server
def start_metrics_server(port=8000):
    start_http_server(port)
    print(f"Metrics server started on port {port}")

# Register middleware
from httpy import add_middleware
add_middleware(metrics_middleware)

# Start metrics server when app starts
if __name__ == "__main__":
    start_metrics_server()
    asyncio.run(run(host="0.0.0.0", port=8080))
```

By following these performance tuning guidelines, you can ensure your HTTPy application runs efficiently and scales well under load.