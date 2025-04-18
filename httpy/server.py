"""
HTTP Server implementation for HTTPy.

This module provides the core functionality for creating an HTTP server.
"""

import asyncio
import socket
import io
import re
from urllib.parse import parse_qs

from .http import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from .request import Request
from .response import Response
from .routing import ROUTES, Route

# Precompile regex patterns for better performance
HEADER_PATTERN = re.compile(r'([^:]+):\s*(.*)')
REQUEST_LINE_PATTERN = re.compile(r'([A-Z]+)\s+([^ ]+)\s+HTTP/\d\.\d')

# Buffer size for socket operations - larger buffer for better performance
BUFFER_SIZE = 8192

# ---------------- SERVER -----------------------
async def handle_socket(client_sock: socket.socket) -> None:
    """
    Handle a client socket connection.

    Args:
        client_sock: The client socket
    """
    loop = asyncio.get_event_loop()
    client_sock.setblocking(False)
    buffer = bytearray(BUFFER_SIZE)  # Preallocate buffer for better performance
    buffer_view = memoryview(buffer)  # Use memoryview for zero-copy operations
    buffer_len = 0
    keep_alive = True

    while keep_alive:
        try:
            # Use a preallocated buffer for better performance
            n = await loop.sock_recv_into(client_sock, buffer_view[buffer_len:])
            if not n:
                break

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
                continue

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

            # If we don't have the full body yet, read more data
            while buffer_len < body_end:
                # If buffer is too small, expand it
                if body_end > len(buffer):
                    new_buffer = bytearray(body_end)
                    new_buffer[:buffer_len] = buffer[:buffer_len]
                    buffer = new_buffer
                    buffer_view = memoryview(buffer)

                n = await loop.sock_recv_into(client_sock, buffer_view[buffer_len:])
                if not n:
                    break
                buffer_len += n

            # Extract body
            body = bytes(buffer_view[body_start:body_end])

            # Check if connection should be kept alive
            conn_header = headers.get("Connection", "").lower()
            keep_alive = conn_header != "close" and headers.get("Connection", "").lower() == "keep-alive"

            # Parse query parameters if present
            query_params = {}
            if '?' in path:
                path, query_string = path.split('?', 1)
                query_params = parse_qs(query_string)
                # Convert lists to single values for simple cases
                for key, value in query_params.items():
                    if len(value) == 1:
                        query_params[key] = value[0]

            # Route matching
            for route in ROUTES:
                path_params = route.match(method, path)
                if path_params is not None:  # Check if path_params is not None instead of truthy
                    req = Request(method, path, headers, body.decode('utf-8', errors='replace'), path_params, query_params)
                    if method == "HEAD":
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

            # Reset buffer for next request if keep-alive
            if keep_alive:
                # Move any remaining data to the beginning of the buffer
                remaining = buffer_len - body_end
                if remaining > 0:
                    buffer[:remaining] = buffer[body_end:buffer_len]
                buffer_len = remaining
            else:
                break

        except Exception as e:
            try:
                await loop.sock_sendall(client_sock, Response(f"Internal Server Error: {str(e)}", HTTP_500_INTERNAL_SERVER_ERROR).to_bytes())
            except:
                pass  # Ignore errors when sending error response
            break

    client_sock.close()

async def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    """
    Run the HTTP server.

    Args:
        host: The host to bind to
        port: The port to listen on
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(100)
    server_sock.setblocking(False)

    print(f"Server running on http://{host}:{port}")
    loop = asyncio.get_event_loop()
    while True:
        client_sock, _ = await loop.sock_accept(server_sock)
        loop.create_task(handle_socket(client_sock))
