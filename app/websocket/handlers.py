"""
WebSocket handlers for real-time progress updates using Redis Pub/Sub
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from app.utils.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client = None
        
        # Initialize Redis async client if available
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                logger.info("Redis async client initialized for WebSocket streaming")
            except Exception as e:
                logger.warning(f"Redis client init failed: {e}")
                self.redis_client = None
    
    async def connect(self, websocket: WebSocket, doc_id: str):
        """
        Connect a WebSocket for a document and start Redis subscription
        
        Args:
            websocket: WebSocket connection
            doc_id: Document ID to track
        """
        await websocket.accept()
        
        if doc_id not in self.active_connections:
            self.active_connections[doc_id] = set()
        
        self.active_connections[doc_id].add(websocket)
        logger.info(f"WebSocket connected for doc {doc_id}")
        
        # Start Redis Pub/Sub listener for this doc_id
        if self.redis_client:
            asyncio.create_task(self._redis_listener(doc_id))
    
    def disconnect(self, websocket: WebSocket, doc_id: str):
        """
        Disconnect a WebSocket
        
        Args:
            websocket: WebSocket connection
            doc_id: Document ID
        """
        if doc_id in self.active_connections:
            self.active_connections[doc_id].discard(websocket)
            if not self.active_connections[doc_id]:
                del self.active_connections[doc_id]
        logger.info(f"WebSocket disconnected for doc {doc_id}")
    
    async def _redis_listener(self, doc_id: str):
        """
        Subscribe to Redis Pub/Sub channel for doc_id and forward events to WebSocket clients
        
        Args:
            doc_id: Document ID
        """
        if not self.redis_client:
            return
        
        channel = f"doc:{doc_id}"
        logger.info(f"Starting Redis Pub/Sub listener for channel: {channel}")
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(channel)
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        # Parse event data
                        event_data = json.loads(message['data'])
                        logger.debug(f"Received event from Redis: {event_data}")
                        
                        # Forward to all connected WebSocket clients
                        await self.broadcast(doc_id, event_data)
                        
                        # Stop listening if task completed or failed
                        if event_data.get('stage') in ['completed', 'failed']:
                            logger.info(f"Task {event_data.get('stage')} for doc {doc_id}, stopping listener")
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
                
                # Stop if no more connections
                if doc_id not in self.active_connections:
                    logger.info(f"No active connections for doc {doc_id}, stopping listener")
                    break
            
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            
        except Exception as e:
            logger.error(f"Redis listener error for {doc_id}: {e}")
    
    async def broadcast(self, doc_id: str, message: Dict):
        """
        Broadcast message to all connections for a document
        
        Args:
            doc_id: Document ID
            message: Message dictionary
        """
        if doc_id not in self.active_connections:
            return
        
        disconnected = set()
        for websocket in self.active_connections[doc_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, doc_id)
    
    async def send_progress(self, task_id: str, message: Dict):
        """
        Legacy method - kept for backward compatibility
        Now progress comes from Redis Pub/Sub, not direct calls
        
        Args:
            task_id: Task ID (deprecated, use doc_id)
            message: Progress message dictionary
        """
        # This is now handled by Redis Pub/Sub automatically
        # Kept for backward compatibility but does nothing
        pass


# Global connection manager
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, doc_id: str):
    """
    WebSocket endpoint for document progress tracking
    
    Args:
        websocket: WebSocket connection
        doc_id: Document ID to track (now uses doc_id instead of task_id for consistency)
    """
    await manager.connect(websocket, doc_id)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo back or handle client messages
            await websocket.send_json({"type": "ack", "message": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, doc_id)


