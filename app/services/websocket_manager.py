"""
WebSocket Connection Manager with Redis Pub/Sub support.

Manages active WebSockets connections grouped by tenant business ID.
Uses Redis Pub/Sub to broadcast messages across multiple instances
of the application to ensure all clients for a tenant receive updates
regardless of which server node they are connected to.
"""

import asyncio
import json
import uuid
from typing import Any

from fastapi import WebSocket

from app.core.logging import logger
from app.services.redis import redis_service


class ConnectionManager:
    """Manages active WebSockets connections with Redis Pub/Sub for multi-instance broadcast."""

    def __init__(self) -> None:
        # Group local active connections by business_id UUID
        self.active_connections: dict[uuid.UUID, list[WebSocket]] = {}
        # Keep track of Redis pub/sub listener tasks per tenant
        self._listener_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def connect(self, websocket: WebSocket, business_id: uuid.UUID) -> None:
        """Accepts the WebSocket connection and subscribes to the tenant room."""
        await websocket.accept()
        
        if business_id not in self.active_connections:
            self.active_connections[business_id] = []
            # Start a Redis listener for this tenant if not already running
            self._start_redis_listener(business_id)
            
        self.active_connections[business_id].append(websocket)
        logger.info(
            "WebSocket client connected to tenant room",
            business_id=str(business_id),
            active_count=len(self.active_connections[business_id]),
        )

    def disconnect(self, websocket: WebSocket, business_id: uuid.UUID) -> None:
        """Unsubscribes the WebSocket connection from the tenant room."""
        if business_id in self.active_connections:
            if websocket in self.active_connections[business_id]:
                self.active_connections[business_id].remove(websocket)
            
            # If no local connections left for this tenant, stop the Redis listener
            if not self.active_connections[business_id]:
                del self.active_connections[business_id]
                self._stop_redis_listener(business_id)
                
        logger.info("WebSocket client disconnected from tenant room", business_id=str(business_id))

    async def broadcast_to_tenant(self, business_id: uuid.UUID, message: dict[str, Any]) -> None:
        """
        Publishes a message to the Redis channel for the specific tenant ID.
        All instances listening to this channel will receive it and push to their local websockets.
        """
        if not redis_service.redis:
            await redis_service.connect()
            
        channel = f"tenant:{business_id}"
        message_json = json.dumps(message)
        
        try:
            if redis_service.redis:
                await redis_service.redis.publish(channel, message_json)
            else:
                # Fallback to local broadcast if Redis is completely unavailable
                await self._local_broadcast(business_id, message)
        except Exception as e:
            logger.error("Failed to publish WebSocket message to Redis", error=str(e), channel=channel)
            # Fallback to local broadcast
            await self._local_broadcast(business_id, message)

    async def _local_broadcast(self, business_id: uuid.UUID, message: dict[str, Any]) -> None:
        """Sends a JSON payload exclusively to locally connected WebSocket clients."""
        if business_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[business_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "Failed to send real-time WebSocket update to client",
                    business_id=str(business_id),
                    error=str(e),
                )
                dead_connections.append(connection)

        # Cleanup dead connection sockets
        for dead in dead_connections:
            self.disconnect(dead, business_id)

    def _start_redis_listener(self, business_id: uuid.UUID) -> None:
        """Starts a background task to listen for Redis Pub/Sub messages for a tenant."""
        if business_id in self._listener_tasks:
            return
            
        task = asyncio.create_task(self._redis_listener_loop(business_id))
        self._listener_tasks[business_id] = task
        logger.debug("Started Redis listener for tenant", business_id=str(business_id))

    def _stop_redis_listener(self, business_id: uuid.UUID) -> None:
        """Stops the Redis Pub/Sub listener for a tenant."""
        task = self._listener_tasks.pop(business_id, None)
        if task:
            task.cancel()
            logger.debug("Stopped Redis listener for tenant", business_id=str(business_id))

    async def _redis_listener_loop(self, business_id: uuid.UUID) -> None:
        """Background loop listening to a specific Redis channel."""
        channel_name = f"tenant:{business_id}"
        
        if not redis_service.redis:
            await redis_service.connect()
            
        if not redis_service.redis:
            logger.error("Cannot start Redis listener: Redis service unavailable")
            return
            
        pubsub = redis_service.redis.pubsub()
        await pubsub.subscribe(channel_name)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self._local_broadcast(business_id, data)
                    except json.JSONDecodeError:
                        logger.warning("Received invalid JSON on Redis pubsub", channel=channel_name)
                    except Exception as e:
                        logger.error("Error processing Redis pubsub message", error=str(e))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis listener loop crashed", error=str(e), channel=channel_name)
        finally:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception:
                pass


# Global singleton instance of WebSocket ConnectionManager
manager = ConnectionManager()
