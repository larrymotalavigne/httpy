"""
HTTP/2.0 implementation for HTTPy.

This module provides HTTP/2.0 support for the HTTP server.
"""

import asyncio
import struct
import enum
from typing import Dict, Any, Optional, Union, Callable, List, Tuple, ByteString

# HTTP/2.0 constants
HTTP2_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
HTTP2_HEADER_TABLE_SIZE = 4096
HTTP2_ENABLE_PUSH = 1
HTTP2_MAX_CONCURRENT_STREAMS = 100
HTTP2_INITIAL_WINDOW_SIZE = 65535
HTTP2_MAX_FRAME_SIZE = 16384
HTTP2_MAX_HEADER_LIST_SIZE = 8192

class FrameType(enum.IntEnum):
    """HTTP/2.0 frame types."""
    DATA = 0x0
    HEADERS = 0x1
    PRIORITY = 0x2
    RST_STREAM = 0x3
    SETTINGS = 0x4
    PUSH_PROMISE = 0x5
    PING = 0x6
    GOAWAY = 0x7
    WINDOW_UPDATE = 0x8
    CONTINUATION = 0x9

class FrameFlag(enum.IntFlag):
    """HTTP/2.0 frame flags."""
    NO_FLAGS = 0x0
    ACK = 0x1
    END_STREAM = 0x1
    END_HEADERS = 0x4
    PADDED = 0x8
    PRIORITY = 0x20

class ErrorCode(enum.IntEnum):
    """HTTP/2.0 error codes."""
    NO_ERROR = 0x0
    PROTOCOL_ERROR = 0x1
    INTERNAL_ERROR = 0x2
    FLOW_CONTROL_ERROR = 0x3
    SETTINGS_TIMEOUT = 0x4
    STREAM_CLOSED = 0x5
    FRAME_SIZE_ERROR = 0x6
    REFUSED_STREAM = 0x7
    CANCEL = 0x8
    COMPRESSION_ERROR = 0x9
    CONNECT_ERROR = 0xa
    ENHANCE_YOUR_CALM = 0xb
    INADEQUATE_SECURITY = 0xc
    HTTP_1_1_REQUIRED = 0xd

class Frame:
    """Represents an HTTP/2.0 frame."""
    
    def __init__(self, frame_type: FrameType, flags: FrameFlag, stream_id: int, payload: bytes):
        """
        Initialize a new HTTP/2.0 frame.
        
        Args:
            frame_type: The frame type
            flags: The frame flags
            stream_id: The stream ID
            payload: The frame payload
        """
        self.type = frame_type
        self.flags = flags
        self.stream_id = stream_id
        self.payload = payload
    
    @classmethod
    def parse(cls, data: bytes) -> Tuple['Frame', bytes]:
        """
        Parse an HTTP/2.0 frame from bytes.
        
        Args:
            data: The bytes to parse
        
        Returns:
            A tuple of (frame, remaining_data)
        """
        if len(data) < 9:
            return None, data
        
        # Parse frame header
        length = struct.unpack("!I", b'\x00' + data[0:3])[0]
        frame_type = FrameType(data[3])
        flags = FrameFlag(data[4])
        stream_id = struct.unpack("!I", data[5:9])[0] & 0x7FFFFFFF
        
        # Check if we have the full frame
        if len(data) < 9 + length:
            return None, data
        
        # Extract payload
        payload = data[9:9+length]
        
        # Create frame
        frame = cls(frame_type, flags, stream_id, payload)
        
        # Return frame and remaining data
        return frame, data[9+length:]
    
    def serialize(self) -> bytes:
        """
        Serialize the frame to bytes.
        
        Returns:
            The serialized frame
        """
        # Create frame header
        header = bytearray(9)
        
        # Length (3 bytes)
        length = len(self.payload)
        header[0:3] = struct.pack("!I", length)[1:4]
        
        # Type (1 byte)
        header[3] = self.type
        
        # Flags (1 byte)
        header[4] = self.flags
        
        # Stream ID (4 bytes)
        header[5:9] = struct.pack("!I", self.stream_id & 0x7FFFFFFF)
        
        # Combine header and payload
        return bytes(header) + self.payload

class HTTP2Connection:
    """Represents an HTTP/2.0 connection."""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Initialize a new HTTP/2.0 connection.
        
        Args:
            reader: The stream reader
            writer: The stream writer
        """
        self.reader = reader
        self.writer = writer
        self.streams = {}
        self.next_stream_id = 1
        self.closed = False
        
        # Settings
        self.local_settings = {
            0x1: HTTP2_HEADER_TABLE_SIZE,
            0x2: HTTP2_ENABLE_PUSH,
            0x3: HTTP2_MAX_CONCURRENT_STREAMS,
            0x4: HTTP2_INITIAL_WINDOW_SIZE,
            0x5: HTTP2_MAX_FRAME_SIZE,
            0x6: HTTP2_MAX_HEADER_LIST_SIZE
        }
        self.remote_settings = {}
    
    async def send_frame(self, frame: Frame) -> None:
        """
        Send a frame to the client.
        
        Args:
            frame: The frame to send
        """
        if self.closed:
            return
        
        self.writer.write(frame.serialize())
        await self.writer.drain()
    
    async def send_settings(self) -> None:
        """Send the initial SETTINGS frame."""
        payload = bytearray()
        for key, value in self.local_settings.items():
            payload.extend(struct.pack("!HI", key, value))
        
        frame = Frame(FrameType.SETTINGS, FrameFlag.NO_FLAGS, 0, payload)
        await self.send_frame(frame)
    
    async def send_settings_ack(self) -> None:
        """Send a SETTINGS ACK frame."""
        frame = Frame(FrameType.SETTINGS, FrameFlag.ACK, 0, b'')
        await self.send_frame(frame)
    
    async def send_ping(self, data: bytes = b'\x00' * 8) -> None:
        """
        Send a PING frame.
        
        Args:
            data: The ping data (must be 8 bytes)
        """
        if len(data) != 8:
            data = data.ljust(8, b'\x00')[:8]
        
        frame = Frame(FrameType.PING, FrameFlag.NO_FLAGS, 0, data)
        await self.send_frame(frame)
    
    async def send_ping_ack(self, data: bytes) -> None:
        """
        Send a PING ACK frame.
        
        Args:
            data: The ping data to acknowledge
        """
        frame = Frame(FrameType.PING, FrameFlag.ACK, 0, data)
        await self.send_frame(frame)
    
    async def send_goaway(self, error_code: ErrorCode = ErrorCode.NO_ERROR, debug_data: bytes = b'') -> None:
        """
        Send a GOAWAY frame.
        
        Args:
            error_code: The error code
            debug_data: Optional debug data
        """
        payload = struct.pack("!II", self.next_stream_id - 1, error_code)
        payload += debug_data
        
        frame = Frame(FrameType.GOAWAY, FrameFlag.NO_FLAGS, 0, payload)
        await self.send_frame(frame)
        
        self.closed = True
        self.writer.close()
        await self.writer.wait_closed()
    
    async def handle_frame(self, frame: Frame) -> None:
        """
        Handle an incoming frame.
        
        Args:
            frame: The frame to handle
        """
        if frame.type == FrameType.SETTINGS:
            if frame.flags & FrameFlag.ACK:
                # SETTINGS ACK, nothing to do
                pass
            else:
                # Parse SETTINGS
                for i in range(0, len(frame.payload), 6):
                    if i + 6 <= len(frame.payload):
                        key, value = struct.unpack("!HI", frame.payload[i:i+6])
                        self.remote_settings[key] = value
                
                # Send ACK
                await self.send_settings_ack()
        
        elif frame.type == FrameType.PING:
            if frame.flags & FrameFlag.ACK:
                # PING ACK, nothing to do
                pass
            else:
                # Send PING ACK
                await self.send_ping_ack(frame.payload)
        
        elif frame.type == FrameType.GOAWAY:
            # Connection is being closed
            self.closed = True
            self.writer.close()
            await self.writer.wait_closed()
    
    async def run(self) -> None:
        """Run the HTTP/2.0 connection."""
        # Wait for client preface
        preface = await self.reader.readexactly(len(HTTP2_PREFACE))
        if preface != HTTP2_PREFACE:
            await self.send_goaway(ErrorCode.PROTOCOL_ERROR)
            return
        
        # Send initial SETTINGS frame
        await self.send_settings()
        
        # Process frames
        buffer = b''
        while not self.closed:
            try:
                # Read more data
                data = await self.reader.read(8192)
                if not data:
                    break
                
                buffer += data
                
                # Process frames
                while buffer:
                    frame, buffer = Frame.parse(buffer)
                    if frame is None:
                        break
                    
                    await self.handle_frame(frame)
            
            except asyncio.IncompleteReadError:
                break
            except Exception as e:
                await self.send_goaway(ErrorCode.INTERNAL_ERROR, str(e).encode())
                break
        
        # Close connection if not already closed
        if not self.closed:
            self.closed = True
            self.writer.close()
            await self.writer.wait_closed()

async def handle_http2_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """
    Handle an HTTP/2.0 connection.
    
    Args:
        reader: The stream reader
        writer: The stream writer
    """
    conn = HTTP2Connection(reader, writer)
    await conn.run()

async def upgrade_to_http2(request, client_sock: asyncio.StreamWriter) -> bool:
    """
    Upgrade an HTTP/1.1 connection to HTTP/2.0.
    
    Args:
        request: The HTTP request
        client_sock: The client socket
    
    Returns:
        True if the upgrade was successful, False otherwise
    """
    # Check for HTTP/2.0 upgrade headers
    if 'Upgrade' not in request.headers or request.headers['Upgrade'] != 'h2c':
        return False
    
    if 'HTTP2-Settings' not in request.headers:
        return False
    
    # Send 101 Switching Protocols
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Connection: Upgrade\r\n"
        "Upgrade: h2c\r\n"
        "\r\n"
    )
    client_sock.write(response.encode())
    await client_sock.drain()
    
    # Create HTTP/2.0 connection
    # Note: In a real implementation, we would need to convert the socket to StreamReader/StreamWriter
    # For now, we'll just return True to indicate the upgrade was successful
    return True