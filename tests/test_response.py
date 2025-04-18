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

from httpy import ServerResponse, HTTP_200_OK, HTTP_404_NOT_FOUND


class TestResponse(unittest.TestCase):
    """Tests for the Response class."""

    def test_init(self):
        """Test Response initialization."""
        response = ServerResponse(
            body="Hello, world!",
            status=HTTP_200_OK,
            headers={"Content-Type": "text/plain"}
        )

        self.assertEqual(response.body, "Hello, world!")
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "text/plain")

    def test_to_bytes(self):
        """Test converting response to bytes."""
        response = ServerResponse(
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
        response = ServerResponse.json(data)

        self.assertEqual(response.body, json.dumps(data, separators=(',', ':')))
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_text_response(self):
        """Test creating a text response."""
        text = "Hello, world!"
        response = ServerResponse.text(text)

        self.assertEqual(response.body, text)
        self.assertEqual(response.status, HTTP_200_OK)
        self.assertEqual(response.headers["Content-Type"], "text/plain")

    def test_custom_status(self):
        """Test response with custom status code."""
        response = ServerResponse.json(
            {"error": "Not Found"},
            status=HTTP_404_NOT_FOUND
        )

        self.assertEqual(response.status, HTTP_404_NOT_FOUND)
        bytes_response = response.to_bytes()
        text_response = bytes_response.decode('utf-8')
        self.assertIn("HTTP/1.1 404 Not Found", text_response)


if __name__ == "__main__":
    unittest.main()
