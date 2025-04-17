"""
HTTP Request implementation for PyHTTP.

This module provides the Request class for handling HTTP requests.
"""

import json
from typing import Dict, Any, Optional

class Request:
    """Represents an HTTP request to the server."""
    
    def __init__(self, method: str, path: str, headers: Dict[str, str], body: str, path_params: Dict[str, str]):
        """
        Initialize a new HTTP request.
        
        Args:
            method: The HTTP method (GET, POST, etc.)
            path: The request path
            headers: The HTTP headers
            body: The request body
            path_params: Parameters extracted from the path
        """
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.path_params = path_params

    def json(self) -> Optional[Any]:
        """
        Parse the request body as JSON.
        
        Returns:
            The parsed JSON data or None if parsing fails
        """
        try:
            return json.loads(self.body)
        except json.JSONDecodeError:
            return None