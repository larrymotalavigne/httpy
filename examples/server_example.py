#!/usr/bin/env python3
"""
Server usage examples for the HTTPy library.
"""

import sys
import os
import asyncio
import ssl
import json
import time

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import (
    ServerResponse, ServerRequest, get, post, put, delete, websocket, run,
    HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND,
    WebSocketConnection
)

# Define some example routes

@get("/")
async def homepage(req: ServerRequest) -> ServerResponse:
    """Handle requests to the homepage."""
    return ServerResponse.text("Welcome to the HTTPy Server Example!")

@get("/hello/{name}")
async def hello(req: ServerRequest) -> ServerResponse:
    """Handle requests to /hello/{name}."""
    name = req.path_params['name']
    return ServerResponse.text(f"Hello, {name}!")

@get("/api/users")
async def get_users(req: ServerRequest) -> ServerResponse:
    """Return a list of users."""
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    ]
    return ServerResponse.json(users)

@get("/api/users/{id}")
async def get_user(req: ServerRequest) -> ServerResponse:
    """Return a specific user by ID."""
    user_id = req.path_params['id']
    # Simulate database lookup
    users = {
        "1": {"id": 1, "name": "Alice", "email": "alice@example.com"},
        "2": {"id": 2, "name": "Bob", "email": "bob@example.com"},
        "3": {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
    }

    if user_id in users:
        return ServerResponse.json(users[user_id])
    else:
        return ServerResponse.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

@post("/api/users")
async def create_user(req: ServerRequest) -> ServerResponse:
    """Create a new user."""
    data = req.json()
    if not data:
        return ServerResponse.json({"error": "Invalid JSON"}, status=HTTP_400_BAD_REQUEST)

    # Simulate user creation
    new_user = {
        "id": 4,  # In a real app, this would be generated
        "name": data.get("name", "Unknown"),
        "email": data.get("email", "unknown@example.com")
    }

    return ServerResponse.json(new_user, status=HTTP_201_CREATED)

@put("/api/users/{id}")
async def update_user(req: ServerRequest) -> ServerResponse:
    """Update an existing user."""
    user_id = req.path_params['id']
    data = req.json()

    if not data:
        return ServerResponse.json({"error": "Invalid JSON"}, status=HTTP_400_BAD_REQUEST)

    # Simulate database update
    return ServerResponse.json({
        "id": int(user_id),
        "name": data.get("name", "Updated User"),
        "email": data.get("email", "updated@example.com"),
        "updated": True
    })

@delete("/api/users/{id}")
async def delete_user(req: ServerRequest) -> ServerResponse:
    """Delete a user."""
    user_id = req.path_params['id']
    # Simulate user deletion
    return ServerResponse.json({"success": True, "message": f"User {user_id} deleted"})

@post("/echo")
async def echo(req: ServerRequest) -> ServerResponse:
    """Echo back the request body."""
    return ServerResponse.text(req.body)

# WebSocket examples

@websocket("/ws")
async def websocket_handler(ws: WebSocketConnection) -> None:
    """Handle WebSocket connections."""
    # Send welcome message
    await ws.send_text("Welcome to the WebSocket server!")

    try:
        # Echo server
        while True:
            # Wait for a message
            msg = await ws.receive()

            if msg.is_text:
                # Echo text messages
                text = msg.text()
                print(f"Received text message: {text}")
                await ws.send_text(f"Echo: {text}")

            elif msg.is_binary:
                # Echo binary messages
                print(f"Received binary message of {len(msg.data)} bytes")
                await ws.send_binary(msg.data)

            elif msg.is_close:
                # Handle close message
                print("Received close message")
                await ws.close()
                break

            elif msg.is_ping:
                # Respond to ping with pong
                print("Received ping")
                await ws.pong(msg.data)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Ensure connection is closed
        if not ws.closed:
            await ws.close()
        print("WebSocket connection closed")

@websocket("/ws/chat/{room}")
async def chat_room(ws: WebSocketConnection) -> None:
    """Example of a chat room with path parameters."""
    room = ws.path_params.get('room', 'default')

    # Send welcome message
    await ws.send_text(f"Welcome to chat room: {room}")

    try:
        # Simple chat example
        while True:
            msg = await ws.receive()
            if msg.is_text:
                # Process chat message
                text = msg.text()
                if text.startswith("/"):
                    # Handle commands
                    if text == "/quit":
                        await ws.send_text("Goodbye!")
                        await ws.close()
                        break
                    elif text == "/time":
                        await ws.send_text(f"Server time: {time.strftime('%H:%M:%S')}")
                    else:
                        await ws.send_text(f"Unknown command: {text}")
                else:
                    # Echo regular messages with room info
                    await ws.send_text(f"[{room}] {text}")
            elif msg.is_close:
                break

    except Exception as e:
        print(f"Chat WebSocket error: {e}")
    finally:
        if not ws.closed:
            await ws.close()

if __name__ == "__main__":
    print("Starting HTTPy Server Example")
    print("Press Ctrl+C to stop the server")
    print("Try these endpoints:")
    print("  - http://localhost:8080/")
    print("  - http://localhost:8080/hello/world")
    print("  - http://localhost:8080/api/users")
    print("  - http://localhost:8080/api/users/1")
    print("  - POST to http://localhost:8080/api/users with JSON body")
    print("  - PUT to http://localhost:8080/api/users/1 with JSON body")
    print("  - DELETE to http://localhost:8080/api/users/1")
    print("  - POST to http://localhost:8080/echo with any body")
    print("  - WebSocket connection to ws://localhost:8080/ws")
    print("  - WebSocket connection to ws://localhost:8080/ws/chat/room1")

    # Check if SSL certificates exist for HTTPS and HTTP/2.0
    ssl_context = None
    cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
    key_file = os.path.join(os.path.dirname(__file__), 'key.pem')

    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("\nSSL certificates found. HTTPS and HTTP/2.0 will be enabled.")
        print("Try these secure endpoints:")
        print("  - https://localhost:8443/")
        print("  - WebSocket connection to wss://localhost:8443/ws")
        print("  - HTTP/2.0 connection to https://localhost:8443/")

        # Create SSL context for HTTPS and HTTP/2.0
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_file, key_file)

        # Enable HTTP/2.0 via ALPN
        ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    else:
        print("\nNo SSL certificates found. Running in HTTP mode only.")
        print("To enable HTTPS and HTTP/2.0, create cert.pem and key.pem files in the examples directory.")
        print("You can generate self-signed certificates with:")
        print("  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes")

    # Define async function to run the server
    async def start_server():
        try:
            # Use 0.0.0.0 to listen on all interfaces (required for Docker)
            if ssl_context:
                # Check if HTTP/3 is available
                http3_available = False
                try:
                    from httpy import AIOQUIC_AVAILABLE
                    http3_available = AIOQUIC_AVAILABLE
                except ImportError:
                    pass

                # Run HTTP, HTTPS, and HTTP/3 servers
                http_server = asyncio.create_task(run(host="0.0.0.0", port=8080))

                if http3_available:
                    # Run HTTPS with HTTP/3 support
                    print("\nHTTP/3 support is available!")
                    print("Try these HTTP/3 endpoints:")
                    print("  - https://localhost:8443/ (with HTTP/3 enabled browser)")
                    https_server = asyncio.create_task(
                        run(host="0.0.0.0", port=8443, ssl_context=ssl_context, http3_port=8443)
                    )
                else:
                    # Run HTTPS without HTTP/3 support
                    print("\nHTTP/3 support is not available.")
                    print("Install aioquic to enable HTTP/3 support: pip install aioquic")
                    https_server = asyncio.create_task(
                        run(host="0.0.0.0", port=8443, ssl_context=ssl_context)
                    )

                # Wait for both servers
                await asyncio.gather(http_server, https_server)
            else:
                # Run HTTP server only
                await run(host="0.0.0.0", port=8080)
        except Exception as e:
            print(f"\nServer error: {e}")

    try:
        # Run the server
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\nServer stopped")
