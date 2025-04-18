#!/usr/bin/env python3
"""
Unit tests for the httpy Request class.
"""

import sys
import os
import json
import unittest

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request


class TestRequest(unittest.TestCase):
    """Tests for the Request class."""

    def test_init(self):
        """Test Request initialization."""
        request = Request(
            method="GET",
            path="/api/users/123",
            headers={"Content-Type": "application/json"},
            body="",
            path_params={"id": "123"}
        )

        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, "/api/users/123")
        self.assertEqual(request.headers["Content-Type"], "application/json")
        self.assertEqual(request.body, "")
        self.assertEqual(request.path_params["id"], "123")

    def test_json_parsing(self):
        """Test parsing JSON request body."""
        # Valid JSON
        data = {"name": "Test User", "email": "test@example.com"}
        json_body = json.dumps(data)

        request = Request(
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            body=json_body,
            path_params={}
        )

        parsed_data = request.json()
        self.assertEqual(parsed_data, data)

        # Invalid JSON
        request = Request(
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            body="This is not JSON",
            path_params={}
        )

        parsed_data = request.json()
        self.assertIsNone(parsed_data)

    def test_binary_body(self):
        """Test handling binary data in request body."""
        # Create binary data
        binary_data = b'\x00\x01\x02\x03\x04\xFF\xFE\xFD\xFC\xFB'

        # Create request with binary body
        request = Request(
            method="POST",
            path="/api/upload",
            headers={"Content-Type": "application/octet-stream"},
            body=binary_data,
            path_params={}
        )

        # Check that the body is stored correctly
        self.assertEqual(request.body, binary_data)
        self.assertEqual(request._body_bytes, binary_data)

        # Test JSON parsing with binary data
        parsed_data = request.json()
        self.assertIsNone(parsed_data)  # Should return None for non-JSON binary data


if __name__ == "__main__":
    unittest.main()
