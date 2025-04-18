#!/usr/bin/env python3
"""
Unit tests for the HTTPy HTTP/1.1 functionality.
"""

import sys
import os
import unittest
import asyncio
import socket
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request, Response, get
from httpy.routing import ROUTES
from httpy.http1 import handle_http1_connection, handle_http1_request


class TestHTTP1(unittest.IsolatedAsyncioTestCase):
    """Tests for the HTTP/1.1 functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    @patch('asyncio.get_event_loop')
    async def test_handle_http1_request(self, mock_get_loop):
        """Test handle_http1_request function."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop

        # Mock socket
        mock_socket = MagicMock()

        # Mock reader and writer
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Mock sock_recv_into to simulate receiving HTTP request data
        # We'll use a side effect function to control the behavior
        call_count = 0
        def sock_recv_into_side_effect(sock, buffer_view):
            nonlocal call_count
            if call_count == 0:
                # First call: write the request data into the buffer
                data = b"GET /test HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
                buffer_view[:len(data)] = data
                call_count += 1
                return len(data)
            else:
                # Subsequent calls: return 0 to indicate end of data
                return 0

        mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

        # Call handle_http1_request
        keep_alive, req = await handle_http1_request(mock_loop, mock_socket, mock_reader, mock_writer)

        # Check that the request was parsed correctly
        self.assertTrue(keep_alive)
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.path, "/test")
        self.assertEqual(req.headers["Host"], "localhost")
        self.assertEqual(req.headers["Connection"], "keep-alive")

    @patch('asyncio.get_event_loop')
    async def test_handle_http1_post_request_with_binary_data(self, mock_get_loop):
        """Test handle_http1_request function with POST and binary data."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop

        # Mock socket
        mock_socket = MagicMock()

        # Mock reader and writer
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Create binary data for the request body
        binary_data = b'\x00\x01\x02\x03\x04\xFF\xFE\xFD\xFC\xFB'
        content_length = len(binary_data)

        # Mock sock_recv_into to simulate receiving HTTP request data with binary body
        call_count = 0
        def sock_recv_into_side_effect(sock, buffer_view):
            nonlocal call_count
            if call_count == 0:
                # First call: write the request headers into the buffer
                headers = f"POST /echo HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/octet-stream\r\nContent-Length: {content_length}\r\n\r\n"
                data = headers.encode('ascii') + binary_data
                buffer_view[:len(data)] = data
                call_count += 1
                return len(data)
            else:
                # Subsequent calls: return 0 to indicate end of data
                return 0

        mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

        # Call handle_http1_request
        keep_alive, req = await handle_http1_request(mock_loop, mock_socket, mock_reader, mock_writer)

        # Check that the request was parsed correctly
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.path, "/echo")
        self.assertEqual(req.headers["Host"], "localhost")
        self.assertEqual(req.headers["Content-Type"], "application/octet-stream")
        self.assertEqual(req.headers["Content-Length"], str(content_length))

        # Check that the binary body was preserved
        self.assertEqual(req.body, binary_data)
        self.assertTrue(isinstance(req.body, bytes))

    @patch('asyncio.get_event_loop')
    async def test_handle_http1_connection(self, mock_get_loop):
        """Test handle_http1_connection function."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop

        # Mock socket
        mock_socket = MagicMock()

        # Mock reader and writer
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Mock handle_http1_request to return a request
        with patch('httpy.http1.handle_http1_request') as mock_handle_request:
            # First call returns a request, second call returns (False, None) to end the loop
            mock_handle_request.side_effect = [
                (True, Request("GET", "/test", {"Host": "localhost"}, "", {}, {})),
                (False, None)
            ]

            # Clear the ROUTES list and set up a test route
            ROUTES.clear()

            # Create a Route object directly instead of using the decorator
            async def test_handler(req):
                return Response.text("Test Response")

            from httpy.routing import Route
            ROUTES.append(Route("GET", "/test", test_handler))

            # Call handle_http1_connection
            await handle_http1_connection(mock_loop, mock_socket, mock_reader, mock_writer)

            # Check that handle_http1_request was called
            self.assertEqual(mock_handle_request.call_count, 2)

            # Check that sock_sendall was called with a response
            mock_loop.sock_sendall.assert_called()
            # Get the bytes that were sent
            sent_bytes = mock_loop.sock_sendall.call_args[0][1]
            sent_text = sent_bytes.decode('utf-8')

            # Check that the response contains the expected content
            self.assertIn("HTTP/1.1 200 OK", sent_text)
            self.assertIn("Test Response", sent_text)


if __name__ == "__main__":
    unittest.main()
