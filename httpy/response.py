"""
HTTP Response implementation for HTTPy.

This module provides the Response class for handling HTTP responses.
"""

import json
import io
from typing import Dict, Any, Optional, Union, Callable

from .status import HTTP_STATUS_CODES

# Cache of status lines for common status codes
STATUS_LINE_CACHE = {
    code: f"HTTP/1.1 {code} {reason}\r\n".encode()
    for code, reason in HTTP_STATUS_CODES.items()
}

# Common headers as bytes to avoid repeated encoding
CONTENT_TYPE_JSON = b"Content-Type: application/json\r\n"
CONTENT_TYPE_TEXT = b"Content-Type: text/plain\r\n"
CONTENT_LENGTH = b"Content-Length: "
CONNECTION_KEEP_ALIVE = b"Connection: keep-alive\r\n"
CONNECTION_CLOSE = b"Connection: close\r\n"
CRLF = b"\r\n"

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
        self._encoded_body = None  # Cache for encoded body

    def to_bytes(self) -> bytes:
        """
        Convert the response to bytes for sending over the network.

        This method is optimized for performance, especially with large responses.

        Returns:
            The HTTP response as bytes
        """
        # Use a BytesIO buffer for efficient concatenation
        buffer = io.BytesIO()

        # Write status line (use cached version if available)
        status_line = STATUS_LINE_CACHE.get(self.status)
        if status_line:
            buffer.write(status_line)
        else:
            reason = HTTP_STATUS_CODES.get(self.status, "Unknown")
            buffer.write(f"HTTP/1.1 {self.status} {reason}\r\n".encode())

        # Encode body only once
        if self._encoded_body is None:
            self._encoded_body = self.body.encode('utf-8')

        # Set content length
        content_length = len(self._encoded_body)
        buffer.write(CONTENT_LENGTH)
        buffer.write(str(content_length).encode())
        buffer.write(CRLF)

        # Write headers
        for k, v in self.headers.items():
            # Skip content-length as we've already added it
            if k.lower() == 'content-length':
                continue

            # Use cached headers for common cases
            if k.lower() == 'content-type':
                if v.lower() == 'application/json':
                    buffer.write(CONTENT_TYPE_JSON)
                    continue
                elif v.lower() == 'text/plain':
                    buffer.write(CONTENT_TYPE_TEXT)
                    continue
            elif k.lower() == 'connection':
                if v.lower() == 'keep-alive':
                    buffer.write(CONNECTION_KEEP_ALIVE)
                    continue
                elif v.lower() == 'close':
                    buffer.write(CONNECTION_CLOSE)
                    continue

            # For other headers, encode them normally
            buffer.write(f"{k}: {v}\r\n".encode())

        # End of headers
        buffer.write(CRLF)

        # Write body
        buffer.write(self._encoded_body)

        return buffer.getvalue()

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
        body = json.dumps(data, separators=(',', ':'))  # Use compact JSON encoding
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

    @staticmethod
    def html(data: str, status: int = 200, headers: Optional[Dict[str, Any]] = None) -> 'Response':
        """
        Create an HTML response.

        Args:
            data: The HTML content
            status: The HTTP status code
            headers: Optional HTTP headers

        Returns:
            A Response object with HTML content
        """
        headers = headers or {}
        headers['Content-Type'] = 'text/html'
        return Response(data, status, headers)

    @staticmethod
    def redirect(location: str, status: int = 302, headers: Optional[Dict[str, Any]] = None) -> 'Response':
        """
        Create a redirect response.

        Args:
            location: The URL to redirect to
            status: The HTTP status code (default: 302 Found)
            headers: Optional HTTP headers

        Returns:
            A Response object for redirection
        """
        headers = headers or {}
        headers['Location'] = location
        return Response("", status, headers)
