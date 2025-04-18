#!/usr/bin/env python3
"""
Unit tests for the HTTPy HTTP/3 functionality.
"""

import sys
import os
import unittest
import asyncio
import socket
import ssl
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Check if aioquic is available
try:
    import aioquic
    from httpy.http3 import (
        HTTP3Protocol, HTTP3Server, run_http3_server, AIOQUIC_AVAILABLE
    )
    SKIP_HTTP3_TESTS = not AIOQUIC_AVAILABLE
except ImportError:
    SKIP_HTTP3_TESTS = True

from httpy import ServerRequest, ServerResponse, get
from httpy.routing import ROUTES


@unittest.skipIf(SKIP_HTTP3_TESTS, "aioquic not available, skipping HTTP/3 tests")
class TestHTTP3(unittest.IsolatedAsyncioTestCase):
    """Tests for the HTTP/3 functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    @patch('aioquic.asyncio.serve')
    async def test_http3_server_start(self, mock_serve):
        """Test starting an HTTP/3 server."""
        # Create a temporary certificate and key
        cert_file = "temp_cert.pem"
        key_file = "temp_key.pem"
        
        try:
            # Create self-signed certificate and key
            self._create_self_signed_cert(cert_file, key_file)
            
            # Create an HTTP3Server
            server = HTTP3Server("localhost", 8443, cert_file, key_file)
            
            # Mock the serve function to return a server
            mock_server = MagicMock()
            mock_serve.return_value = mock_server
            
            # Start the server
            await server.start()
            
            # Check that serve was called with the correct arguments
            mock_serve.assert_called_once()
            args, kwargs = mock_serve.call_args
            
            # Check host and port
            self.assertEqual(args[0], "localhost")
            self.assertEqual(args[1], 8443)
            
            # Check configuration
            self.assertIn("configuration", kwargs)
            config = kwargs["configuration"]
            self.assertEqual(config.alpn_protocols, ["h3"])
            self.assertFalse(config.is_client)
            
            # Check create_protocol
            self.assertIn("create_protocol", kwargs)
            self.assertEqual(kwargs["create_protocol"], HTTP3Protocol)
            
            # Check that the server was stored
            self.assertEqual(server._server, mock_server)
            
        finally:
            # Clean up temporary files
            if os.path.exists(cert_file):
                os.remove(cert_file)
            if os.path.exists(key_file):
                os.remove(key_file)
    
    @patch('aioquic.asyncio.serve')
    async def test_run_http3_server(self, mock_serve):
        """Test running an HTTP/3 server."""
        # Create a temporary certificate and key
        cert_file = "temp_cert.pem"
        key_file = "temp_key.pem"
        
        try:
            # Create self-signed certificate and key
            self._create_self_signed_cert(cert_file, key_file)
            
            # Mock the serve function to return a server
            mock_server = MagicMock()
            mock_serve.return_value = mock_server
            
            # Run the HTTP/3 server
            server = await run_http3_server("localhost", 8443, cert_file, key_file)
            
            # Check that serve was called with the correct arguments
            mock_serve.assert_called_once()
            
            # Check that a server was returned
            self.assertIsNotNone(server)
            self.assertIsInstance(server, HTTP3Server)
            
        finally:
            # Clean up temporary files
            if os.path.exists(cert_file):
                os.remove(cert_file)
            if os.path.exists(key_file):
                os.remove(key_file)
    
    @patch('aioquic.h3.connection.H3Connection')
    async def test_http3_protocol_init(self, mock_h3_connection):
        """Test HTTP3Protocol initialization."""
        # Create a mock QuicConnection
        mock_quic = MagicMock()
        
        # Create an HTTP3Protocol
        protocol = HTTP3Protocol(mock_quic)
        
        # Check that the protocol was initialized correctly
        self.assertIsNone(protocol.h3)
        self.assertEqual(protocol.requests, {})
        self.assertEqual(protocol.request_waiter, {})
    
    def _create_self_signed_cert(self, cert_file, key_file):
        """Create a self-signed certificate and key for testing."""
        # This is a helper method to create a self-signed certificate
        # In a real test, we would use a library like cryptography
        # For this example, we'll just create empty files
        with open(cert_file, 'w') as f:
            f.write("-----BEGIN CERTIFICATE-----\nMIIDazCCAlOgAwIBAgIUJPPK7y9Xp/tVCEJSQyX9hCFciMwwDQYJKoZIhvcNAQEL\nBQAwRTELMAkGA1UEBhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoM\nGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDAeFw0yMzA1MTUxMjAwMDBaFw0yNDA1\nMTQxMjAwMDBaMEUxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEw\nHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEB\nAQUAA4IBDwAwggEKAoIBAQDK/FdDQAMiSyMvBwRfnGNcILYLkHRUGYSUiQMHIh1i\nYFYEYmVz+I1JHmJ2DfYvCVp6NGlU+Q5l5RUcJ+cuyDtP5GZMwfBIYVQgKG9EZh+L\nRUEQI+gZHZz8nCKLSFLHzUXygkQfgUg4Wm5Y5EZ0gqYuWqWqUUBxCLRVmPWoKk9o\nVXBxCYP1o/ToWrdc5hESZ4+vOKt4tSK3AoMUOv+nYuJBLKsV/PYVJWwNUOYGTRRJ\nD9nUDcTWjkxGvMnHjfLUkYe8/lbXMKILZlxnqjf8ORXgY3CQQZRj85EKAGDTt5Bj\nFxLKXEd+HOW1v9YQ5/A7YqGLlQUOdGP5/hHOjp7XAgMBAAGjUzBRMB0GA1UdDgQW\nBBQHWkV+oLWLmYYQ9hLgBPSBR7FRpDAfBgNVHSMEGDAWgBQHWkV+oLWLmYYQ9hLg\nBPSBR7FRpDAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQCgGCFd\nF49+95IKqIeGFmMwUBMZM3OLvlDzZGXoXIQC1cUi7BRxUQhNw2S0XGt+ybc3kh1b\n6IpTp7YxvV9JcYt1KIjGHlIVGpzEMXY+ahGKt/8LbpuLRGx6kcCK69m/3jKbq8lp\nZ3sYL5XNcoyRQV+Xpqc5X/J3/PqRMfB2ZzJW1RXl+GZY9UqXuBi9TVKQIFg0/BGV\nLUstEMaC3LLh/LUT8V6Y0h5N+dZnWGCJQWEgkxGsNtJlVnQj5Bh0TwOlk5f3pnQI\nCyVBcCQhQX41JXWLcvYiXzUQvnGsxdVAQB4zCUXGgqQVT7Jzr6DtjZ3eBYYCHEpT\n/ykP5ydAM1iFzFBg\n-----END CERTIFICATE-----")
        
        with open(key_file, 'w') as f:
            f.write("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDK/FdDQAMiSyMv\nBwRfnGNcILYLkHRUGYSUiQMHIh1iYFYEYmVz+I1JHmJ2DfYvCVp6NGlU+Q5l5RUc\nJ+cuyDtP5GZMwfBIYVQgKG9EZh+LRUEQI+gZHZz8nCKLSFLHzUXygkQfgUg4Wm5Y\n5EZ0gqYuWqWqUUBxCLRVmPWoKk9oVXBxCYP1o/ToWrdc5hESZ4+vOKt4tSK3AoMU\nOv+nYuJBLKsV/PYVJWwNUOYGTRRJD9nUDcTWjkxGvMnHjfLUkYe8/lbXMKILZlxn\nqjf8ORXgY3CQQZRj85EKAGDTt5BjFxLKXEd+HOW1v9YQ5/A7YqGLlQUOdGP5/hHO\njp7XAgMBAAECggEABEI1P6nf6Zs7mJlyBDv+Pfl5nS4wJPvcs9QgYZf3/S6STTg2\nYxJCdnUfswxTkPmRLWkUE4ATmxvn7zcFJ/XCaQXyKXLxJlyf5xRPfXMCwXLzvEMK\nGBaR0nWn3KJzD4ztK9a1AuHF7X2eKQQ9QiUUPgLDjkJxKVUa7PZ3xLRVQJvSbkzx\nLVwZ7xm6OepNIJzU3TQiPCbhUJjYTvBHJPo1JuTNrYoJAGeQDrH/ssLyp+PYuiJK\nGBkLbifHwXh1bRQgII4zvG6iTKGCyBpJrBNk3ZzZcePqiKdKAzqCRGJi1vWJI8B8\nS5UrtyDy9Eu/mIrRLobJk9hZ1Exh+8xQGNejAQKBgQDlvMwV06bdbFid5BwgQVnF\nAJgCQ8DYN9sHE1LHZhpJ8UZcO4xVKQFLBG2Ib5nkLEFUDSyYgwLKzGYcSWt1KE9m\nQpkxdGt4uZnz+HdgKBNBXcpyC7MxvOAK+Qpzwp8hk2HmZm4i5tZq9xf7EQRdNYqq\n7xyKyuXpBQXs9jKe4F7BwQKBgQDh+usYTOIQCwyI6vEBBYwkzyzCXXbwZTLNzHd3\nG60yVIrRJ8kCmGQtsKfO6/Q5BW1w/pA5mn9vBiEYzw6+1G8QXKZzRp+oNtXuSYmk\nXnmPy5qj01HkeEqcbIRGGQZxbk3+MO7G+LRjkrwGy1vS4lymCuQvdDUmHRH7FJtt\nMJnX1wKBgC0JMsESQ6YcDsRpnWiKk6dkfzCHgBnZ3KWR6eGMtNyXKA3jaCwBL+Yx\nXY5Etc39XJNz7RfFZ8YQjQrWAHRWSxdWkE0OYLQfc3KO6hjLX3MsEYBr7MBb5HLQ\nMuDCuv9Nl9cVJFB3X9IkDOSMrELpRyALNzjYE2H3WLuYfwRsl4jBAoGAG2PT+pgn\nDYPxJZYYKn93RaIxL8TtYXQH8XXD5Vn5bL/x9sGcV5zcsYhvsRlDFWFVJqOCBsOY\nHzoqIBPUZkfLKLJYSizDjGsvz2wC5PRk/TQ1+CvNFnlQfQMm2ZfxsLY9X1J3zWYL\nVX9j1oUYkNQXjQYQmZALbDwXbVVIuUJe+okCgYEAyoUOWy6opGf5H6M8ON3uLF5c\nWBUUHkqOyrCo59QRvlm/YADsXEoE2CqLGHXOB5HYY/7U/qGcQgKvRKnTuNJ3N96K\nstRKXjCCi/ckXiMjcM8gVQT5rRU9MOlTjC4jxYg7faeH3/I5MmIW1+GTCJW8+Z5H\nIPJFEAhz3NNPDE9tLzI=\n-----END PRIVATE KEY-----")


if __name__ == "__main__":
    unittest.main()