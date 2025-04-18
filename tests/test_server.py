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

from httpy import Request, Response, get, run
from httpy.routing import ROUTES
from httpy.server import handle_socket


class TestServer(unittest.IsolatedAsyncioTestCase):
    """Tests for the server functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    @patch('asyncio.get_event_loop')
    @patch('httpy.server.asyncio.get_event_loop')
    @patch('asyncio.open_connection')
    @patch('httpy.server.asyncio.open_connection')
    async def test_handle_socket(self, mock_server_open_connection, mock_open_connection, mock_server_get_loop, mock_get_loop):
        """Test handle_socket function."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop
        mock_server_get_loop.return_value = mock_loop

        # Mock StreamReader and StreamWriter
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (mock_reader, mock_writer)
        mock_server_open_connection.return_value = (mock_reader, mock_writer)

        # Mock socket
        mock_socket = MagicMock()

        # Mock sock_recv_into to simulate receiving HTTP request data
        # We'll use a side effect function to control the behavior
        call_count = 0
        def sock_recv_into_side_effect(sock, buffer_view):
            nonlocal call_count
            if call_count == 0:
                # First call: write the request data into the buffer
                data = b"GET /test HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
                buffer_view[:len(data)] = data
                call_count += 1
                return len(data)
            else:
                # Subsequent calls: return 0 to indicate end of data
                return 0

        mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

        # Clear the ROUTES list and set up a test route
        ROUTES.clear()

        # Create a Route object directly instead of using the decorator
        async def test_handler(req):
            return Response.text("Test Response")

        from httpy.routing import Route
        ROUTES.append(Route("GET", "/test", test_handler))

        # Set a timeout for the test to prevent hanging
        try:
            # Call handle_socket with a timeout
            await asyncio.wait_for(handle_socket(mock_socket), timeout=5.0)
        except asyncio.TimeoutError:
            self.fail("handle_socket timed out, indicating it might be stuck in a loop")

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
    @patch('httpy.server.asyncio.get_event_loop')
    async def test_run(self, mock_server_get_loop, mock_get_loop, mock_socket_class):
        """Test run function."""
        # This test is more complex as it involves testing the server startup
        # We'll just test that the socket is set up correctly

        # Set up mocks
        mock_loop = AsyncMock()
        mock_get_loop.return_value = mock_loop
        mock_server_get_loop.return_value = mock_loop

        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance

        # Mock sock_accept to return a client socket and address
        mock_client_socket = MagicMock()

        # Instead of using KeyboardInterrupt, we'll use a side effect function
        # that raises an exception after the first call
        call_count = 0
        def sock_accept_side_effect(*args, **kwargs):
            nonlocal call_count
            if call_count == 0:
                call_count += 1
                return (mock_client_socket, ('127.0.0.1', 12345))
            else:
                raise Exception("Stop the loop")

        mock_loop.sock_accept.side_effect = sock_accept_side_effect

        # Import run directly to avoid running the actual server
        from httpy.server import run

        # Call run (this will enter an infinite loop, but our side effect will break it)
        try:
            # Add a timeout to prevent hanging if the side effect doesn't work
            await asyncio.wait_for(run(host="localhost", port=8080), timeout=5.0)
            self.fail("run should have raised an exception but didn't")
        except asyncio.TimeoutError:
            self.fail("run timed out, indicating it might be stuck in a loop")
        except Exception as e:
            if str(e) != "Stop the loop":
                raise  # Re-raise if it's not our expected exception

        # Check that the socket was set up correctly
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket_instance.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_socket_instance.bind.assert_called_once_with(('localhost', 8080))
        mock_socket_instance.listen.assert_called_once_with(100)
        mock_socket_instance.setblocking.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
