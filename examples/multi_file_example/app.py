#!/usr/bin/env python3
"""
Main application file for the multi-file example.

This file imports all the routes and runs the server.
"""

import os
import sys
import asyncio
import ssl
import time

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from httpy import (
    Response, Request, get, post, run,
    HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST
)

# Import all routes
from routes import api, pages, websockets

# Create a directory for file uploads if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Create a directory for static files if it doesn't exist
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

# Create a sample static file if it doesn't exist
SAMPLE_CSS = os.path.join(STATIC_DIR, 'style.css')
if not os.path.exists(SAMPLE_CSS):
    with open(SAMPLE_CSS, 'w') as f:
        f.write("""
/* Sample CSS file */
body {
    font-family: Arial, sans-serif;
    margin: 40px;
    line-height: 1.6;
}
h1 {
    color: #333;
}
.nav {
    margin-bottom: 20px;
}
.nav a {
    margin-right: 15px;
    color: #0066cc;
    text-decoration: none;
}
.nav a:hover {
    text-decoration: underline;
}
.content {
    background: #f9f9f9;
    padding: 20px;
    border-radius: 5px;
}
""")

# Create a sample static HTML file if it doesn't exist
SAMPLE_HTML = os.path.join(STATIC_DIR, 'sample.html')
if not os.path.exists(SAMPLE_HTML):
    with open(SAMPLE_HTML, 'w') as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Static File Example</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <h1>Static File Example</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/users">Users</a>
        <a href="/chat">Chat</a>
    </div>
    <div class="content">
        <p>This is a static HTML file served by HTTPy.</p>
        <p>It demonstrates serving static files from a directory.</p>
    </div>
</body>
</html>
""")

# Create a sample image file if it doesn't exist
SAMPLE_IMAGE = os.path.join(STATIC_DIR, 'logo.svg')
if not os.path.exists(SAMPLE_IMAGE):
    with open(SAMPLE_IMAGE, 'w') as f:
        f.write("""
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
  <rect width="100" height="100" fill="#0066cc" />
  <text x="50" y="50" font-family="Arial" font-size="20" text-anchor="middle" fill="white" dominant-baseline="middle">
    HTTPy
  </text>
</svg>
""")

# File upload/download routes

@post("/upload")
async def upload_file(req: Request) -> Response:
    """Handle file uploads."""
    # Check if the request has multipart form data
    if not req.is_multipart():
        return Response.json({"error": "Multipart form data required"}, status=HTTP_400_BAD_REQUEST)
    
    # Get the uploaded file
    form_data = await req.form()
    if "file" not in form_data:
        return Response.json({"error": "No file uploaded"}, status=HTTP_400_BAD_REQUEST)
    
    file = form_data["file"]
    
    # Save the file
    filename = os.path.basename(file.filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    return Response.json({
        "success": True,
        "filename": filename,
        "size": os.path.getsize(file_path),
        "download_url": f"/download/{filename}"
    })

@get("/download/{filename}")
async def download_file(req: Request) -> Response:
    """Handle file downloads."""
    filename = req.path_params.get('filename', '')
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        return Response.json({"error": "File not found"}, status=HTTP_404_NOT_FOUND)
    
    # Read the file
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    content_type = "application/octet-stream"
    if filename.endswith(".txt"):
        content_type = "text/plain"
    elif filename.endswith(".html") or filename.endswith(".htm"):
        content_type = "text/html"
    elif filename.endswith(".css"):
        content_type = "text/css"
    elif filename.endswith(".js"):
        content_type = "application/javascript"
    elif filename.endswith(".json"):
        content_type = "application/json"
    elif filename.endswith(".png"):
        content_type = "image/png"
    elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif filename.endswith(".gif"):
        content_type = "image/gif"
    elif filename.endswith(".svg"):
        content_type = "image/svg+xml"
    elif filename.endswith(".pdf"):
        content_type = "application/pdf"
    
    # Create response with appropriate headers
    headers = {
        "Content-Disposition": f"attachment; filename=\"{filename}\"",
        "Content-Type": content_type,
        "Content-Length": str(len(content))
    }
    
    return Response(content, headers=headers)

@get("/upload-form")
async def upload_form(req: Request) -> Response:
    """Render a file upload form."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Upload - HTTPy Multi-File Example</title>
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
        <h1>File Upload</h1>
        <div class="nav">
            <a href="/">Home</a>
            <a href="/about">About</a>
            <a href="/users">Users</a>
            <a href="/chat">Chat</a>
        </div>
        <div class="content">
            <p>Upload a file to the server:</p>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit">Upload</button>
            </form>
            
            <div id="result" style="margin-top: 20px;"></div>
            
            <script>
                document.querySelector('form').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    try {
                        const response = await fetch('/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            document.getElementById('result').innerHTML = `
                                <div style="background-color: #dff0d8; padding: 10px; border-radius: 5px;">
                                    <p>File uploaded successfully!</p>
                                    <p>Filename: ${result.filename}</p>
                                    <p>Size: ${result.size} bytes</p>
                                    <p><a href="${result.download_url}" target="_blank">Download File</a></p>
                                </div>
                            `;
                        } else {
                            document.getElementById('result').innerHTML = `
                                <div style="background-color: #f2dede; padding: 10px; border-radius: 5px;">
                                    <p>Error: ${result.error}</p>
                                </div>
                            `;
                        }
                    } catch (error) {
                        document.getElementById('result').innerHTML = `
                            <div style="background-color: #f2dede; padding: 10px; border-radius: 5px;">
                                <p>Error: ${error.message}</p>
                            </div>
                        `;
                    }
                });
            </script>
        </div>
    </body>
    </html>
    """
    return Response.html(html)

# Static file serving

@get("/static/{path:path}")
async def serve_static(req: Request) -> Response:
    """Serve static files."""
    path = req.path_params.get('path', '')
    file_path = os.path.join(STATIC_DIR, path)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return Response.json({"error": "File not found"}, status=HTTP_404_NOT_FOUND)
    
    # Read the file
    with open(file_path, "rb") as f:
        content = f.read()
    
    # Determine content type
    content_type = "application/octet-stream"
    if path.endswith(".txt"):
        content_type = "text/plain"
    elif path.endswith(".html") or path.endswith(".htm"):
        content_type = "text/html"
    elif path.endswith(".css"):
        content_type = "text/css"
    elif path.endswith(".js"):
        content_type = "application/javascript"
    elif path.endswith(".json"):
        content_type = "application/json"
    elif path.endswith(".png"):
        content_type = "image/png"
    elif path.endswith(".jpg") or path.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif path.endswith(".gif"):
        content_type = "image/gif"
    elif path.endswith(".svg"):
        content_type = "image/svg+xml"
    elif path.endswith(".pdf"):
        content_type = "application/pdf"
    
    # Create response with appropriate headers
    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(content))
    }
    
    return Response(content, headers=headers)

if __name__ == "__main__":
    print("Starting HTTPy Multi-File Example")
    print("Press Ctrl+C to stop the server")
    print("\nTry these endpoints:")
    print("  - http://localhost:8080/")
    print("  - http://localhost:8080/about")
    print("  - http://localhost:8080/users")
    print("  - http://localhost:8080/chat")
    print("  - http://localhost:8080/api/users")
    print("  - http://localhost:8080/api/users/1")
    print("  - http://localhost:8080/upload-form")
    print("  - http://localhost:8080/static/sample.html")
    print("  - http://localhost:8080/static/style.css")
    print("  - http://localhost:8080/static/logo.svg")
    print("  - WebSocket connection to ws://localhost:8080/ws/chat")
    print("  - WebSocket connection to ws://localhost:8080/ws/chat/tech")
    print("  - WebSocket connection to ws://localhost:8080/ws/data-stream")
    
    # Check if SSL certificates exist for HTTPS
    ssl_context = None
    cert_file = os.path.join(os.path.dirname(__file__), '../cert.pem')
    key_file = os.path.join(os.path.dirname(__file__), '../key.pem')
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        print("\nSSL certificates found. HTTPS will be enabled.")
        print("Try these secure endpoints:")
        print("  - https://localhost:8443/")
        print("  - WebSocket connection to wss://localhost:8443/ws/chat")
        
        # Create SSL context for HTTPS
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_file, key_file)
        
        # Enable HTTP/2.0 via ALPN
        ssl_context.set_alpn_protocols(['h2', 'http/1.1'])
    
    # Define async function to run the server
    async def start_server():
        try:
            if ssl_context:
                # Run HTTP and HTTPS servers
                http_server = asyncio.create_task(run(host="0.0.0.0", port=8080))
                https_server = asyncio.create_task(run(host="0.0.0.0", port=8443, ssl_context=ssl_context))
                
                # Wait for both servers
                await asyncio.gather(http_server, https_server)
            else:
                # Run HTTP server only
                await run(host="0.0.0.0", port=8080)
        except Exception as e:
            print(f"\nServer error: {e}")
    
    try:
        # Run the server
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("\nServer stopped")