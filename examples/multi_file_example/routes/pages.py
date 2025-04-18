"""
Page routes for the multi-file example.

This module contains all the page routes for the application.
"""

import sys
import os
import time
from typing import Dict, List, Any

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from httpy import (
    Response, Request, get, post,
    HTTP_404_NOT_FOUND
)

# HTML Templates
def render_template(template_name: str, **context) -> str:
    """Simple template rendering function."""
    templates = {
        "index": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HTTPy Multi-File Example</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 15px; color: #0066cc; text-decoration: none; }
                .nav a:hover { text-decoration: underline; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>Welcome to HTTPy Multi-File Example</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/users">Users</a>
                <a href="/chat">Chat</a>
            </div>
            <div class="content">
                <p>This is a demonstration of a multi-file HTTPy application.</p>
                <p>The current time is: {current_time}</p>
                <p>Try the following endpoints:</p>
                <ul>
                    <li><a href="/api/users">API: List Users</a></li>
                    <li><a href="/api/users/1">API: Get User 1</a></li>
                    <li>Connect to WebSocket: <code>ws://localhost:8080/ws/chat</code></li>
                </ul>
            </div>
        </body>
        </html>
        """,
        
        "about": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>About - HTTPy Multi-File Example</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 15px; color: #0066cc; text-decoration: none; }
                .nav a:hover { text-decoration: underline; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>About HTTPy</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/users">Users</a>
                <a href="/chat">Chat</a>
            </div>
            <div class="content">
                <p>HTTPy is a simple and intuitive HTTP server library for Python.</p>
                <p>Features:</p>
                <ul>
                    <li>HTTP/1.1, HTTP/2, and HTTP/3 support</li>
                    <li>WebSocket support</li>
                    <li>Decorator-based routing</li>
                    <li>Path parameters</li>
                    <li>JSON handling</li>
                    <li>File uploads/downloads</li>
                </ul>
            </div>
        </body>
        </html>
        """,
        
        "users": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Users - HTTPy Multi-File Example</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 15px; color: #0066cc; text-decoration: none; }
                .nav a:hover { text-decoration: underline; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
            </style>
            <script>
                // Simple JavaScript to fetch users from the API
                window.onload = function() {
                    fetch('/api/users')
                        .then(response => response.json())
                        .then(users => {
                            const tbody = document.getElementById('users-table-body');
                            tbody.innerHTML = '';
                            users.forEach(user => {
                                tbody.innerHTML += `
                                    <tr>
                                        <td>${user.id}</td>
                                        <td>${user.name}</td>
                                        <td>${user.email}</td>
                                    </tr>
                                `;
                            });
                        })
                        .catch(error => console.error('Error fetching users:', error));
                };
            </script>
        </head>
        <body>
            <h1>Users</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/users">Users</a>
                <a href="/chat">Chat</a>
            </div>
            <div class="content">
                <p>This page demonstrates fetching data from the API.</p>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Email</th>
                        </tr>
                    </thead>
                    <tbody id="users-table-body">
                        <tr>
                            <td colspan="3">Loading users...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """,
        
        "chat": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chat - HTTPy Multi-File Example</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 15px; color: #0066cc; text-decoration: none; }
                .nav a:hover { text-decoration: underline; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; }
                #chat-box { height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; margin-bottom: 10px; }
                #message-form { display: flex; }
                #message-input { flex-grow: 1; padding: 8px; }
                button { padding: 8px 16px; background: #0066cc; color: white; border: none; cursor: pointer; }
            </style>
            <script>
                let socket;
                
                function connect() {
                    // Connect to WebSocket
                    socket = new WebSocket(`ws://${window.location.host}/ws/chat`);
                    
                    // Connection opened
                    socket.addEventListener('open', function (event) {
                        addMessage('System', 'Connected to chat server');
                    });
                    
                    // Listen for messages
                    socket.addEventListener('message', function (event) {
                        addMessage('Server', event.data);
                    });
                    
                    // Connection closed
                    socket.addEventListener('close', function (event) {
                        addMessage('System', 'Disconnected from chat server');
                        // Try to reconnect after a delay
                        setTimeout(connect, 3000);
                    });
                    
                    // Connection error
                    socket.addEventListener('error', function (event) {
                        addMessage('System', 'WebSocket error');
                    });
                }
                
                function sendMessage() {
                    const input = document.getElementById('message-input');
                    const message = input.value.trim();
                    
                    if (message && socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(message);
                        addMessage('You', message);
                        input.value = '';
                    }
                }
                
                function addMessage(sender, message) {
                    const chatBox = document.getElementById('chat-box');
                    const messageElement = document.createElement('div');
                    messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
                    chatBox.appendChild(messageElement);
                    chatBox.scrollTop = chatBox.scrollHeight;
                }
                
                window.onload = function() {
                    // Connect to WebSocket when page loads
                    connect();
                    
                    // Set up form submission
                    document.getElementById('message-form').addEventListener('submit', function(e) {
                        e.preventDefault();
                        sendMessage();
                    });
                };
            </script>
        </head>
        <body>
            <h1>Chat Room</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/users">Users</a>
                <a href="/chat">Chat</a>
            </div>
            <div class="content">
                <p>This page demonstrates WebSocket communication.</p>
                <div id="chat-box"></div>
                <form id="message-form">
                    <input type="text" id="message-input" placeholder="Type a message..." autocomplete="off">
                    <button type="submit">Send</button>
                </form>
            </div>
        </body>
        </html>
        """,
        
        "404": """
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Page Not Found</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; text-align: center; }
                h1 { color: #d9534f; }
                .nav { margin-bottom: 20px; }
                .nav a { margin-right: 15px; color: #0066cc; text-decoration: none; }
                .nav a:hover { text-decoration: underline; }
                .content { background: #f9f9f9; padding: 20px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>404 - Page Not Found</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/about">About</a>
                <a href="/users">Users</a>
                <a href="/chat">Chat</a>
            </div>
            <div class="content">
                <p>The page you requested could not be found.</p>
                <p>Path: {path}</p>
            </div>
        </body>
        </html>
        """
    }
    
    template = templates.get(template_name, templates["404"])
    return template.format(**context)

# Page Routes

@get("/")
async def index(req: Request) -> Response:
    """Render the homepage."""
    html = render_template("index", current_time=time.strftime("%Y-%m-%d %H:%M:%S"))
    return Response.html(html)

@get("/about")
async def about(req: Request) -> Response:
    """Render the about page."""
    html = render_template("about")
    return Response.html(html)

@get("/users")
async def users_page(req: Request) -> Response:
    """Render the users page."""
    html = render_template("users")
    return Response.html(html)

@get("/chat")
async def chat_page(req: Request) -> Response:
    """Render the chat page."""
    html = render_template("chat")
    return Response.html(html)

@get("/{path:path}")
async def not_found(req: Request) -> Response:
    """Handle 404 errors."""
    path = req.path_params.get('path', '')
    html = render_template("404", path=path)
    return Response.html(html, status=HTTP_404_NOT_FOUND)