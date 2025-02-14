from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    def __init__(self):
        # Store active connections by session_id and conversation_id
        self.active_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        conversation_id: str
    ):
        """Connect a new WebSocket client"""
        await websocket.accept()
        
        # Initialize session dict if needed
        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}
            
        # Initialize conversation set if needed
        if conversation_id not in self.active_connections[session_id]:
            self.active_connections[session_id][conversation_id] = set()
            
        # Add connection
        self.active_connections[session_id][conversation_id].add(websocket)

    def disconnect(
        self,
        websocket: WebSocket,
        session_id: str,
        conversation_id: str
    ):
        """Disconnect a WebSocket client"""
        if session_id in self.active_connections:
            if conversation_id in self.active_connections[session_id]:
                self.active_connections[session_id][conversation_id].remove(websocket)
                
                # Clean up empty sets
                if not self.active_connections[session_id][conversation_id]:
                    del self.active_connections[session_id][conversation_id]
                    
            # Clean up empty session dicts
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_conversation(
        self,
        session_id: str,
        conversation_id: str,
        message: dict
    ):
        """Broadcast a message to all clients in a conversation"""
        if session_id in self.active_connections:
            if conversation_id in self.active_connections[session_id]:
                message["timestamp"] = datetime.utcnow().isoformat()
                
                # Send to all connected clients
                for connection in self.active_connections[session_id][conversation_id]:
                    try:
                        await connection.send_json(message)
                    except WebSocketDisconnect:
                        self.disconnect(connection, session_id, conversation_id)

    async def broadcast_typing_status(
        self,
        session_id: str,
        conversation_id: str,
        is_typing: bool
    ):
        """Broadcast typing status to conversation"""
        await self.broadcast_to_conversation(
            session_id,
            conversation_id,
            {
                "type": "typing_status",
                "is_typing": is_typing
            }
        )

# Create global connection manager
manager = ConnectionManager()

async def chat_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    conversation_id: str
):
    """WebSocket endpoint for chat connections"""
    await manager.connect(websocket, session_id, conversation_id)
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            
            # Handle different message types
            message_type = data.get("type")
            
            if message_type == "typing":
                # Broadcast typing status
                await manager.broadcast_typing_status(
                    session_id,
                    conversation_id,
                    data.get("is_typing", False)
                )
            
            elif message_type == "message":
                # Broadcast message to all clients
                await manager.broadcast_to_conversation(
                    session_id,
                    conversation_id,
                    {
                        "type": "message",
                        "content": data.get("content"),
                        "sender": data.get("sender")
                    }
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id, conversation_id)
        await manager.broadcast_to_conversation(
            session_id,
            conversation_id,
            {
                "type": "system",
                "content": "Client disconnected"
            }
        ) 