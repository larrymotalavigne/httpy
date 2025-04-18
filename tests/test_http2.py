#!/usr/bin/env python3
"""
Unit tests for the HTTPy HTTP/2.0 functionality.
"""

import sys
import os
import unittest
import asyncio
import socket
import struct
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request, Response, get
from httpy.routing import ROUTES
from httpy.http2 import (
    Frame, FrameType, FrameFlag, ErrorCode, 
    HTTP2Connection, handle_http2_connection, upgrade_to_http2
)


class TestHTTP2(unittest.IsolatedAsyncioTestCase):
    """Tests for the HTTP/2.0 functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    def test_frame_serialize_parse(self):
        """Test Frame serialization and parsing."""
        # Create a frame
        frame = Frame(
            frame_type=FrameType.HEADERS,
            flags=FrameFlag.END_HEADERS | FrameFlag.END_STREAM,
            stream_id=1,
            payload=b"test payload"
        )

        # Serialize the frame
        serialized = frame.serialize()

        # Parse the serialized frame
        parsed_frame, remaining = Frame.parse(serialized)

        # Check that the parsed frame matches the original
        self.assertEqual(parsed_frame.type, frame.type)
        self.assertEqual(parsed_frame.flags, frame.flags)
        self.assertEqual(parsed_frame.stream_id, frame.stream_id)
        self.assertEqual(parsed_frame.payload, frame.payload)
        self.assertEqual(remaining, b"")

    @patch('asyncio.StreamReader')
    @patch('asyncio.StreamWriter')
    async def test_http2_connection_init(self, mock_writer, mock_reader):
        """Test HTTP2Connection initialization."""
        # Create an HTTP2Connection
        conn = HTTP2Connection(mock_reader, mock_writer)

        # Check that the connection was initialized correctly
        self.assertEqual(conn.reader, mock_reader)
        self.assertEqual(conn.writer, mock_writer)
        self.assertEqual(conn.streams, {})
        self.assertEqual(conn.next_stream_id, 1)
        self.assertFalse(conn.closed)

        # Check that the settings were initialized correctly
        self.assertIn(0x1, conn.local_settings)  # HEADER_TABLE_SIZE
        self.assertIn(0x2, conn.local_settings)  # ENABLE_PUSH
        self.assertIn(0x3, conn.local_settings)  # MAX_CONCURRENT_STREAMS
        self.assertIn(0x4, conn.local_settings)  # INITIAL_WINDOW_SIZE
        self.assertIn(0x5, conn.local_settings)  # MAX_FRAME_SIZE
        self.assertIn(0x6, conn.local_settings)  # MAX_HEADER_LIST_SIZE

    @patch('asyncio.StreamReader')
    @patch('asyncio.StreamWriter')
    async def test_send_frame(self, mock_writer, mock_reader):
        """Test sending a frame."""
        # Create an HTTP2Connection
        mock_writer.drain = AsyncMock()  # Use AsyncMock for awaitable methods
        conn = HTTP2Connection(mock_reader, mock_writer)

        # Create a frame
        frame = Frame(
            frame_type=FrameType.HEADERS,
            flags=FrameFlag.END_HEADERS | FrameFlag.END_STREAM,
            stream_id=1,
            payload=b"test payload"
        )

        # Send the frame
        await conn.send_frame(frame)

        # Check that the frame was written to the writer
        mock_writer.write.assert_called_once_with(frame.serialize())
        mock_writer.drain.assert_called_once()

    @patch('asyncio.StreamReader')
    @patch('asyncio.StreamWriter')
    async def test_send_settings(self, mock_writer, mock_reader):
        """Test sending settings."""
        # Create an HTTP2Connection
        mock_writer.drain = AsyncMock()  # Use AsyncMock for awaitable methods
        conn = HTTP2Connection(mock_reader, mock_writer)

        # Send settings
        await conn.send_settings()

        # Check that a SETTINGS frame was written to the writer
        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_called_once()

        # Get the bytes that were written
        written_bytes = mock_writer.write.call_args[0][0]

        # Parse the frame
        frame, _ = Frame.parse(written_bytes)

        # Check that it's a SETTINGS frame
        self.assertEqual(frame.type, FrameType.SETTINGS)
        self.assertEqual(frame.flags, FrameFlag.NO_FLAGS)
        self.assertEqual(frame.stream_id, 0)

        # Check that the payload contains settings
        self.assertGreater(len(frame.payload), 0)

    @patch('asyncio.StreamReader')
    @patch('asyncio.StreamWriter')
    async def test_upgrade_to_http2(self, mock_writer, mock_reader):
        """Test upgrading to HTTP/2."""
        # Use AsyncMock for awaitable methods
        mock_writer.drain = AsyncMock()
        # Create a request with HTTP/2 upgrade headers
        req = Request(
            method="GET",
            path="/",
            headers={
                "Upgrade": "h2c",
                "Connection": "Upgrade, HTTP2-Settings",
                "HTTP2-Settings": "AAMAAABkAAQAAP__"  # Base64-encoded SETTINGS frame
            },
            body="",
            path_params={},
            query_params={}
        )

        # Upgrade to HTTP/2
        result = await upgrade_to_http2(req, mock_writer)

        # Check that the upgrade was successful
        self.assertTrue(result)

        # Check that the 101 response was written to the writer
        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_called_once()

        # Get the bytes that were written
        written_bytes = mock_writer.write.call_args[0][0]
        written_text = written_bytes.decode('utf-8')

        # Check that it's a 101 Switching Protocols response
        self.assertIn("HTTP/1.1 101 Switching Protocols", written_text)
        self.assertIn("Connection: Upgrade", written_text)
        self.assertIn("Upgrade: h2c", written_text)


if __name__ == "__main__":
    unittest.main()
