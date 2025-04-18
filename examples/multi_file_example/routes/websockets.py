"""
WebSocket routes for the multi-file example.

This module contains all the WebSocket routes for the application.
"""

import sys
import os
import json
import time
import asyncio
import random
from typing import Dict, List, Set, Any

# Add the parent directory to the path so we can import the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from httpy import (
    websocket, WebSocketConnection
)

# Chat room implementation
class ChatRoom:
    """A simple chat room implementation."""
    
    def __init__(self, name: str):
        self.name = name
        self.clients: Set[WebSocketConnection] = set()
        self.history: List[Dict[str, Any]] = []
        self.max_history = 50
    
    async def join(self, ws: WebSocketConnection) -> None:
        """Add a client to the chat room."""
        # Add client to the room
        self.clients.add(ws)
        
        # Send welcome message
        await ws.send_text(f"Welcome to chat room: {self.name}")
        
        # Send recent history
        if self.history:
            await ws.send_text(f"Last {len(self.history)} messages:")
            for msg in self.history:
                await ws.send_text(f"[{msg['time']}] {msg['user']}: {msg['text']}")
    
    async def leave(self, ws: WebSocketConnection) -> None:
        """Remove a client from the chat room."""
        if ws in self.clients:
            self.clients.remove(ws)
    
    async def broadcast(self, message: str, sender: str) -> None:
        """Broadcast a message to all clients in the room."""
        # Create message object
        msg = {
            "time": time.strftime("%H:%M:%S"),
            "user": sender,
            "text": message
        }
        
        # Add to history
        self.history.append(msg)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Broadcast to all clients
        disconnected = set()
        for client in self.clients:
            try:
                await client.send_text(f"[{msg['time']}] {msg['user']}: {msg['text']}")
            except Exception:
                # Mark client for removal
                disconnected.add(client)
        
        # Remove disconnected clients
        for client in disconnected:
            await self.leave(client)

# Create chat rooms
chat_rooms: Dict[str, ChatRoom] = {
    "general": ChatRoom("general"),
    "tech": ChatRoom("tech"),
    "random": ChatRoom("random")
}

# WebSocket Routes

@websocket("/ws/chat")
async def chat_handler(ws: WebSocketConnection) -> None:
    """Handle WebSocket connections to the default chat room."""
    # Default to general chat room
    room = chat_rooms["general"]
    
    # Join the room
    await room.join(ws)
    
    try:
        # Process messages
        while True:
            msg = await ws.receive()
            
            if msg.is_text:
                text = msg.text()
                
                # Handle commands
                if text.startswith("/"):
                    parts = text.split(" ", 1)
                    command = parts[0].lower()
                    
                    if command == "/help":
                        await ws.send_text("Available commands:")
                        await ws.send_text("/help - Show this help message")
                        await ws.send_text("/rooms - List available rooms")
                        await ws.send_text("/join <room> - Join a different room")
                        await ws.send_text("/nick <name> - Change your nickname")
                        await ws.send_text("/quit - Disconnect from the chat")
                    
                    elif command == "/rooms":
                        await ws.send_text("Available rooms:")
                        for name in chat_rooms:
                            count = len(chat_rooms[name].clients)
                            await ws.send_text(f"- {name} ({count} users)")
                    
                    elif command == "/join" and len(parts) > 1:
                        new_room_name = parts[1].strip().lower()
                        if new_room_name in chat_rooms:
                            # Leave current room
                            await room.leave(ws)
                            # Join new room
                            room = chat_rooms[new_room_name]
                            await room.join(ws)
                        else:
                            await ws.send_text(f"Room '{new_room_name}' does not exist")
                    
                    elif command == "/nick" and len(parts) > 1:
                        new_nick = parts[1].strip()
                        # Store nickname in connection object
                        ws.user_data["nickname"] = new_nick
                        await ws.send_text(f"Your nickname is now: {new_nick}")
                    
                    elif command == "/quit":
                        await ws.send_text("Goodbye!")
                        await ws.close()
                        break
                    
                    else:
                        await ws.send_text(f"Unknown command: {command}")
                
                # Regular message
                else:
                    # Get nickname or use default
                    nickname = ws.user_data.get("nickname", "Anonymous")
                    # Broadcast message
                    await room.broadcast(text, nickname)
            
            elif msg.is_close:
                break
    
    except Exception as e:
        print(f"Chat WebSocket error: {e}")
    finally:
        # Leave the room
        await room.leave(ws)
        # Close connection if not already closed
        if not ws.closed:
            await ws.close()

@websocket("/ws/chat/{room_name}")
async def room_chat_handler(ws: WebSocketConnection) -> None:
    """Handle WebSocket connections to a specific chat room."""
    # Get room name from path parameters
    room_name = ws.path_params.get('room_name', 'general').lower()
    
    # Create room if it doesn't exist
    if room_name not in chat_rooms:
        chat_rooms[room_name] = ChatRoom(room_name)
    
    # Get the room
    room = chat_rooms[room_name]
    
    # Join the room
    await room.join(ws)
    
    try:
        # Process messages (same as default handler)
        while True:
            msg = await ws.receive()
            
            if msg.is_text:
                text = msg.text()
                
                # Handle commands
                if text.startswith("/"):
                    parts = text.split(" ", 1)
                    command = parts[0].lower()
                    
                    if command == "/help":
                        await ws.send_text("Available commands:")
                        await ws.send_text("/help - Show this help message")
                        await ws.send_text("/rooms - List available rooms")
                        await ws.send_text("/join <room> - Join a different room")
                        await ws.send_text("/nick <name> - Change your nickname")
                        await ws.send_text("/quit - Disconnect from the chat")
                    
                    elif command == "/rooms":
                        await ws.send_text("Available rooms:")
                        for name in chat_rooms:
                            count = len(chat_rooms[name].clients)
                            await ws.send_text(f"- {name} ({count} users)")
                    
                    elif command == "/join" and len(parts) > 1:
                        new_room_name = parts[1].strip().lower()
                        if new_room_name in chat_rooms:
                            # Leave current room
                            await room.leave(ws)
                            # Join new room
                            room = chat_rooms[new_room_name]
                            await room.join(ws)
                        else:
                            await ws.send_text(f"Room '{new_room_name}' does not exist")
                    
                    elif command == "/nick" and len(parts) > 1:
                        new_nick = parts[1].strip()
                        # Store nickname in connection object
                        ws.user_data["nickname"] = new_nick
                        await ws.send_text(f"Your nickname is now: {new_nick}")
                    
                    elif command == "/quit":
                        await ws.send_text("Goodbye!")
                        await ws.close()
                        break
                    
                    else:
                        await ws.send_text(f"Unknown command: {command}")
                
                # Regular message
                else:
                    # Get nickname or use default
                    nickname = ws.user_data.get("nickname", "Anonymous")
                    # Broadcast message
                    await room.broadcast(text, nickname)
            
            elif msg.is_close:
                break
    
    except Exception as e:
        print(f"Chat WebSocket error: {e}")
    finally:
        # Leave the room
        await room.leave(ws)
        # Close connection if not already closed
        if not ws.closed:
            await ws.close()

@websocket("/ws/data-stream")
async def data_stream_handler(ws: WebSocketConnection) -> None:
    """Handle WebSocket connections for a real-time data stream."""
    # Send welcome message
    await ws.send_text("Connected to data stream")
    
    # Set up data stream parameters
    interval = 1.0  # Default interval in seconds
    running = True
    
    try:
        # Start data stream task
        stream_task = asyncio.create_task(send_data_stream(ws, interval))
        
        # Process control messages
        while running:
            msg = await ws.receive()
            
            if msg.is_text:
                text = msg.text()
                
                try:
                    # Parse as JSON command
                    command = json.loads(text)
                    
                    # Handle interval change
                    if "interval" in command:
                        new_interval = float(command["interval"])
                        if 0.1 <= new_interval <= 10.0:
                            interval = new_interval
                            # Cancel and restart stream task
                            stream_task.cancel()
                            stream_task = asyncio.create_task(send_data_stream(ws, interval))
                            await ws.send_text(f"Interval changed to {interval} seconds")
                        else:
                            await ws.send_text("Interval must be between 0.1 and 10 seconds")
                    
                    # Handle stop command
                    elif "command" in command and command["command"] == "stop":
                        running = False
                        stream_task.cancel()
                        await ws.send_text("Data stream stopped")
                        await ws.close()
                        break
                
                except json.JSONDecodeError:
                    await ws.send_text("Invalid JSON command")
                except Exception as e:
                    await ws.send_text(f"Error processing command: {str(e)}")
            
            elif msg.is_close:
                running = False
                stream_task.cancel()
                break
    
    except asyncio.CancelledError:
        # Handle cancellation
        pass
    except Exception as e:
        print(f"Data stream WebSocket error: {e}")
    finally:
        # Ensure task is cancelled
        if 'stream_task' in locals() and not stream_task.done():
            stream_task.cancel()
        # Close connection if not already closed
        if not ws.closed:
            await ws.close()

async def send_data_stream(ws: WebSocketConnection, interval: float) -> None:
    """Send a stream of data at the specified interval."""
    try:
        while True:
            # Generate random data
            data = {
                "timestamp": time.time(),
                "values": {
                    "temperature": round(random.uniform(20, 30), 2),
                    "humidity": round(random.uniform(30, 70), 2),
                    "pressure": round(random.uniform(990, 1010), 2),
                    "wind_speed": round(random.uniform(0, 20), 2)
                }
            }
            
            # Send as JSON
            await ws.send_json(data)
            
            # Wait for next interval
            await asyncio.sleep(interval)
    
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        pass