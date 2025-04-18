# HTTPy

A simple, intuitive HTTP server library for Python.

## Features

- Asynchronous HTTP server with minimal dependencies
- Decorator-based routing system
- Path parameter extraction
- JSON request and response handling
- Support for common HTTP methods (GET, POST, PUT, DELETE)
- Connection keep-alive support
- WebSocket support
- HTTP/2.0 support

## Installation

```bash
# Not yet available on PyPI
# Clone the repository
git clone https://github.com/LarryMotaLavigne/httpy.git

# Install in development mode
pip install -e .
```

## Usage

#### Basic Server

```python
import asyncio
from httpy import get, post, Request, Response, run

# Define routes using decorators
@get("/")
async def homepage(req: Request) -> Response:
    return Response.text("Hello, World!")

@get("/users/{id}")
async def get_user(req: Request) -> Response:
    user_id = req.path_params['id']
    return Response.json({"id": user_id, "name": "Example User"})

@post("/users")
async def create_user(req: Request) -> Response:
    data = req.json()
    if not data:
        return Response.json({"error": "Invalid JSON"}, status=400)

    # Process the data...
    return Response.json({"id": 123, "name": data.get("name")}, status=201)

# Run the server
if __name__ == "__main__":
    asyncio.run(run(host="localhost", port=8080))
```

#### RESTful API Server

```python
import asyncio
from httpy import (
    get, post, put, delete, 
    Request, Response, 
    HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND,
    run
)

# In-memory database for the example
users = {}

@get("/api/users")
async def get_users(req: Request) -> Response:
    return Response.json(list(users.values()))

@get("/api/users/{id}")
async def get_user(req: Request) -> Response:
    user_id = req.path_params['id']
    if user_id in users:
        return Response.json(users[user_id])
    return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

@post("/api/users")
async def create_user(req: Request) -> Response:
    data = req.json()
    if not data or "name" not in data:
        return Response.json({"error": "Invalid user data"}, status=400)

    user_id = str(len(users) + 1)
    users[user_id] = {"id": user_id, "name": data["name"]}
    return Response.json(users[user_id], status=HTTP_201_CREATED)

@put("/api/users/{id}")
async def update_user(req: Request) -> Response:
    user_id = req.path_params['id']
    if user_id not in users:
        return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

    data = req.json()
    if not data:
        return Response.json({"error": "Invalid user data"}, status=400)

    users[user_id].update(data)
    return Response.json(users[user_id])

@delete("/api/users/{id}")
async def delete_user(req: Request) -> Response:
    user_id = req.path_params['id']
    if user_id not in users:
        return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

    del users[user_id]
    return Response.json({"success": True})

if __name__ == "__main__":
    asyncio.run(run(host="localhost", port=8080))
```

## API Reference

### Route Decorators

Define routes for your HTTP server:

```python
@get(path)
@post(path)
@put(path)
@delete(path)
@route(method, path)
@websocket(path)  # For WebSocket routes
```

Example:
```python
@get("/users/{id}")
async def get_user(request):
    user_id = request.path_params['id']
    # ...
    return Response.json({"id": user_id, "name": "John"})

@websocket("/ws")
async def websocket_handler(ws):
    await ws.send_text("Welcome to the WebSocket server!")
    while True:
        msg = await ws.receive()
        if msg.is_text:
            await ws.send_text(f"Echo: {msg.text()}")
        elif msg.is_close:
            await ws.close()
            break
```

### Request

Represents an HTTP request to the server.

#### Properties

- `method`: The HTTP method (GET, POST, etc.)
- `path`: The request path
- `headers`: The HTTP headers
- `body`: The request body as a string
- `path_params`: Parameters extracted from the path

#### Methods

- `json()`: Parse the request body as JSON

### Response

Represents an HTTP response from the server.

#### Static Methods

- `text(data, status=200, headers=None)`: Create a text response
- `json(data, status=200, headers=None)`: Create a JSON response

### WebSocketConnection

Represents a WebSocket connection to the client.

#### Properties

- `path`: The request path
- `headers`: The HTTP headers from the initial request
- `closed`: Whether the connection is closed

#### Methods

- `send_text(message)`: Send a text message to the client
- `send_binary(message)`: Send a binary message to the client
- `close(code=1000, reason="")`: Close the WebSocket connection
- `ping(data=b'')`: Send a ping message to the client
- `pong(data=b'')`: Send a pong message to the client

### HTTP/2.0 Support

HTTPy includes support for HTTP/2.0 via both ALPN negotiation (for HTTPS) and HTTP/1.1 upgrade (h2c).

To enable HTTP/2.0 with ALPN, provide an SSL context when running the server:

```python
import ssl
from httpy import run

# Create SSL context
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Run with SSL (enables HTTP/2.0 via ALPN)
asyncio.run(run(host="localhost", port=443, ssl_context=ssl_context))
```

### HTTP/3 Support

HTTPy includes support for HTTP/3 via the QUIC protocol. HTTP/3 requires SSL and the `aioquic` library.

To enable HTTP/3, install the required dependency:

```bash
pip install aioquic
```

Then provide an SSL context and HTTP/3 port when running the server:

```python
import ssl
from httpy import run, AIOQUIC_AVAILABLE

# Create SSL context
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Check if HTTP/3 is available
if AIOQUIC_AVAILABLE:
    # Run with SSL and HTTP/3 support
    asyncio.run(run(host="localhost", port=443, ssl_context=ssl_context, http3_port=443))
else:
    # Run with SSL only (HTTP/2.0 and HTTP/1.1)
    asyncio.run(run(host="localhost", port=443, ssl_context=ssl_context))
```

HTTP/3 provides several advantages over HTTP/2:
- Improved performance on unreliable networks
- Faster connection establishment
- Better multiplexing without head-of-line blocking
- Improved security with TLS 1.3 by default

#### Running the Server

```python
import asyncio
import ssl
from httpy import run

# Define your routes...

if __name__ == "__main__":
    # For HTTP/1.1 only
    asyncio.run(run(host="localhost", port=8080))

    # For HTTPS and HTTP/2.0
    # ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    # ssl_context.load_cert_chain('cert.pem', 'key.pem')
    # asyncio.run(run(host="localhost", port=443, ssl_context=ssl_context))
```

## Benchmarks

HTTPy includes benchmarking tools to compare its performance with other popular Python web frameworks like Starlette, Flask, and Tornado.

To run the benchmarks:

```bash
# Install benchmark dependencies
pip install flask tornado starlette uvicorn psutil

# Run the benchmark
python benchmark/benchmark.py
```

For more details, see the [benchmark README](benchmark/README.md).

## Docker

HTTPy can be easily deployed using Docker. A Dockerfile is included in the repository.

### Building the Docker image

```bash
docker build -t httpy:latest .
```

### Running the Docker container

```bash
docker run -p 8080:8080 httpy:latest
```

### Using the pre-built image from GitHub Container Registry

The project provides multi-architecture images (amd64, arm64) for multiple Python versions (3.9, 3.10, 3.11, 3.12, 3.13).

#### Latest version:
```bash
docker pull ghcr.io/larrymolalavigne/httpy:latest
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:latest
```

#### Specific Python version:
```bash
# For Python 3.9
docker pull ghcr.io/larrymolalavigne/httpy:python3.9
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:python3.9

# For Python 3.10
docker pull ghcr.io/larrymolalavigne/httpy:python3.10
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:python3.10

# For Python 3.11
docker pull ghcr.io/larrymolalavigne/httpy:python3.11
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:python3.11

# For Python 3.12
docker pull ghcr.io/larrymolalavigne/httpy:python3.12
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:python3.12

# For Python 3.13
docker pull ghcr.io/larrymolalavigne/httpy:python3.13
docker run -p 8080:8080 ghcr.io/larrymolalavigne/httpy:python3.13
```

### Technical Details

The Docker images use Google's distroless Python images (`gcr.io/distroless/python3-debian12`) as the base, which provides:
- Minimal attack surface (no shell, no package manager)
- Smaller image size
- Better security posture
- Debian 12 (Bookworm) base

## Kubernetes Deployment

To deploy HTTPy on a Kubernetes cluster, you can use the following example manifest:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: httpy
  labels:
    app: httpy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: httpy
  template:
    metadata:
      labels:
        app: httpy
    spec:
      containers:
      - name: httpy
        image: ghcr.io/larrymolalavigne/httpy:latest
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: "0.5"
            memory: "256Mi"
          requests:
            cpu: "0.2"
            memory: "128Mi"
---
apiVersion: v1
kind: Service
metadata:
  name: httpy
spec:
  selector:
    app: httpy
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

Save this to a file named `kubernetes.yaml` and apply it with:

```bash
kubectl apply -f kubernetes.yaml
```

## License

MIT
