"""
HTTP Server implementation for PyHTTP.

This module provides the core functionality for creating an HTTP server.
"""

import asyncio
import socket

from .http import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from .request import Request
from .response import Response
from .routing import ROUTES, Route

# ---------------- SERVER -----------------------
async def handle_socket(client_sock: socket.socket) -> None:
    """
    Handle a client socket connection.

    Args:
        client_sock: The client socket
    """
    loop = asyncio.get_event_loop()
    client_sock.setblocking(False)
    buffer = b""
    keep_alive = True

    while keep_alive:
        try:
            chunk = await loop.sock_recv(client_sock, 4096)
            if not chunk:
                break
            buffer += chunk

            if b"\r\n\r\n" not in buffer:
                continue

            header_part, remaining = buffer.split(b"\r\n\r\n", 1)
            lines = header_part.decode().split("\r\n")
            request_line = lines[0]
            method, path, _ = request_line.split()

            headers = {}
            for line in lines[1:]:
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers[key] = value

            content_length = int(headers.get("Content-Length", "0"))
            body = remaining

            while len(body) < content_length:
                more = await loop.sock_recv(client_sock, 4096)
                if not more:
                    break
                body += more

            conn_header = headers.get("Connection", "").lower()
            keep_alive = conn_header != "close"

            for route in ROUTES:
                path_params = route.match(method, path)
                if path_params:
                    req = Request(method, path, headers, body.decode(), path_params)
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

            buffer = b""

        except Exception as e:
            await loop.sock_sendall(client_sock, Response("Internal Server Error", HTTP_500_INTERNAL_SERVER_ERROR).to_bytes())
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
