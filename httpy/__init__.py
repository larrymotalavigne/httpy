"""
HTTPy - A simple HTTP server library for Python

This library provides a clean and intuitive interface for creating HTTP servers.
"""

from .request import Request as ServerRequest
from .response import Response as ServerResponse
from .routing import Route, get, post, put, delete, route
from .server import run
from .status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
)
from .websocket import (
    WebSocketConnection, WebSocketMessage, WebSocketOpCode, websocket
)
from .http2 import (
    HTTP2Connection, Frame, FrameType, FrameFlag, ErrorCode
)
from .http1 import handle_http1_connection
try:
    from .http3 import (
        HTTP3Protocol, HTTP3Server, run_http3_server, AIOQUIC_AVAILABLE
    )
except ImportError:
    AIOQUIC_AVAILABLE = False

__all__ = [
    # Server
    'ServerRequest', 'ServerResponse', 'Route',
    'get', 'post', 'put', 'delete', 'route', 'run',
    # HTTP Status Codes
    'HTTP_200_OK', 'HTTP_201_CREATED', 'HTTP_204_NO_CONTENT',
    'HTTP_400_BAD_REQUEST', 'HTTP_401_UNAUTHORIZED', 'HTTP_403_FORBIDDEN',
    'HTTP_404_NOT_FOUND', 'HTTP_405_METHOD_NOT_ALLOWED',
    'HTTP_422_UNPROCESSABLE_ENTITY', 'HTTP_500_INTERNAL_SERVER_ERROR',
    # WebSocket
    'WebSocketConnection', 'WebSocketMessage', 'WebSocketOpCode', 'websocket',
    # HTTP/1.1
    'handle_http1_connection',
    # HTTP/2.0
    'HTTP2Connection', 'Frame', 'FrameType', 'FrameFlag', 'ErrorCode',
]

# Add HTTP/3 exports if available
if AIOQUIC_AVAILABLE:
    __all__.extend([
        # HTTP/3
        'HTTP3Protocol', 'HTTP3Server', 'run_http3_server', 'AIOQUIC_AVAILABLE'
    ])
else:
    __all__.append('AIOQUIC_AVAILABLE')
