"""
WebSocket implementation for HTTPy.

This module provides WebSocket support for the HTTP server.
"""

import asyncio
import base64
import hashlib
import struct
from enum import Enum
from typing import Dict, Any, Optional, Union, Callable, List, Tuple

class WebSocketOpCode(Enum):
    """WebSocket operation codes."""
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA

class WebSocketMessage:
    """Represents a WebSocket message."""

    def __init__(self, opcode: WebSocketOpCode, data: bytes):
        """
        Initialize a new WebSocket message.

        Args:
            opcode: The WebSocket operation code
            data: The message data
        """
        self.opcode = opcode
        self.data = data

    @property
    def is_text(self) -> bool:
        """Check if this is a text message."""
        return self.opcode == WebSocketOpCode.TEXT

    @property
    def is_binary(self) -> bool:
        """Check if this is a binary message."""
        return self.opcode == WebSocketOpCode.BINARY

    @property
    def is_close(self) -> bool:
        """Check if this is a close message."""
        return self.opcode == WebSocketOpCode.CLOSE

    @property
    def is_ping(self) -> bool:
        """Check if this is a ping message."""
        return self.opcode == WebSocketOpCode.PING

    @property
    def is_pong(self) -> bool:
        """Check if this is a pong message."""
        return self.opcode == WebSocketOpCode.PONG

    def text(self) -> str:
        """
        Get the message data as text.

        Returns:
            The message data decoded as UTF-8
        """
        return self.data.decode('utf-8')

class WebSocketConnection:
    """Represents a WebSocket connection."""

    def __init__(self, client_sock: asyncio.StreamWriter, path: str, headers: Dict[str, str], path_params: Dict[str, str] = None):
        """
        Initialize a new WebSocket connection.

        Args:
            client_sock: The client socket
            path: The request path
            headers: The HTTP headers
            path_params: Path parameters extracted from the URL
        """
        self.writer = client_sock
        self.path = path
        self.headers = headers
        self.path_params = path_params or {}
        self.closed = False
        self._reader = None  # Will be set when needed

    async def send(self, message: Union[str, bytes], opcode: Optional[WebSocketOpCode] = None) -> None:
        """
        Send a message to the client.

        Args:
            message: The message to send
            opcode: The WebSocket operation code (defaults to TEXT for str, BINARY for bytes)
        """
        if self.closed:
            return

        if opcode is None:
            opcode = WebSocketOpCode.TEXT if isinstance(message, str) else WebSocketOpCode.BINARY

        if isinstance(message, str):
            message = message.encode('utf-8')

        # Create the frame header
        header = bytearray()

        # First byte: FIN bit (1) + RSV bits (000) + opcode (4 bits)
        header.append(0x80 | opcode.value)

        # Second byte: MASK bit (0) + payload length
        length = len(message)
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.append(126)
            header.extend(struct.pack('!H', length))
        else:
            header.append(127)
            header.extend(struct.pack('!Q', length))

        # Write the header and payload
        self.writer.write(header)
        self.writer.write(message)
        await self.writer.drain()

    async def send_text(self, message: str) -> None:
        """
        Send a text message to the client.

        Args:
            message: The text message to send
        """
        await self.send(message, WebSocketOpCode.TEXT)

    async def send_binary(self, message: bytes) -> None:
        """
        Send a binary message to the client.

        Args:
            message: The binary message to send
        """
        await self.send(message, WebSocketOpCode.BINARY)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """
        Close the WebSocket connection.

        Args:
            code: The close code
            reason: The close reason
        """
        if self.closed:
            return

        # Create close frame payload
        payload = struct.pack('!H', code)
        if reason:
            payload += reason.encode('utf-8')

        # Send close frame
        await self.send(payload, WebSocketOpCode.CLOSE)
        self.closed = True
        self.writer.close()
        await self.writer.wait_closed()

    async def ping(self, data: bytes = b'') -> None:
        """
        Send a ping message to the client.

        Args:
            data: Optional ping data
        """
        await self.send(data, WebSocketOpCode.PING)

    async def pong(self, data: bytes = b'') -> None:
        """
        Send a pong message to the client.

        Args:
            data: Optional pong data
        """
        await self.send(data, WebSocketOpCode.PONG)

    async def receive(self) -> WebSocketMessage:
        """
        Receive a message from the client.

        Returns:
            A WebSocketMessage object

        Raises:
            ConnectionError: If the connection is closed
        """
        if self.closed:
            raise ConnectionError("WebSocket connection is closed")

        # Create a reader from the writer's transport if not already created
        if self._reader is None:
            transport = self.writer.transport
            self._reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self._reader)
            await asyncio.get_event_loop().connect_accepted_socket(
                lambda: protocol, transport.get_extra_info('socket')
            )

        # Read the header (2 bytes minimum)
        header = await self._reader.readexactly(2)

        # Parse the header
        fin = (header[0] & 0x80) != 0
        opcode = WebSocketOpCode(header[0] & 0x0F)
        masked = (header[1] & 0x80) != 0
        payload_length = header[1] & 0x7F

        # Read extended payload length if needed
        if payload_length == 126:
            payload_length = struct.unpack('!H', await self._reader.readexactly(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack('!Q', await self._reader.readexactly(8))[0]

        # Read mask if present
        mask = await self._reader.readexactly(4) if masked else None

        # Read payload
        payload = await self._reader.readexactly(payload_length)

        # Unmask payload if needed
        if masked:
            unmasked = bytearray(payload_length)
            for i in range(payload_length):
                unmasked[i] = payload[i] ^ mask[i % 4]
            payload = bytes(unmasked)

        # Handle control frames
        if opcode == WebSocketOpCode.PING:
            # Automatically respond to pings
            await self.pong(payload)
        elif opcode == WebSocketOpCode.CLOSE:
            # Parse close code and reason
            if len(payload) >= 2:
                code = struct.unpack('!H', payload[:2])[0]
                reason = payload[2:].decode('utf-8', errors='replace') if len(payload) > 2 else ""
                # Echo the close frame
                await self.close(code, reason)
            else:
                # No code provided, use default
                await self.close()

        # Return the message
        return WebSocketMessage(opcode, payload)

async def handle_websocket_handshake(request, client_sock: asyncio.StreamWriter) -> Optional[WebSocketConnection]:
    """
    Handle a WebSocket handshake request.

    Args:
        request: The HTTP request
        client_sock: The client socket

    Returns:
        A WebSocketConnection if the handshake was successful, None otherwise
    """
    # Check for required headers
    if 'Upgrade' not in request.headers or request.headers['Upgrade'].lower() != 'websocket':
        return None

    if 'Connection' not in request.headers or 'upgrade' not in request.headers['Connection'].lower():
        return None

    if 'Sec-WebSocket-Key' not in request.headers:
        return None

    if 'Sec-WebSocket-Version' not in request.headers or request.headers['Sec-WebSocket-Version'] != '13':
        return None

    # Calculate the Sec-WebSocket-Accept header
    key = request.headers['Sec-WebSocket-Key']
    accept = base64.b64encode(
        hashlib.sha1(f"{key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11".encode()).digest()
    ).decode()

    # Send the handshake response
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    client_sock.write(response.encode())
    await client_sock.drain()

    # Create and return the WebSocket connection
    return WebSocketConnection(client_sock, request.path, request.headers, request.path_params)

def websocket(path: str) -> Callable:
    """
    Decorator to register a WebSocket route.

    Args:
        path: The URL path pattern

    Returns:
        A decorator function
    """
    from .routing import ROUTES, Route

    def decorator(func: Callable) -> Callable:
        # Create a special WebSocket route
        route = Route("WEBSOCKET", path, func)
        ROUTES.append(route)
        return func

    return decorator
