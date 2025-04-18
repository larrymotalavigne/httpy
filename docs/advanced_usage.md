# HTTPy Advanced Usage Scenarios

This document provides advanced usage scenarios and patterns for the HTTPy framework that go beyond the basic examples in the README.

## Table of Contents

1. [Application Structure for Larger Projects](#application-structure-for-larger-projects)
2. [Middleware Implementation](#middleware-implementation)
3. [Authentication and Authorization](#authentication-and-authorization)
4. [File Uploads and Downloads](#file-uploads-and-downloads)
5. [WebSocket Real-time Applications](#websocket-real-time-applications)
6. [HTTP/2 and HTTP/3 Optimization](#http2-and-http3-optimization)
7. [Error Handling and Logging](#error-handling-and-logging)
8. [Testing Strategies](#testing-strategies)

## Application Structure for Larger Projects

For larger applications, it's recommended to organize your code into modules by functionality:

```
my_app/
├── app.py                 # Main application entry point
├── routes/                # Route definitions
│   ├── __init__.py        # Package initialization
│   ├── api.py             # API routes
│   ├── pages.py           # Page routes
│   └── websockets.py      # WebSocket routes
├── middleware/            # Middleware components
│   ├── __init__.py
│   ├── auth.py            # Authentication middleware
│   └── logging.py         # Logging middleware
├── models/                # Data models
│   ├── __init__.py
│   └── user.py            # User model
├── services/              # Business logic
│   ├── __init__.py
│   └── user_service.py    # User service
├── static/                # Static files
│   ├── css/
│   ├── js/
│   └── images/
└── templates/             # HTML templates
```

### Example app.py

```python
import asyncio
import os
from httpy import run

# Import all routes
from routes import api, pages, websockets

# Import middleware
from middleware import auth, logging

if __name__ == "__main__":
    # Run the server
    asyncio.run(run(host="0.0.0.0", port=8080))
```

## Middleware Implementation

HTTPy supports middleware for request/response processing. Here's how to implement custom middleware:

### Authentication Middleware

```python
from httpy import Request, Response, HTTP_401_UNAUTHORIZED

# Define a middleware function
async def auth_middleware(request: Request, handler):
    # Check for authentication token
    auth_header = request.headers.get("Authorization")
    
    # Skip authentication for public routes
    if request.path.startswith("/public") or request.path == "/login":
        return await handler(request)
    
    # Validate token
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response.json(
            {"error": "Unauthorized"}, 
            status=HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.replace("Bearer ", "")
    if not validate_token(token):  # Implement your token validation
        return Response.json(
            {"error": "Invalid token"}, 
            status=HTTP_401_UNAUTHORIZED
        )
    
    # Token is valid, proceed with the request
    return await handler(request)

# Register middleware
from httpy import add_middleware
add_middleware(auth_middleware)
```

### Logging Middleware

```python
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("httpy")

async def logging_middleware(request: Request, handler):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.path}")
    
    # Process request
    response = await handler(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(f"Response: {response.status} - {duration:.4f}s")
    
    return response

# Register middleware
from httpy import add_middleware
add_middleware(logging_middleware)
```

## Authentication and Authorization

### JWT Authentication

```python
import jwt
from datetime import datetime, timedelta
from httpy import post, Request, Response, HTTP_401_UNAUTHORIZED

# Secret key for JWT
SECRET_KEY = "your-secret-key"  # Use a secure key in production

# User database (replace with your database)
users = {
    "user1": {"password": "password1", "role": "user"},
    "admin": {"password": "admin123", "role": "admin"}
}

@post("/login")
async def login(request: Request) -> Response:
    data = request.json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return Response.json({"error": "Username and password required"}, status=400)
    
    if username not in users or users[username]["password"] != password:
        return Response.json({"error": "Invalid credentials"}, status=HTTP_401_UNAUTHORIZED)
    
    # Create JWT token
    expiration = datetime.utcnow() + timedelta(hours=24)
    payload = {
        "sub": username,
        "role": users[username]["role"],
        "exp": expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    
    return Response.json({"token": token, "expires": expiration.isoformat()})

# Helper function to validate token
def validate_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Protected route example
@get("/api/protected")
async def protected_route(request: Request) -> Response:
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response.json({"error": "Unauthorized"}, status=HTTP_401_UNAUTHORIZED)
    
    token = auth_header.replace("Bearer ", "")
    payload = validate_token(token)
    
    if not payload:
        return Response.json({"error": "Invalid token"}, status=HTTP_401_UNAUTHORIZED)
    
    # Access granted
    return Response.json({
        "message": "Protected data",
        "user": payload["sub"],
        "role": payload["role"]
    })

# Role-based authorization
@get("/api/admin")
async def admin_route(request: Request) -> Response:
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response.json({"error": "Unauthorized"}, status=HTTP_401_UNAUTHORIZED)
    
    token = auth_header.replace("Bearer ", "")
    payload = validate_token(token)
    
    if not payload:
        return Response.json({"error": "Invalid token"}, status=HTTP_401_UNAUTHORIZED)
    
    # Check role
    if payload["role"] != "admin":
        return Response.json({"error": "Forbidden"}, status=403)
    
    # Admin access granted
    return Response.json({
        "message": "Admin data",
        "user": payload["sub"]
    })
```

## File Uploads and Downloads

HTTPy supports multipart form data for file uploads:

```python
import os
from httpy import post, get, Request, Response, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

# Create upload directory
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

@post("/upload")
async def upload_file(req: Request) -> Response:
    # Check if the request has multipart form data
    if not req.is_multipart():
        return Response.json({"error": "Multipart form data required"}, status=HTTP_400_BAD_REQUEST)
    
    # Get the uploaded file
    form_data = await req.form()
    if "file" not in form_data:
        return Response.json({"error": "No file uploaded"}, status=HTTP_400_BAD_REQUEST)
    
    file = form_data["file"]
    
    # Save the file
    filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    return Response.json({
        "success": True,
        "filename": filename,
        "size": os.path.getsize(file_path),
        "download_url": f"/download/{filename}"
    })

@get("/download/{filename}")
async def download_file(req: Request) -> Response:
    filename = req.path_params.get('filename', '')
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        return Response.json({"error": "File not found"}, status=HTTP_404_NOT_FOUND)
    
    # Read the file
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    content_type = "application/octet-stream"
    if filename.endswith(".txt"):
        content_type = "text/plain"
    elif filename.endswith(".html") or filename.endswith(".htm"):
        content_type = "text/html"
    elif filename.endswith(".pdf"):
        content_type = "application/pdf"
    # Add more content types as needed
    
    # Create response with appropriate headers
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"",
        "Content-Type": content_type,
        "Content-Length": str(len(content))
    }
    
    return Response(content, headers=headers)
```

## WebSocket Real-time Applications

### Chat Application

```python
import asyncio
import json
from httpy import websocket, WebSocketConnection

# Store active connections by room
rooms = {}

@websocket("/ws/chat/{room}")
async def chat_room(ws: WebSocketConnection) -> None:
    room = ws.path_params.get('room', 'default')
    
    # Add connection to room
    if room not in rooms:
        rooms[room] = set()
    rooms[room].add(ws)
    
    # Send welcome message
    await ws.send_text(f"Welcome to chat room: {room}")
    
    # Broadcast join message to other users
    for client in rooms[room]:
        if client != ws:
            await client.send_text(f"User joined the room")
    
    try:
        while True:
            msg = await ws.receive()
            if msg.is_text:
                text = msg.text()
                data = json.loads(text)
                
                # Broadcast message to all clients in the room
                for client in rooms[room]:
                    await client.send_text(json.dumps({
                        "sender": data.get("sender", "Anonymous"),
                        "message": data.get("message", ""),
                        "timestamp": data.get("timestamp", "")
                    }))
            elif msg.is_close:
                break
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove connection from room
        if room in rooms and ws in rooms[room]:
            rooms[room].remove(ws)
            if not rooms[room]:
                del rooms[room]
        
        # Close connection if still open
        if not ws.closed:
            await ws.close()
```

### Real-time Data Stream

```python
import asyncio
import json
import random
from datetime import datetime
from httpy import websocket, WebSocketConnection

@websocket("/ws/data-stream")
async def data_stream(ws: WebSocketConnection) -> None:
    """Stream real-time data to the client."""
    try:
        # Send initial message
        await ws.send_text("Starting data stream...")
        
        # Stream data every second
        while True:
            # Generate random data
            data = {
                "timestamp": datetime.now().isoformat(),
                "value": random.random() * 100,
                "status": random.choice(["normal", "warning", "critical"])
            }
            
            # Send data as JSON
            await ws.send_text(json.dumps(data))
            
            # Wait for 1 second
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Data stream error: {e}")
    finally:
        if not ws.closed:
            await ws.close()
```

## HTTP/2 and HTTP/3 Optimization

### HTTP/2 Server Push

HTTP/2 server push allows the server to send resources to the client before they are requested:

```python
from httpy import get, Request, Response

@get("/")
async def homepage(req: Request) -> Response:
    # Create the main response
    response = Response.html("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HTTP/2 Server Push Example</title>
        <link rel="stylesheet" href="/static/style.css">
        <script src="/static/app.js" defer></script>
    </head>
    <body>
        <h1>HTTP/2 Server Push Example</h1>
        <div id="content">Loading...</div>
    </body>
    </html>
    """)
    
    # Add server push headers for CSS and JS
    response.push_resources = [
        ("/static/style.css", "style"),
        ("/static/app.js", "script")
    ]
    
    return response
```

### HTTP/3 Configuration

```python
import asyncio
import ssl
from httpy import run, AIOQUIC_AVAILABLE

# Create SSL context
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

# Run with HTTP/3 support if available
if AIOQUIC_AVAILABLE:
    # Configure HTTP/3 with custom settings
    http3_config = {
        "max_datagram_size": 1350,
        "quic_max_stream_data": 1024 * 1024,  # 1MB
        "quic_max_data": 5 * 1024 * 1024,     # 5MB
        "quic_max_streams_bidi": 100,
        "quic_max_streams_uni": 100,
        "quic_idle_timeout": 30.0,            # 30 seconds
    }
    
    # Run server with HTTP/3 support
    asyncio.run(run(
        host="0.0.0.0", 
        port=443, 
        ssl_context=ssl_context, 
        http3_port=443,
        http3_config=http3_config
    ))
else:
    # Fallback to HTTP/2 and HTTP/1.1
    asyncio.run(run(host="0.0.0.0", port=443, ssl_context=ssl_context))
```

## Error Handling and Logging

### Global Exception Handler

```python
import traceback
import logging
from httpy import Request, Response, add_exception_handler, HTTP_500_INTERNAL_SERVER_ERROR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger("httpy")

# Define global exception handler
async def global_exception_handler(request: Request, exc: Exception) -> Response:
    # Log the exception
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    # In development, return detailed error
    if os.environ.get("ENV") == "development":
        return Response.json({
            "error": str(exc),
            "type": exc.__class__.__name__,
            "traceback": traceback.format_exc()
        }, status=HTTP_500_INTERNAL_SERVER_ERROR)
    
    # In production, return generic error
    return Response.json({
        "error": "Internal Server Error"
    }, status=HTTP_500_INTERNAL_SERVER_ERROR)

# Register the exception handler
add_exception_handler(Exception, global_exception_handler)

# Route-specific exception handler
from httpy import add_exception_handler_for_route

async def database_error_handler(request: Request, exc: DatabaseError) -> Response:
    logger.error(f"Database error: {exc}")
    return Response.json({
        "error": "Database error occurred",
        "details": str(exc)
    }, status=503)  # Service Unavailable

# Register for specific route and exception type
add_exception_handler_for_route("/api/users", DatabaseError, database_error_handler)
```

## Testing Strategies

### Unit Testing Routes

```python
import pytest
from httpy import Request, Response, get

# Route to test
@get("/api/users/{id}")
async def get_user(req: Request) -> Response:
    user_id = req.path_params['id']
    # Simulate database lookup
    if user_id == "1":
        return Response.json({"id": 1, "name": "Test User"})
    return Response.json({"error": "User not found"}, status=404)

# Test function
@pytest.mark.asyncio
async def test_get_user():
    # Create mock request
    request = Request(
        method="GET",
        path="/api/users/1",
        headers={},
        body=b"",
        path_params={"id": "1"}
    )
    
    # Call the route handler
    response = await get_user(request)
    
    # Assert response
    assert response.status == 200
    assert response.json_body() == {"id": 1, "name": "Test User"}
    
    # Test not found case
    request.path_params = {"id": "999"}
    response = await get_user(request)
    assert response.status == 404
```

### Integration Testing

```python
import pytest
import asyncio
import aiohttp
import subprocess
import time
import signal
import os

@pytest.fixture
async def server():
    # Start the server in a subprocess
    process = subprocess.Popen(["python", "app.py"])
    
    # Wait for server to start
    time.sleep(2)
    
    yield
    
    # Stop the server
    process.send_signal(signal.SIGINT)
    process.wait()

@pytest.mark.asyncio
async def test_api_integration(server):
    async with aiohttp.ClientSession() as session:
        # Test GET request
        async with session.get("http://localhost:8080/api/users") as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, list)
        
        # Test POST request
        user_data = {"name": "New User", "email": "new@example.com"}
        async with session.post("http://localhost:8080/api/users", json=user_data) as response:
            assert response.status == 201
            data = await response.json()
            assert data["name"] == "New User"
            user_id = data["id"]
        
        # Test GET specific user
        async with session.get(f"http://localhost:8080/api/users/{user_id}") as response:
            assert response.status == 200
            data = await response.json()
            assert data["name"] == "New User"
```

### Load Testing

```python
import asyncio
import aiohttp
import time
import statistics

async def load_test(url, num_requests, concurrency):
    semaphore = asyncio.Semaphore(concurrency)
    start_time = time.time()
    response_times = []
    
    async def make_request():
        async with semaphore:
            req_start = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    await response.text()
                    req_time = time.time() - req_start
                    response_times.append(req_time)
    
    # Create tasks for all requests
    tasks = [make_request() for _ in range(num_requests)]
    
    # Run all tasks
    await asyncio.gather(*tasks)
    
    # Calculate statistics
    total_time = time.time() - start_time
    avg_time = statistics.mean(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
    
    return {
        "total_requests": num_requests,
        "concurrency": concurrency,
        "total_time": total_time,
        "requests_per_second": num_requests / total_time,
        "avg_response_time": avg_time,
        "min_response_time": min_time,
        "max_response_time": max_time,
        "p95_response_time": p95_time
    }

# Run the load test
async def run_load_test():
    results = await load_test("http://localhost:8080/api/users", 1000, 100)
    print(f"Requests per second: {results['requests_per_second']:.2f}")
    print(f"Average response time: {results['avg_response_time'] * 1000:.2f}ms")
    print(f"95th percentile response time: {results['p95_response_time'] * 1000:.2f}ms")

# asyncio.run(run_load_test())
```