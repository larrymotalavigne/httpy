#!/usr/bin/env python3
"""
Unit tests for the HTTPy routing functionality.
"""

import sys
import os
import unittest
import asyncio
from unittest.mock import AsyncMock

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import ServerRequest, ServerResponse, Route, get, post, put, delete, route
from httpy.routing import ROUTES


class TestRoute(unittest.TestCase):
    """Tests for the Route class."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()

    def test_route_init(self):
        """Test Route initialization."""
        async def handler(req):
            return ServerResponse.text("Test")

        route_obj = Route("GET", "/api/users/{id}", handler)

        self.assertEqual(route_obj.method, "GET")
        self.assertEqual(route_obj.handler, handler)
        # Check that the regex and param_names were created
        self.assertTrue(hasattr(route_obj, 'regex'))
        self.assertTrue(hasattr(route_obj, 'param_names'))
        self.assertEqual(route_obj.param_names, ['id'])

    def test_route_match(self):
        """Test route matching."""
        async def handler(req):
            return ServerResponse.text("Test")

        route_obj = Route("GET", "/api/users/{id}", handler)

        # Test matching path
        params = route_obj.match("GET", "/api/users/123")
        self.assertEqual(params, {'id': '123'})

        # Test non-matching method
        params = route_obj.match("POST", "/api/users/123")
        self.assertIsNone(params)

        # Test non-matching path
        params = route_obj.match("GET", "/api/products/123")
        self.assertIsNone(params)

    def test_route_decorator(self):
        """Test route decorator."""
        @route("GET", "/test")
        async def test_handler(req):
            return ServerResponse.text("Test")

        self.assertEqual(len(ROUTES), 1)
        self.assertEqual(ROUTES[0].method, "GET")
        self.assertEqual(ROUTES[0].handler, test_handler)

    def test_method_decorators(self):
        """Test HTTP method decorators."""
        @get("/get")
        async def get_handler(req):
            return ServerResponse.text("GET")

        @post("/post")
        async def post_handler(req):
            return ServerResponse.text("POST")

        @put("/put")
        async def put_handler(req):
            return ServerResponse.text("PUT")

        @delete("/delete")
        async def delete_handler(req):
            return ServerResponse.text("DELETE")

        self.assertEqual(len(ROUTES), 4)

        methods = [r.method for r in ROUTES]
        self.assertIn("GET", methods)
        self.assertIn("POST", methods)
        self.assertIn("PUT", methods)
        self.assertIn("DELETE", methods)


if __name__ == "__main__":
    unittest.main()
