from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Dict, List
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, List[str]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = []
        logger.info(f"Client {client_id} connected via WebSocket")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except:
                self.disconnect(client_id)
    
    async def broadcast_to_subscribers(self, message: str, event_type: str):
        message_data = json.loads(message)
        item_fingerprint = message_data.get('fingerprint')
        
        disconnected_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if event_type in subscriptions or 'all' in subscriptions:
                try:
                    await self.active_connections[client_id].send_text(message)
                except:
                    disconnected_clients.append(client_id)
        
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def add_subscription(self, client_id: str, event_type: str):
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = []
        if event_type not in self.client_subscriptions[client_id]:
            self.client_subscriptions[client_id].append(event_type)
    
    def remove_subscription(self, client_id: str, event_type: str):
        if client_id in self.client_subscriptions:
            if event_type in self.client_subscriptions[client_id]:
                self.client_subscriptions[client_id].remove(event_type)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get('type') == 'subscribe':
                    event_types = message.get('events', [])
                    for event_type in event_types:
                        manager.add_subscription(client_id, event_type)
                    await manager.send_personal_message(
                        json.dumps({"type": "subscription_confirmed", "events": event_types}),
                        client_id
                    )
                
                elif message.get('type') == 'unsubscribe':
                    event_types = message.get('events', [])
                    for event_type in event_types:
                        manager.remove_subscription(client_id, event_type)
                    await manager.send_personal_message(
                        json.dumps({"type": "unsubscription_confirmed", "events": event_types}),
                        client_id
                    )
                
                elif message.get('type') == 'ping':
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                        client_id
                    )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Invalid JSON"}),
                    client_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)