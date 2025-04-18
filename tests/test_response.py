#!/usr/bin/env python3
"""
Unit tests for the httpy Response class.
"""

import sys
import os
import json
import unittest

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Response, HTTP_200_OK, HTTP_404_NOT_FOUND


class TestResponse(unittest.TestCase):
    """Tests for the Response class."""

    def test_init(self):
        """Test Response initialization."""
        response = Response(
            body="Hello, world!",
            status=HTTP_200_OK,
            headers={"Content-Type": "text/plain"}
        )

        self.assertEqual(response.body, "Hello, world!")
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "text/plain")

    def test_to_bytes(self):
        """Test converting response to bytes."""
        response = Response(
            body="Hello, world!",
            status=HTTP_200_OK,
            headers={"Content-Type": "text/plain"}
        )

        bytes_response = response.to_bytes()
        self.assertIsInstance(bytes_response, bytes)

        # Check that the response contains the expected parts
        text_response = bytes_response.decode('utf-8')
        self.assertIn("HTTP/1.1 200 OK", text_response)
        self.assertIn("Content-Type: text/plain", text_response)
        self.assertIn("Content-Length: 13", text_response)
        self.assertIn("Hello, world!", text_response)

    def test_json_response(self):
        """Test creating a JSON response."""
        data = {"name":"Test User","id":123}
        response = Response.json(data)

        self.assertEqual(response.body, json.dumps(data, separators=(',', ':')))
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_text_response(self):
        """Test creating a text response."""
        text = "Hello, world!"
        response = Response.text(text)

        self.assertEqual(response.body, text)
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "text/plain")

    def test_custom_status(self):
        """Test response with custom status code."""
        response = Response.json(
            {"error": "Not Found"},
            status=HTTP_404_NOT_FOUND
        )

        self.assertEqual(response.status, HTTP_404_NOT_FOUND)
        bytes_response = response.to_bytes()
        text_response = bytes_response.decode('utf-8')
        self.assertIn("HTTP/1.1 404 Not Found", text_response)

    def test_binary_response(self):
        """Test creating a binary response."""
        # Create binary data
        binary_data = b'\x00\x01\x02\x03\x04\xFF\xFE\xFD\xFC\xFB'

        # Create binary response
        response = Response.binary(binary_data)

        # Check response properties
        self.assertEqual(response.body, binary_data)
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "application/octet-stream")

        # Check that the binary data is preserved in to_bytes()
        bytes_response = response.to_bytes()
        self.assertIsInstance(bytes_response, bytes)

        # The response should contain the binary data
        self.assertIn(binary_data, bytes_response)

    def test_response_with_binary_body(self):
        """Test response with binary body."""
        # Create binary data
        binary_data = b'\x00\x01\x02\x03\x04\xFF\xFE\xFD\xFC\xFB'

        # Create response with binary body directly
        response = Response(
            body=binary_data,
            status=HTTP_200_OK,
            headers={"Content-Type": "application/octet-stream"}
        )

        # Check that the body is stored correctly
        self.assertEqual(response.body, binary_data)

        # Check that _encoded_body is set correctly
        self.assertEqual(response._encoded_body, binary_data)

        # Check that the binary data is preserved in to_bytes()
        bytes_response = response.to_bytes()
        self.assertIn(binary_data, bytes_response)


if __name__ == "__main__":
    unittest.main()
