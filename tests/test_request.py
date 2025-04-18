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

from httpy import ServerRequest


class TestRequest(unittest.TestCase):
    """Tests for the Request class."""

    def test_init(self):
        """Test Request initialization."""
        request = ServerRequest(
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
        
        request = ServerRequest(
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            body=json_body,
            path_params={}
        )
        
        parsed_data = request.json()
        self.assertEqual(parsed_data, data)
        
        # Invalid JSON
        request = ServerRequest(
            method="POST",
            path="/api/users",
            headers={"Content-Type": "application/json"},
            body="This is not JSON",
            path_params={}
        )
        
        parsed_data = request.json()
        self.assertIsNone(parsed_data)


if __name__ == "__main__":
    unittest.main()