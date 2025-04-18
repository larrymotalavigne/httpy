"""
API routes for the multi-file example.

This module contains all the API endpoints for the application.
"""

import sys
import os
import json
from typing import Dict, List, Any

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from httpy import (
    Response, Request, get, post, put, delete,
    HTTP_201_CREATED, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
)

# Simulate a database
_users_db: Dict[str, Dict[str, Any]] = {
    "1": {"id": 1, "name": "Alice", "email": "alice@example.com"},
    "2": {"id": 2, "name": "Bob", "email": "bob@example.com"},
    "3": {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
}

# API Routes

@get("/api/users")
async def get_users(req: Request) -> Response:
    """Return a list of users."""
    return Response.json(list(_users_db.values()))

@get("/api/users/{id}")
async def get_user(req: Request) -> Response:
    """Return a specific user by ID."""
    user_id = req.path_params['id']
    
    if user_id in _users_db:
        return Response.json(_users_db[user_id])
    else:
        return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

@post("/api/users")
async def create_user(req: Request) -> Response:
    """Create a new user."""
    data = req.json()
    if not data:
        return Response.json({"error": "Invalid JSON"}, status=HTTP_400_BAD_REQUEST)
    
    # Generate a new ID
    new_id = str(max(int(id) for id in _users_db.keys()) + 1)
    
    # Create the new user
    new_user = {
        "id": int(new_id),
        "name": data.get("name", "Unknown"),
        "email": data.get("email", "unknown@example.com")
    }
    
    # Add to the database
    _users_db[new_id] = new_user
    
    return Response.json(new_user, status=HTTP_201_CREATED)

@put("/api/users/{id}")
async def update_user(req: Request) -> Response:
    """Update an existing user."""
    user_id = req.path_params['id']
    data = req.json()
    
    if not data:
        return Response.json({"error": "Invalid JSON"}, status=HTTP_400_BAD_REQUEST)
    
    if user_id not in _users_db:
        return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)
    
    # Update the user
    user = _users_db[user_id]
    if "name" in data:
        user["name"] = data["name"]
    if "email" in data:
        user["email"] = data["email"]
    
    return Response.json(user)

@delete("/api/users/{id}")
async def delete_user(req: Request) -> Response:
    """Delete a user."""
    user_id = req.path_params['id']
    
    if user_id not in _users_db:
        return Response.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)
    
    # Delete the user
    del _users_db[user_id]
    
    return Response.json({"success": True, "message": f"User {user_id} deleted"})