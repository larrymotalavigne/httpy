"""
Routing implementation for PyHTTP.

This module provides the Route class and routing decorators for the HTTP server.
"""

import re
from typing import Dict, Any, List, Callable, Optional, Pattern

from .request import Request

# Global list of routes
ROUTES: List['Route'] = []

class Route:
    """Represents a route in the HTTP server."""
    
    def __init__(self, method: str, path: str, handler: Callable[[Request], Any]):
        """
        Initialize a new route.
        
        Args:
            method: The HTTP method this route responds to
            path: The URL path pattern
            handler: The function to handle requests to this route
        """
        self.method = method.upper()
        self.handler = handler
        self.regex, self.param_names = self._compile_path(path)

    def _compile_path(self, path: str) -> tuple[Pattern, List[str]]:
        """
        Compile a path pattern into a regex.
        
        Args:
            path: The path pattern with optional parameters like {id}
            
        Returns:
            A tuple of (compiled regex, list of parameter names)
        """
        pattern = "^"
        param_names = []
        for part in path.strip("/").split("/"):
            if part.startswith("{") and part.endswith("}"):
                name = part[1:-1]
                param_names.append(name)
                pattern += rf"/(?P<{name}>[^/]+)"
            else:
                pattern += f"/{part}"
        pattern += "/?$"
        return re.compile(pattern), param_names

    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        """
        Check if this route matches the given method and path.
        
        Args:
            method: The HTTP method
            path: The request path
            
        Returns:
            A dictionary of path parameters if matched, None otherwise
        """
        if method != self.method:
            return None
        m = self.regex.match(path)
        return m.groupdict() if m else None

def route(method: str, path: str) -> Callable:
    """
    Decorator to register a route.
    
    Args:
        method: The HTTP method
        path: The URL path pattern
        
    Returns:
        A decorator function
    """
    def decorator(func: Callable) -> Callable:
        ROUTES.append(Route(method, path, func))
        return func
    return decorator

def get(path: str) -> Callable:
    """Decorator for GET routes."""
    return route("GET", path)

def post(path: str) -> Callable:
    """Decorator for POST routes."""
    return route("POST", path)

def put(path: str) -> Callable:
    """Decorator for PUT routes."""
    return route("PUT", path)

def delete(path: str) -> Callable:
    """Decorator for DELETE routes."""
    return route("DELETE", path)