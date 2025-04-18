"""
HTTP/3 implementation for HTTPy.

This module provides HTTP/3 support for the HTTP server using the QUIC protocol.
"""

import asyncio
import os
import ssl
import time
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from urllib.parse import urlparse

from .request import Request
from .response import Response
from .routing import ROUTES
from .status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)

# Check if aioquic is available
try:
    import aioquic
    from aioquic.asyncio import serve
    from aioquic.asyncio.protocol import QuicConnectionProtocol
    from aioquic.h3.connection import H3Connection
    from aioquic.h3.events import (
        DataReceived, HeadersReceived, H3Event, WebTransportStreamDataReceived
    )
    from aioquic.h3.exceptions import NoAvailablePushIDError
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.events import DatagramFrameReceived, ProtocolNegotiated, QuicEvent
    AIOQUIC_AVAILABLE = True
except ImportError:
    AIOQUIC_AVAILABLE = False
    logging.warning("aioquic not available, HTTP/3 support disabled. Install with 'pip install aioquic'")

if AIOQUIC_AVAILABLE:
    class HTTP3Protocol(QuicConnectionProtocol):
        """HTTP/3 protocol implementation."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.h3 = None
            self.requests = {}
            self.request_waiter = {}

        def http_event_received(self, event: H3Event) -> None:
            """
            Handle an HTTP/3 event.

            Args:
                event: The HTTP/3 event
            """
            if isinstance(event, HeadersReceived):
                # Extract request information from headers
                headers = {}
                method = None
                path = None

                for header, value in event.headers:
                    if header == b":method":
                        method = value.decode()
                    elif header == b":path":
                        path = value.decode()
                    elif header.startswith(b":"):
                        # Skip other pseudo-headers
                        continue
                    else:
                        headers[header.decode()] = value.decode()

                # Store request information
                self.requests[event.stream_id] = {
                    "method": method,
                    "path": path,
                    "headers": headers,
                    "body": b"",
                    "stream_id": event.stream_id,
                }

            elif isinstance(event, DataReceived):
                # Append request body data
                if event.stream_id in self.requests:
                    self.requests[event.stream_id]["body"] += event.data

                    # If this is the end of the request, process it
                    if event.stream_ended:
                        asyncio.create_task(self.process_request(event.stream_id))

        async def process_request(self, stream_id: int) -> None:
            """
            Process an HTTP/3 request.

            Args:
                stream_id: The stream ID
            """
            if stream_id not in self.requests:
                return

            request_data = self.requests[stream_id]
            method = request_data["method"]
            path = request_data["path"]
            headers = request_data["headers"]
            body = request_data["body"].decode("utf-8", errors="replace")

            # Parse query parameters
            query_params = {}
            if "?" in path:
                path, query_string = path.split("?", 1)
                # Simple query parameter parsing
                for param in query_string.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        query_params[key] = value
                    else:
                        query_params[param] = ""

            # Create request object
            req = Request(method, path, headers, body, {}, query_params)

            # Find matching route
            response = None
            for route in ROUTES:
                path_params = route.match(method, path)
                if path_params is not None:
                    req.path_params = path_params
                    try:
                        response = await route.handler(req)
                        break
                    except Exception as e:
                        response = Response(
                            f"Internal Server Error: {str(e)}",
                            HTTP_500_INTERNAL_SERVER_ERROR
                        )
                        break

            if response is None:
                response = Response("Not Found", HTTP_404_NOT_FOUND)

            # Send response
            await self.send_response(stream_id, response)

            # Clean up request data
            del self.requests[stream_id]

        async def send_response(self, stream_id: int, response: Response) -> None:
            """
            Send an HTTP/3 response.

            Args:
                stream_id: The stream ID
                response: The response to send
            """
            if self.h3 is None:
                return

            # Convert response to HTTP/3 format
            headers = [
                (b":status", str(response.status).encode()),
            ]

            # Add response headers
            for name, value in response.headers.items():
                headers.append((name.lower().encode(), str(value).encode()))

            # Send headers
            self.h3.send_headers(stream_id, headers, end_stream=False)

            # Send body
            self.h3.send_data(stream_id, response.body.encode(), end_stream=True)

        def quic_event_received(self, event: QuicEvent) -> None:
            """
            Handle a QUIC event.

            Args:
                event: The QUIC event
            """
            if isinstance(event, ProtocolNegotiated):
                if event.alpn_protocol == "h3":
                    self.h3 = H3Connection(self._quic)

            if self.h3 is not None:
                for h3_event in self.h3.handle_event(event):
                    self.http_event_received(h3_event)
else:
    class HTTP3Protocol:
        """Placeholder for HTTP/3 protocol when aioquic is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError("aioquic is required for HTTP/3 support")

class HTTP3Server:
    """HTTP/3 server implementation."""

    def __init__(self, host: str, port: int, ssl_certfile: str, ssl_keyfile: str):
        """
        Initialize a new HTTP/3 server.

        Args:
            host: The host to bind to
            port: The port to listen on
            ssl_certfile: Path to the SSL certificate file
            ssl_keyfile: Path to the SSL key file
        """
        if not AIOQUIC_AVAILABLE:
            raise ImportError("aioquic is required for HTTP/3 support")

        self.host = host
        self.port = port
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile
        self._server = None

    async def start(self) -> None:
        """Start the HTTP/3 server."""
        # Create QUIC configuration
        quic_config = QuicConfiguration(
            alpn_protocols=["h3"],
            is_client=False,
            max_datagram_frame_size=65536,
        )

        # Load SSL certificate and key
        quic_config.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)

        # Create server
        self._server = await serve(
            self.host,
            self.port,
            configuration=quic_config,
            create_protocol=HTTP3Protocol,
        )

        print(f"HTTP/3 server running on https://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the HTTP/3 server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

async def run_http3_server(host: str, port: int, ssl_certfile: str, ssl_keyfile: str) -> HTTP3Server:
    """
    Run an HTTP/3 server.

    Args:
        host: The host to bind to
        port: The port to listen on
        ssl_certfile: Path to the SSL certificate file
        ssl_keyfile: Path to the SSL key file

    Returns:
        The HTTP/3 server instance
    """
    if not AIOQUIC_AVAILABLE:
        logging.error("aioquic is required for HTTP/3 support")
        return None

    server = HTTP3Server(host, port, ssl_certfile, ssl_keyfile)
    await server.start()
    return server
