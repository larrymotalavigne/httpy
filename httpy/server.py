"""
HTTP Server implementation for HTTPy.

This module provides the core functionality for creating an HTTP server.
"""

import asyncio
import socket
import os
import ssl
from typing import Optional, Dict, Any

from .logging import logger

from .status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from .request import Request
from .response import Response
from .routing import ROUTES, Route
from .websocket import handle_websocket_handshake, WebSocketConnection
from .http2 import upgrade_to_http2, handle_http2_connection
from .http1 import handle_http1_connection

# Try to import HTTP/3 support
try:
    from .http3 import run_http3_server, AIOQUIC_AVAILABLE
except ImportError:
    AIOQUIC_AVAILABLE = False
    logger.warning("HTTP/3 support not available. Install with 'pip install aioquic'")

# ---------------- SERVER -----------------------
async def handle_socket(client_sock: socket.socket) -> None:
    """
    Handle a client socket connection.

    Args:
        client_sock: The client socket
    """
    client_addr = client_sock.getpeername()
    logger.debug(f"New connection from {client_addr[0]}:{client_addr[1]}")

    loop = asyncio.get_event_loop()
    client_sock.setblocking(False)

    # Create StreamReader/StreamWriter for protocol support
    reader, writer = await asyncio.open_connection(sock=client_sock)

    # First check for WebSocket or HTTP/2 upgrade
    try:
        # Read the first part of the request to check for upgrades
        data = await reader.readuntil(b"\r\n\r\n")
        reader._buffer.extendleft([data])  # Put the data back in the buffer

        # Check for WebSocket upgrade
        if b"upgrade: websocket" in data.lower() and b"connection:" in data.lower() and b"upgrade" in data.lower():
            # Handle WebSocket connection
            logger.debug("WebSocket upgrade requested")
            await handle_websocket_connection(reader, writer)
            return

        # Check for HTTP/2 upgrade
        elif b"upgrade: h2c" in data.lower() and b"connection:" in data.lower() and b"upgrade" in data.lower():
            # Handle HTTP/2 connection
            logger.debug("HTTP/2 upgrade requested")
            await handle_http2_connection(reader, writer)
            return

    except Exception as e:
        # If there's an error checking for upgrades, fall back to HTTP/1.1
        logger.error(f"Error checking for protocol upgrades: {str(e)}")
        logger.debug("Falling back to HTTP/1.1")

    # Handle HTTP/1.1 connection
    await handle_http1_connection(loop, client_sock, reader, writer)

    # Close the socket when done
    client_sock.close()

async def handle_websocket_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """
    Handle a WebSocket connection.

    Args:
        reader: The stream reader
        writer: The stream writer
    """
    # Read the HTTP request
    request_line = await reader.readline()
    headers = {}

    # Parse headers
    while True:
        line = await reader.readline()
        if line == b"\r\n":
            break

        if b":" in line:
            key, value = line.decode("latin1").strip().split(":", 1)
            headers[key.strip()] = value.strip()

    # Extract path from request line
    method, path, _ = request_line.decode("latin1").strip().split(" ", 2)

    # Create request object
    req = Request(method, path, headers, "", {}, {})

    # Find WebSocket route
    for route in ROUTES:
        path_params = route.match("WEBSOCKET", path)
        if path_params is not None:
            req.path_params = path_params
            # Handle WebSocket handshake
            ws_conn = await handle_websocket_handshake(req, writer)
            if ws_conn:
                # Call WebSocket handler
                await route.handler(ws_conn)
            break

async def run(host: str = "127.0.0.1", port: int = 8080, ssl_context: ssl.SSLContext = None, 
              http3_port: Optional[int] = None) -> None:
    """
    Run the HTTP server.

    Args:
        host: The host to bind to
        port: The port to listen on
        ssl_context: Optional SSL context for HTTPS and HTTP/2.0 support
        http3_port: Optional port for HTTP/3 support (requires SSL)
    """
    logger.info(f"Starting HTTPy server on {host}:{port}")

    # Configure server socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((host, port))
        server_sock.listen(100)
        server_sock.setblocking(False)
        logger.debug(f"Server socket bound to {host}:{port}")
    except OSError as e:
        logger.error(f"Failed to bind to {host}:{port}: {str(e)}")
        raise

    # Start HTTP/3 server if requested and available
    http3_server = None
    if http3_port and ssl_context and AIOQUIC_AVAILABLE:
        # Extract certificate and key paths from SSL context
        # This is a bit hacky, but there's no direct way to get the paths from the context
        cert_file = ssl_context.get_ca_certs()
        key_file = None

        # If we can't get the paths, we can't start HTTP/3
        if cert_file and key_file:
            http3_server = await run_http3_server(host, http3_port, cert_file, key_file)
            print(f"HTTP/3 server running on https://{host}:{http3_port}")
        else:
            logger.warning("Could not start HTTP/3 server: certificate and key paths required")
    elif http3_port and not AIOQUIC_AVAILABLE:
        logger.warning("HTTP/3 support requested but aioquic not available. Install with 'pip install aioquic'")

    if ssl_context:
        logger.info(f"Server running on https://{host}:{port} (HTTP/2.0 enabled)")
        # For HTTP/2.0 support with ALPN
        ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    else:
        logger.info(f"Server running on http://{host}:{port}")

    loop = asyncio.get_event_loop()
    logger.info("Server started and ready to accept connections")

    try:
        while True:
            client_sock, client_addr = await loop.sock_accept(server_sock)
            logger.debug(f"Accepted connection from {client_addr[0]}:{client_addr[1]}")

            if ssl_context:
                # Wrap socket with SSL for HTTPS and HTTP/2.0
                try:
                    ssl_sock = ssl_context.wrap_socket(
                        client_sock,
                        server_side=True,
                        do_handshake_on_connect=False
                    )
                    ssl_sock.setblocking(False)
                    loop.create_task(handle_socket(ssl_sock))
                except ssl.SSLError as e:
                    logger.error(f"SSL error: {str(e)}")
                    client_sock.close()
            else:
                loop.create_task(handle_socket(client_sock))
    except asyncio.CancelledError:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Unexpected error in server loop: {str(e)}")
        # Re-raise the exception to allow tests to catch it
        raise
    finally:
        logger.info("Server shutting down")
        server_sock.close()
