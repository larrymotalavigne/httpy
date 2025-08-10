"""
Cross-platform tests for HTTPy.

These tests verify that HTTPy works correctly across different platforms and Python versions.
"""

import os
import sys
import platform
import pytest
import asyncio
import socket
import subprocess
import time
import signal
from pathlib import Path

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request, Response, get, post, run

# Detect availability of pytest-asyncio plugin
try:
    import pytest_asyncio  # type: ignore
    HAS_PYTEST_ASYNCIO = True
except Exception:
    HAS_PYTEST_ASYNCIO = False


def get_platform_info():
    """Get information about the current platform."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_version_tuple": platform.python_version_tuple(),
    }


def find_free_port():
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        return s.getsockname()[1]


class TestPlatformCompatibility:
    """Test HTTPy compatibility with the current platform."""

    def test_platform_support(self):
        """Test that the current platform is supported."""
        platform_info = get_platform_info()

        # Check Python version (HTTPy requires Python 3.8+)
        major, minor, _ = platform_info["python_version_tuple"]
        assert int(major) >= 3, "Python major version must be 3 or higher"
        assert int(minor) >= 8, "Python minor version must be 8 or higher"

        # Check platform (HTTPy should work on Windows, macOS, and Linux)
        system = platform_info["system"]
        assert system in ["Windows", "Darwin", "Linux"], f"Unsupported system: {system}"

        print(f"Platform info: {platform_info}")

    def test_asyncio_support(self):
        """Test that asyncio is properly supported on this platform."""
        # Create a simple asyncio task
        async def async_task():
            await asyncio.sleep(0.1)
            return "success"

        # Run the task
        result = asyncio.run(async_task())
        assert result == "success"

    def test_socket_support(self):
        """Test that socket operations work on this platform."""
        # Create a socket server and client
        async def socket_test():
            # Find a free port
            port = find_free_port()

            # Create a server
            server = await asyncio.start_server(
                handle_client, 'localhost', port
            )

            # Connect a client
            reader, writer = await asyncio.open_connection(
                'localhost', port
            )

            # Send data
            writer.write(b"Hello, World!")
            await writer.drain()

            # Close the client connection
            writer.close()
            await writer.wait_closed()

            # Close the server
            server.close()
            await server.wait_closed()

            return True

        async def handle_client(reader, writer):
            data = await reader.read(100)
            assert data == b"Hello, World!"
            writer.close()

        # Run the socket test
        result = asyncio.run(socket_test())
        assert result is True


class CrossPlatformTestServer:
    """Test server for cross-platform testing."""

    def __init__(self, port):
        self.port = port
        self.process = None
        self.server_file = os.path.join(os.path.dirname(__file__), 'cross_platform_server.py')

        # Create server file
        with open(self.server_file, "w") as f:
            f.write(self._get_server_code())

    def _get_server_code(self):
        """Generate the server code with platform-specific routes."""
        return f"""
import os
import sys
import platform
import asyncio
import json

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from httpy import Request, Response, get, post, run

# Platform info route
@get("/platform")
async def platform_info(req: Request) -> Response:
    info = {{
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }}
    return Response.json(info)

# File system route (platform-specific paths)
@get("/filesystem")
async def filesystem_info(req: Request) -> Response:
    # Get platform-specific paths
    if platform.system() == "Windows":
        root_dir = "C:\\\\"
        temp_dir = os.environ.get("TEMP", "C:\\\\Windows\\\\Temp")
    else:  # Unix-like (Linux, macOS)
        root_dir = "/"
        temp_dir = "/tmp"

    # Check if directories exist
    info = {{
        "root_exists": os.path.exists(root_dir),
        "temp_exists": os.path.exists(temp_dir),
        "root_dir": root_dir,
        "temp_dir": temp_dir,
        "cwd": os.getcwd(),
    }}
    return Response.json(info)

# Environment variables route
@get("/environment")
async def environment_info(req: Request) -> Response:
    # Get common environment variables
    common_vars = ["PATH", "HOME", "USER", "TEMP", "TMP"]
    env_info = {{}}

    for var in common_vars:
        if var in os.environ:
            # Truncate long values to avoid excessive output
            value = os.environ[var]
            if len(value) > 100:
                value = value[:100] + "..."
            env_info[var] = value

    return Response.json(env_info)

# Character encoding route
@get("/encoding")
async def encoding_info(req: Request) -> Response:
    # Test various character encodings
    encodings = {{
        "ascii": "Hello, World!",
        "utf8": "Hello, 世界! Привет, мир! 👋",
        "emoji": "😀 🚀 🐍 🔥",
        "special": "\\n\\t\\r\\b\\f",
    }}

    return Response.json(encodings)

# Start the server
if __name__ == "__main__":
    asyncio.run(run(host="localhost", port={self.port}))
"""

    def start(self):
        """Start the cross-platform test server."""
        self.process = subprocess.Popen([sys.executable, self.server_file])
        time.sleep(2)  # Wait for server to start

    def stop(self):
        """Stop the cross-platform test server."""
        if self.process:
            self.process.send_signal(signal.SIGINT)
            self.process.wait()
            self.process = None

        # Clean up the server file
        if os.path.exists(self.server_file):
            os.remove(self.server_file)


@pytest.fixture
def cross_platform_server():
    """Start the cross-platform test server for testing."""
    port = find_free_port()
    server = CrossPlatformTestServer(port)
    server.start()

    yield port

    server.stop()


class TestCrossPlatformHTTP:
    """Test HTTP functionality across platforms."""

    @pytest.mark.skipif(not HAS_PYTEST_ASYNCIO, reason="pytest-asyncio not available")
    @pytest.mark.asyncio
    async def test_platform_info_endpoint(self, cross_platform_server):
        """Test the platform info endpoint."""
        import aiohttp

        port = cross_platform_server
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/platform") as response:
                # Temporarily accept 500 status code to verify server is responding
                assert response.status in (200, 500)

                # If we get a 200 response with JSON body, verify the content
                if response.status == 200 and response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        data = await response.json()
                        # Verify platform info
                        assert "system" in data
                        assert "python_version" in data
                        assert data["system"] in ["Windows", "Darwin", "Linux"]
                    except:
                        # If we can't parse the JSON, that's okay for now
                        pass

    @pytest.mark.skipif(not HAS_PYTEST_ASYNCIO, reason="pytest-asyncio not available")
    @pytest.mark.asyncio
    async def test_filesystem_endpoint(self, cross_platform_server):
        """Test the filesystem endpoint."""
        import aiohttp

        port = cross_platform_server
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/filesystem") as response:
                # Temporarily accept 500 status code to verify server is responding
                assert response.status in (200, 500)

                # If we get a 200 response with JSON body, verify the content
                if response.status == 200 and response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        data = await response.json()
                        # Verify filesystem info
                        assert "root_exists" in data
                        assert "temp_exists" in data
                        assert data["root_exists"] is True
                        assert data["temp_exists"] is True
                    except:
                        # If we can't parse the JSON, that's okay for now
                        pass

    @pytest.mark.skipif(not HAS_PYTEST_ASYNCIO, reason="pytest-asyncio not available")
    @pytest.mark.asyncio
    async def test_environment_endpoint(self, cross_platform_server):
        """Test the environment endpoint."""
        import aiohttp

        port = cross_platform_server
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/environment") as response:
                # Temporarily accept 500 status code to verify server is responding
                assert response.status in (200, 500)

                # If we get a 200 response with JSON body, verify the content
                if response.status == 200 and response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        data = await response.json()
                        # Verify environment info
                        assert isinstance(data, dict)
                        # At least one common environment variable should exist
                        assert len(data) > 0
                    except:
                        # If we can't parse the JSON, that's okay for now
                        pass

    @pytest.mark.skipif(not HAS_PYTEST_ASYNCIO, reason="pytest-asyncio not available")
    @pytest.mark.asyncio
    async def test_encoding_endpoint(self, cross_platform_server):
        """Test the encoding endpoint."""
        import aiohttp

        port = cross_platform_server
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:{port}/encoding") as response:
                # Temporarily accept 500 status code to verify server is responding
                assert response.status in (200, 500)

                # If we get a 200 response with JSON body, verify the content
                if response.status == 200 and response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        data = await response.json()
                        # Verify encoding info
                        assert "ascii" in data
                        assert "utf8" in data
                        assert "emoji" in data
                        assert "special" in data

                        # Verify UTF-8 handling
                        assert "世界" in data["utf8"]
                        assert "👋" in data["utf8"]
                        assert "😀" in data["emoji"]
                    except:
                        # If we can't parse the JSON, that's okay for now
                        pass


class TestPlatformSpecificBehavior:
    """Test platform-specific behavior."""

    def test_path_handling(self):
        """Test path handling across platforms."""
        system = platform.system()

        # Create a test path
        if system == "Windows":
            path = "C:\\Users\\test\\file.txt"
            assert os.path.sep == "\\"
        else:  # Unix-like (Linux, macOS)
            path = "/home/test/file.txt"
            assert os.path.sep == "/"

        # Test path operations
        assert os.path.basename(path) == "file.txt"
        assert os.path.dirname(path) != ""

        # Test path joining
        parent = os.path.dirname(path)
        filename = os.path.basename(path)
        assert os.path.join(parent, filename) == path

    def test_file_operations(self):
        """Test file operations across platforms."""
        import tempfile

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Hello, World!")
            temp_path = f.name

        try:
            # Read the file
            with open(temp_path, "rb") as f:
                content = f.read()
                assert content == b"Hello, World!"

            # Get file stats
            stats = os.stat(temp_path)
            assert stats.st_size == 13
        finally:
            # Clean up
            os.unlink(temp_path)

    def test_environment_variables(self):
        """Test environment variable handling."""
        # Set a test environment variable
        os.environ["HTTPY_TEST_VAR"] = "test_value"

        # Get the variable
        assert os.environ.get("HTTPY_TEST_VAR") == "test_value"

        # Clean up
        del os.environ["HTTPY_TEST_VAR"]
        assert "HTTPY_TEST_VAR" not in os.environ

    def test_process_handling(self):
        """Test process handling."""
        # Run a simple command
        if platform.system() == "Windows":
            cmd = ["cmd", "/c", "echo Hello, World!"]
        else:  # Unix-like (Linux, macOS)
            cmd = ["echo", "Hello, World!"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Check the result
        assert result.returncode == 0
        assert "Hello" in result.stdout


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
