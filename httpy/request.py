"""
HTTP Request implementation for HTTPy.

This module provides the Request class for handling HTTP requests.
"""

import json
from typing import Dict, Any, Optional, Union

class Request:
    """Represents an HTTP request to the server."""

    def __init__(self, method: str, path: str, headers: Dict[str, str], body: str, 
                 path_params: Dict[str, str], query_params: Optional[Dict[str, Union[str, list]]] = None):
        """
        Initialize a new HTTP request.

        Args:
            method: The HTTP method (GET, POST, etc.)
            path: The request path
            headers: The HTTP headers
            body: The request body
            path_params: Parameters extracted from the path
            query_params: Query parameters from the URL
        """
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.path_params = path_params
        self.query_params = query_params or {}

        # Cache for parsed JSON data
        self._json_cache = None
        self._json_parsed = False

    def json(self) -> Optional[Any]:
        """
        Parse the request body as JSON.

        The result is cached for subsequent calls.

        Returns:
            The parsed JSON data or None if parsing fails
        """
        # Return cached result if we've already parsed this body
        if self._json_parsed:
            return self._json_cache

        try:
            self._json_cache = json.loads(self.body)
            self._json_parsed = True
            return self._json_cache
        except json.JSONDecodeError:
            self._json_parsed = True
            self._json_cache = None
            return None

    def get_query_param(self, name: str, default: Any = None) -> Any:
        """
        Get a query parameter by name.

        Args:
            name: The parameter name
            default: Default value if parameter is not present

        Returns:
            The parameter value or the default value
        """
        return self.query_params.get(name, default)

    def get_path_param(self, name: str, default: Any = None) -> Any:
        """
        Get a path parameter by name.

        Args:
            name: The parameter name
            default: Default value if parameter is not present

        Returns:
            The parameter value or the default value
        """
        return self.path_params.get(name, default)
