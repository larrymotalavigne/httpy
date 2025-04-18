"""
HTTP/1.1 implementation for HTTPy.

This module provides HTTP/1.1 support for the HTTP server.
"""

import asyncio
import re
import io
from urllib.parse import parse_qs
from typing import Dict, Any, Optional, Tuple, Union

from .request import Request
from .response import Response
from .routing import ROUTES
from .status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)

# Precompile regex patterns for better performance
HEADER_PATTERN = re.compile(r'([^:]+):\s*(.*)')
REQUEST_LINE_PATTERN = re.compile(r'([A-Z]+)\s+([^ ]+)\s+HTTP/\d\.\d')

# Buffer size for socket operations - larger buffer for better performance
BUFFER_SIZE = 8192

async def handle_http1_request(
    loop: asyncio.AbstractEventLoop,
    client_sock: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter
) -> Tuple[bool, Optional[Request]]:
    """
    Handle an HTTP/1.1 request.

    Args:
        loop: The event loop
        client_sock: The client socket
        reader: The stream reader
        writer: The stream writer

    Returns:
        A tuple of (keep_alive, request) where keep_alive is a boolean indicating
        whether the connection should be kept alive, and request is the parsed
        HTTP request or None if the connection should be closed.
    """
    buffer = bytearray(BUFFER_SIZE)  # Preallocate buffer for better performance
    buffer_view = memoryview(buffer)  # Use memoryview for zero-copy operations
    buffer_len = 0

    # Use a preallocated buffer for better performance
    n = await loop.sock_recv_into(client_sock, buffer_view[buffer_len:])
    if not n:
        return False, None

    buffer_len += n
    data = buffer_view[:buffer_len]

    # Find the header/body separator
    header_end = data.obj.find(b"\r\n\r\n", 0, buffer_len)
    if header_end == -1:
        # If buffer is full but no header end found, expand the buffer
        if buffer_len == len(buffer):
            new_buffer = bytearray(len(buffer) * 2)
            new_buffer[:buffer_len] = buffer[:buffer_len]
            buffer = new_buffer
            buffer_view = memoryview(buffer)
        return False, None

    # Parse headers more efficiently
    header_data = bytes(data[:header_end]).decode('latin1')  # Use latin1 for better performance
    header_lines = header_data.split("\r\n")

    # Parse request line
    request_line = header_lines[0]
    match = REQUEST_LINE_PATTERN.match(request_line)
    if not match:
        raise ValueError(f"Invalid request line: {request_line}")

    method, path = match.groups()

    # Parse headers more efficiently
    headers = {}
    for line in header_lines[1:]:
        if not line:
            continue
        match = HEADER_PATTERN.match(line)
        if match:
            key, value = match.groups()
            headers[key] = value

    # Get content length and prepare to read body
    content_length = int(headers.get("Content-Length", "0"))
    body_start = header_end + 4  # Skip \r\n\r\n

    # Check if we need to read more data for the body
    body_end = body_start + content_length

    # For POST and PUT requests, ensure we read the full body
    if method in ["POST", "PUT"] and content_length > 0:
        # If we don't have the full body yet, read more data
        remaining_bytes = max(0, body_end - buffer_len)

        # If buffer is too small, expand it
        if body_end > len(buffer):
            new_buffer = bytearray(body_end)
            new_buffer[:buffer_len] = buffer[:buffer_len]
            buffer = new_buffer
            buffer_view = memoryview(buffer)

        # Read remaining bytes with timeout
        try:
            # Set a reasonable timeout for reading the body
            while remaining_bytes > 0:
                # Ensure we don't try to read beyond the buffer size
                read_size = min(remaining_bytes, len(buffer_view) - buffer_len)
                if read_size <= 0:
                    # Buffer is full but we need more data, expand the buffer
                    new_size = max(len(buffer) * 2, buffer_len + remaining_bytes)
                    new_buffer = bytearray(new_size)
                    new_buffer[:buffer_len] = buffer[:buffer_len]
                    buffer = new_buffer
                    buffer_view = memoryview(buffer)
                    read_size = min(remaining_bytes, len(buffer_view) - buffer_len)

                n = await asyncio.wait_for(
                    loop.sock_recv_into(client_sock, buffer_view[buffer_len:buffer_len + read_size]),
                    timeout=5.0  # 5 second timeout
                )
                if not n:
                    break  # Connection closed

                buffer_len += n
                remaining_bytes -= n
        except asyncio.TimeoutError:
            # If timeout occurs, use what we have so far
            pass
    else:
        # For other methods, just read what's available
        while buffer_len < body_end:
            try:
                n = await loop.sock_recv_into(client_sock, buffer_view[buffer_len:])
                if not n:
                    break
                buffer_len += n
            except Exception:
                break

    # Extract body (ensure we don't go beyond buffer_len)
    actual_body_end = min(body_end, buffer_len)
    body = bytes(buffer_view[body_start:actual_body_end])

    # Check if connection should be kept alive
    # In HTTP/1.1, connections are keep-alive by default unless explicitly closed
    conn_header = headers.get("Connection", "").lower()
    http_version = request_line.split(" ")[2] if len(request_line.split(" ")) > 2 else "HTTP/1.0"

    if http_version.startswith("HTTP/1.1"):
        # HTTP/1.1: Keep-alive by default unless explicitly closed
        keep_alive = conn_header != "close"
    else:
        # HTTP/1.0: Close by default unless explicitly kept alive
        keep_alive = conn_header == "keep-alive"

    # Parse query parameters if present
    query_params = {}
    if '?' in path:
        path, query_string = path.split('?', 1)
        query_params = parse_qs(query_string)
        # Convert lists to single values for simple cases
        for key, value in query_params.items():
            if len(value) == 1:
                query_params[key] = value[0]

    # Create request object - pass raw bytes for POST/PUT methods to handle binary data correctly
    if method in ["POST", "PUT"]:
        req = Request(method, path, headers, body, {}, query_params)
    else:
        # For other methods, decode to string for backward compatibility
        req = Request(method, path, headers, body.decode('utf-8', errors='replace'), {}, query_params)

    return keep_alive, req

async def handle_http1_connection(
    loop: asyncio.AbstractEventLoop,
    client_sock: asyncio.StreamWriter,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter
) -> None:
    """
    Handle an HTTP/1.1 connection.

    Args:
        loop: The event loop
        client_sock: The client socket
        reader: The stream reader
        writer: The stream writer
    """
    keep_alive = True

    while keep_alive:
        try:
            keep_alive, req = await handle_http1_request(loop, client_sock, reader, writer)

            if not req:
                break

            # Route matching
            for route in ROUTES:
                path_params = route.match(req.method, req.path)
                if path_params is not None:  # Check if path_params is not None instead of truthy
                    req.path_params = path_params
                    if req.method == "HEAD":
                        req.method = "GET"
                        res = await route.handler(req)
                        res.body = ""
                    else:
                        res = await route.handler(req)

                    if keep_alive:
                        res.headers['Connection'] = 'keep-alive'
                    else:
                        res.headers['Connection'] = 'close'

                    await loop.sock_sendall(client_sock, res.to_bytes())
                    break
            else:
                await loop.sock_sendall(client_sock, Response("Not Found", HTTP_404_NOT_FOUND).to_bytes())

        except Exception as e:
            try:
                await loop.sock_sendall(client_sock, Response(f"Internal Server Error: {str(e)}", HTTP_500_INTERNAL_SERVER_ERROR).to_bytes())
            except:
                pass  # Ignore errors when sending error response
            break
