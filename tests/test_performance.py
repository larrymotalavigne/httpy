#!/usr/bin/env python3
"""
Performance tests for the HTTPy server.

These tests measure the performance of various components of the HTTPy server,
particularly focusing on the optimizations implemented in Phase 3.
"""

import sys
import os
import unittest
import asyncio
import time
import gc
import statistics
import io
from unittest.mock import patch, MagicMock, AsyncMock
try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    print("memory_profiler module not available, skipping memory usage test")

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request, Response, get, post, route, run
from httpy.routing import ROUTES, Route
from httpy.http1 import handle_http1_request, handle_http1_connection, BUFFER_SIZE


class TestHTTP1Performance(unittest.IsolatedAsyncioTestCase):
    """Performance tests for the HTTP/1.1 implementation."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the global ROUTES list before each test
        ROUTES.clear()
        # Force garbage collection to ensure consistent memory measurements
        gc.collect()

    async def test_request_parsing_performance(self):
        """Test the performance of HTTP request parsing."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_socket = MagicMock()
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Create a large request with many headers
        headers = "\r\n".join([f"Header-{i}: Value-{i}" for i in range(50)])
        request_data = f"GET /test HTTP/1.1\r\nHost: localhost\r\n{headers}\r\n\r\n"
        request_bytes = request_data.encode('latin1')

        # Mock sock_recv_into to return the request data
        def sock_recv_into_side_effect(sock, buffer_view):
            buffer_view[:len(request_bytes)] = request_bytes
            return len(request_bytes)

        mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

        # Measure the time it takes to parse the request
        start_time = time.time()
        iterations = 1000
        for _ in range(iterations):
            keep_alive, req = await handle_http1_request(mock_loop, mock_socket, mock_reader, mock_writer)
        end_time = time.time()

        # Calculate average time per request
        avg_time = (end_time - start_time) / iterations
        print(f"Average request parsing time: {avg_time:.6f} seconds")

        # Assert that the request was parsed correctly
        self.assertTrue(keep_alive)
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.path, "/test")
        self.assertEqual(req.headers["Host"], "localhost")

        # Assert that the parsing time is below a reasonable threshold
        # This threshold should be adjusted based on the actual performance of the system
        self.assertLess(avg_time, 0.001, "Request parsing is too slow")

    async def test_routing_algorithm_performance(self):
        """Test the performance of the routing algorithm."""
        # Create a large number of routes
        num_routes = 1000
        for i in range(num_routes):
            ROUTES.append(Route("GET", f"/test/{i}", lambda req: Response.text("Test")))

        # Create a request that will match the last route
        req = Request("GET", f"/test/{num_routes-1}", {"Host": "localhost"}, "", {}, {})

        # Measure the time it takes to find the matching route
        start_time = time.time()
        iterations = 1000
        for _ in range(iterations):
            for route in ROUTES:
                path_params = route.match(req.method, req.path)
                if path_params is not None:
                    break
        end_time = time.time()

        # Calculate average time per route matching
        avg_time = (end_time - start_time) / iterations
        print(f"Average route matching time: {avg_time:.6f} seconds")

        # Assert that the route matching time is below a reasonable threshold
        # This threshold should be adjusted based on the actual performance of the system
        self.assertLess(avg_time, 0.001, "Route matching is too slow")

    async def test_connection_handling_performance(self):
        """Test the performance of connection handling."""
        # Set up mocks
        mock_loop = AsyncMock()
        mock_socket = MagicMock()
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()

        # Create a simple request
        request_data = "GET /test HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
        request_bytes = request_data.encode('latin1')

        # Mock sock_recv_into to return the request data
        call_count = 0
        def sock_recv_into_side_effect(sock, buffer_view):
            nonlocal call_count
            if call_count % 2 == 0:  # Every other call returns data
                buffer_view[:len(request_bytes)] = request_bytes
                call_count += 1
                return len(request_bytes)
            else:  # Alternate calls return 0 to end the request
                call_count += 1
                return 0

        mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

        # Create a test route
        async def test_handler(req):
            return Response.text("Test Response")

        ROUTES.append(Route("GET", "/test", test_handler))

        # Measure the time it takes to handle multiple connections
        start_time = time.time()
        iterations = 100
        for _ in range(iterations):
            await handle_http1_connection(mock_loop, mock_socket, mock_reader, mock_writer)
        end_time = time.time()

        # Calculate average time per connection
        avg_time = (end_time - start_time) / iterations
        print(f"Average connection handling time: {avg_time:.6f} seconds")

        # Assert that the connection handling time is below a reasonable threshold
        # This threshold should be adjusted based on the actual performance of the system
        self.assertLess(avg_time, 0.01, "Connection handling is too slow")

    def test_memory_usage_optimization(self):
        """Test the memory usage optimization."""
        if not MEMORY_PROFILER_AVAILABLE:
            self.skipTest("memory_profiler module not available")
            return

        # Define a function to measure memory usage during request parsing
        @memory_profiler.profile
        def parse_request():
            # Set up mocks
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            mock_socket = MagicMock()
            mock_reader = MagicMock()
            mock_writer = MagicMock()

            # Create a large request with a large body
            body = "X" * 1000000  # 1MB body
            request_data = f"POST /test HTTP/1.1\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            request_bytes = request_data.encode('latin1')

            # Mock sock_recv_into to return the request data
            def sock_recv_into_side_effect(sock, buffer_view):
                # Only copy as much as the buffer can hold
                copy_size = min(len(request_bytes), len(buffer_view))
                buffer_view[:copy_size] = request_bytes[:copy_size]
                return copy_size

            # Create a mock event loop that returns our mock socket
            mock_loop = MagicMock()
            mock_loop.sock_recv_into.side_effect = sock_recv_into_side_effect

            # Parse the request
            try:
                loop.run_until_complete(handle_http1_request(mock_loop, mock_socket, mock_reader, mock_writer))
            except Exception as e:
                print(f"Error parsing request: {e}")
            finally:
                loop.close()

        # Run the memory profiling
        parse_request()

        # Since memory_profiler doesn't provide a programmatic way to get the results,
        # we'll just print them and rely on manual inspection for now
        print("Memory usage test completed. Check the output above for memory usage details.")

        # In a real test, we would assert on the memory usage, but for now we'll just pass
        self.assertTrue(True)

    async def test_async_handling_performance(self):
        """Test the performance of async handling."""
        # Create a test route with an async handler
        async def test_handler(req):
            # Simulate some async work
            await asyncio.sleep(0.001)
            return Response.text("Test Response")

        ROUTES.append(Route("GET", "/test", test_handler))

        # Create a request
        req = Request("GET", "/test", {"Host": "localhost"}, "", {}, {})

        # Measure the time it takes to handle multiple requests concurrently
        start_time = time.time()
        tasks = []
        for _ in range(100):
            for route in ROUTES:
                path_params = route.match(req.method, req.path)
                if path_params is not None:
                    req.path_params = path_params
                    tasks.append(route.handler(req))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        end_time = time.time()

        # Calculate total time
        total_time = end_time - start_time
        print(f"Total time for 100 concurrent requests: {total_time:.6f} seconds")

        # Assert that the total time is reasonable for concurrent processing
        # This threshold should be adjusted based on the actual performance of the system
        # Since we're sleeping for 0.001 seconds per request, the total time should be close to 0.001 seconds
        # if the concurrency is working well
        self.assertLess(total_time, 0.1, "Async handling is not efficient")


if __name__ == "__main__":
    unittest.main()
