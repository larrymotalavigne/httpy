# PyHTTP

A simple, intuitive HTTP server library for Python.

## Features

- Asynchronous HTTP server with minimal dependencies
- Decorator-based routing system
- Path parameter extraction
- JSON request and response handling
- Support for common HTTP methods (GET, POST, PUT, DELETE)
- Connection keep-alive support

## Installation

```bash
# Not yet available on PyPI
# Clone the repository
git clone https://github.com/LarryMotaLavigne/pyhttp.git

# Install in development mode
pip install -e .
```

## Usage

#### Basic Server

```python
import asyncio
from pyhttp import get, post, ServerRequest, ServerResponse, run

# Define routes using decorators
@get("/")
async def homepage(req: ServerRequest) -> ServerResponse:
    return ServerResponse.text("Hello, World!")

@get("/users/{id}")
async def get_user(req: ServerRequest) -> ServerResponse:
    user_id = req.path_params['id']
    return ServerResponse.json({"id": user_id, "name": "Example User"})

@post("/users")
async def create_user(req: ServerRequest) -> ServerResponse:
    data = req.json()
    if not data:
        return ServerResponse.json({"error": "Invalid JSON"}, status=400)

    # Process the data...
    return ServerResponse.json({"id": 123, "name": data.get("name")}, status=201)

# Run the server
if __name__ == "__main__":
    asyncio.run(run(host="localhost", port=8080))
```

#### RESTful API Server

```python
import asyncio
from pyhttp import (
    get, post, put, delete, 
    ServerRequest, ServerResponse, 
    HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND,
    run
)

# In-memory database for the example
users = {}

@get("/api/users")
async def get_users(req: ServerRequest) -> ServerResponse:
    return ServerResponse.json(list(users.values()))

@get("/api/users/{id}")
async def get_user(req: ServerRequest) -> ServerResponse:
    user_id = req.path_params['id']
    if user_id in users:
        return ServerResponse.json(users[user_id])
    return ServerResponse.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

@post("/api/users")
async def create_user(req: ServerRequest) -> ServerResponse:
    data = req.json()
    if not data or "name" not in data:
        return ServerResponse.json({"error": "Invalid user data"}, status=400)

    user_id = str(len(users) + 1)
    users[user_id] = {"id": user_id, "name": data["name"]}
    return ServerResponse.json(users[user_id], status=HTTP_201_CREATED)

@put("/api/users/{id}")
async def update_user(req: ServerRequest) -> ServerResponse:
    user_id = req.path_params['id']
    if user_id not in users:
        return ServerResponse.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

    data = req.json()
    if not data:
        return ServerResponse.json({"error": "Invalid user data"}, status=400)

    users[user_id].update(data)
    return ServerResponse.json(users[user_id])

@delete("/api/users/{id}")
async def delete_user(req: ServerRequest) -> ServerResponse:
    user_id = req.path_params['id']
    if user_id not in users:
        return ServerResponse.json({"error": "User not found"}, status=HTTP_404_NOT_FOUND)

    del users[user_id]
    return ServerResponse.json({"success": True})

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
```

Example:
```python
@get("/users/{id}")
async def get_user(request):
    user_id = request.path_params['id']
    # ...
    return ServerResponse.json({"id": user_id, "name": "John"})
```

### ServerRequest

Represents an HTTP request to the server.

#### Properties

- `method`: The HTTP method (GET, POST, etc.)
- `path`: The request path
- `headers`: The HTTP headers
- `body`: The request body as a string
- `path_params`: Parameters extracted from the path

#### Methods

- `json()`: Parse the request body as JSON

### ServerResponse

Represents an HTTP response from the server.

#### Static Methods

- `text(data, status=200, headers=None)`: Create a text response
- `json(data, status=200, headers=None)`: Create a JSON response

#### Running the Server

```python
import asyncio
from pyhttp import run

# Define your routes...

if __name__ == "__main__":
    asyncio.run(run(host="localhost", port=8080))
```

## License

MIT
