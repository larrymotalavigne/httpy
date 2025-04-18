#!/usr/bin/env python3
"""
Server usage examples for the HTTPy library.
"""

import sys
import os
import asyncio

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import (
    ServerResponse, ServerRequest, get, post, put, delete, run,
    HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND
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

    try:
        asyncio.run(run(host="localhost", port=8080))
    except KeyboardInterrupt:
        print("\nServer stopped")
