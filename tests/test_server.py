#!/usr/bin/env python3
"""
Unit tests for the HTTPy server functionality.
"""

import sys
import os
import unittest
import asyncio
import socket
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import ServerRequest, ServerResponse, get, run
from httpy.routing import ROUTES
from httpy.server import handle_socket


class TestServer(unittest.IsolatedAsyncioTestCase):
    """Tests for the server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    @patch('asyncio.get_event_loop')
    async def test_handle_socket(self, mock_get_loop):
        """Test handle_socket function."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop

        # Mock socket
        mock_socket = MagicMock()

        # Mock sock_recv to return HTTP request data
        mock_loop.sock_recv.side_effect = [
            b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n",
            b"",  # Empty response to break the loop
        ]

        # Clear the ROUTES list and set up a test route
        ROUTES.clear()

        # Create a Route object directly instead of using the decorator
        async def test_handler(req):
            return ServerResponse.text("Test Response")

        from httpy.routing import Route
        ROUTES.append(Route("GET", "/test", test_handler))

        # Call handle_socket
        await handle_socket(mock_socket)

        # Check that sock_sendall was called with a response
        mock_loop.sock_sendall.assert_called()
        # Get the bytes that were sent
        sent_bytes = mock_loop.sock_sendall.call_args[0][1]
        sent_text = sent_bytes.decode('utf-8')

        # Check that the response contains the expected content
        self.assertIn("HTTP/1.1 200 OK", sent_text)
        self.assertIn("Test Response", sent_text)

        # Check that the socket was closed
        mock_socket.close.assert_called_once()

    @patch('socket.socket')
    @patch('asyncio.get_event_loop')
    async def test_run(self, mock_get_loop, mock_socket_class):
        """Test run function."""
        # This test is more complex as it involves testing the server startup
        # We'll just test that the socket is set up correctly

        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop

        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance

        # Mock sock_accept to return a client socket and address
        mock_client_socket = MagicMock()
        mock_loop.sock_accept.return_value = (mock_client_socket, ('127.0.0.1', 12345))

        # Import run directly to avoid running the actual server
        from httpy.server import run

        # Call run (this will enter an infinite loop, so we'll need to break out)
        mock_loop.sock_accept.side_effect = KeyboardInterrupt()  # Break the loop

        try:
            await run(host="localhost", port=8080)
        except KeyboardInterrupt:
            pass

        # Check that the socket was set up correctly
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket_instance.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_socket_instance.bind.assert_called_once_with(('localhost', 8080))
        mock_socket_instance.listen.assert_called_once_with(100)
        mock_socket_instance.setblocking.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
