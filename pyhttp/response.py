"""
HTTP Response implementation for PyHTTP.

This module provides the Response class for handling HTTP responses.
"""

import json
from typing import Dict, Any, Optional

from .http import HTTP_STATUS_CODES

class Response:
    """Represents an HTTP response from the server."""
    
    def __init__(self, body: str = '', status: int = 200, headers: Optional[Dict[str, Any]] = None):
        """
        Initialize a new HTTP response.
        
        Args:
            body: The response body as a string
            status: The HTTP status code
            headers: Optional HTTP headers
        """
        self.status = status
        self.body = body
        self.headers = headers or {}

    def to_bytes(self) -> bytes:
        """
        Convert the response to bytes for sending over the network.
        
        Returns:
            The HTTP response as bytes
        """
        reason = HTTP_STATUS_CODES.get(self.status, "Unknown")
        response = f"HTTP/1.1 {self.status} {reason}\r\n"
        self.headers['Content-Length'] = len(self.body.encode())
        for k, v in self.headers.items():
            response += f"{k}: {v}\r\n"
        response += "\r\n" + self.body
        return response.encode()

    @staticmethod
    def json(data: Any, status: int = 200, headers: Optional[Dict[str, Any]] = None) -> 'Response':
        """
        Create a JSON response.
        
        Args:
            data: The data to serialize as JSON
            status: The HTTP status code
            headers: Optional HTTP headers
            
        Returns:
            A Response object with JSON content
        """
        body = json.dumps(data)
        headers = headers or {}
        headers['Content-Type'] = 'application/json'
        return Response(body, status, headers)

    @staticmethod
    def text(data: str, status: int = 200, headers: Optional[Dict[str, Any]] = None) -> 'Response':
        """
        Create a plain text response.
        
        Args:
            data: The text content
            status: The HTTP status code
            headers: Optional HTTP headers
            
        Returns:
            A Response object with text content
        """
        headers = headers or {}
        headers['Content-Type'] = 'text/plain'
        return Response(data, status, headers)