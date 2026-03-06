"""WebSocket endpoint for real-time updates."""

import json
import logging
from datetime import datetime, timezone
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.models import Equipment, CycleLabel, Alert
from backend.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections and broadcasting."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self.equipment_subscriptions: dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, equipment_id: int = None):
        """
        Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            equipment_id: Optional equipment ID for filtering
        """
        await websocket.accept()
        self.active_connections.add(websocket)

        if equipment_id:
            if equipment_id not in self.equipment_subscriptions:
                self.equipment_subscriptions[equipment_id] = set()
            self.equipment_subscriptions[equipment_id].add(websocket)
            logger.info(f"Client connected (equipment {equipment_id}): {len(self.equipment_subscriptions[equipment_id])} subscribers")
        else:
            logger.info(f"Client connected (global): {len(self.active_connections)} total connections")

    def disconnect(self, websocket: WebSocket, equipment_id: int = None):
        """
        Unregister a WebSocket connection.

        Args:
            websocket: WebSocket connection
            equipment_id: Optional equipment ID
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if equipment_id and equipment_id in self.equipment_subscriptions:
            if websocket in self.equipment_subscriptions[equipment_id]:
                self.equipment_subscriptions[equipment_id].remove(websocket)

        logger.info(f"Client disconnected (equipment {equipment_id}): {len(self.active_connections)} remaining")

    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dict to send
        """
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

    async def broadcast_to_equipment(self, equipment_id: int, message: dict):
        """
        Broadcast message to clients subscribed to specific equipment.

        Args:
            equipment_id: Equipment ID
            message: Message dict to send
        """
        if equipment_id not in self.equipment_subscriptions:
            return

        for connection in self.equipment_subscriptions[equipment_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to equipment {equipment_id}: {e}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send message to specific connection.

        Args:
            message: Message dict
            websocket: WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")


# Global connection manager
manager = ConnectionManager()


async def handle_websocket(websocket: WebSocket, equipment_id: int = None):
    """
    Handle WebSocket connection.

    Args:
        websocket: WebSocket connection
        equipment_id: Optional equipment ID to filter messages
    """
    await manager.connect(websocket, equipment_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.debug(f"Received WebSocket message: {message}")

            # Handle different message types
            message_type = message.get("type")

            if message_type == "ping":
                # Echo ping for heartbeat
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, websocket)

            elif message_type == "request_equipment_status":
                # Client requesting equipment status
                eq_id = message.get("equipment_id")
                await send_equipment_status(websocket, eq_id)

            elif message_type == "request_active_cycle":
                # Client requesting current active cycle
                eq_id = message.get("equipment_id")
                await send_active_cycle(websocket, eq_id)

            elif message_type == "request_alerts":
                # Client requesting alerts for equipment
                eq_id = message.get("equipment_id")
                await send_equipment_alerts(websocket, eq_id)

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, equipment_id)
        logger.info(f"WebSocket client disconnected (equipment {equipment_id})")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, equipment_id)


async def send_equipment_status(websocket: WebSocket, equipment_id: int):
    """Send equipment status to client."""
    db = SessionLocal()

    try:
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()

        if not equipment:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Equipment {equipment_id} not found"
            }, websocket)
            return

        # Get cached status or use database status
        cached_status = cache_service.get_equipment_status(equipment_id)
        status = cached_status.get("status") if cached_status else equipment.status

        await manager.send_personal_message({
            "type": "equipment_status",
            "equipment_id": equipment_id,
            "name": equipment.name,
            "status": status,
            "location": equipment.location,
            "model": equipment.model,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, websocket)

    finally:
        db.close()


async def send_active_cycle(websocket: WebSocket, equipment_id: int):
    """Send active cycle information to client."""
    db = SessionLocal()

    try:
        # Get cached active cycle
        active_cycle = cache_service.get_active_cycle(equipment_id)

        if active_cycle:
            await manager.send_personal_message({
                "type": "active_cycle",
                "equipment_id": equipment_id,
                "data": active_cycle,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, websocket)
        else:
            await manager.send_personal_message({
                "type": "active_cycle",
                "equipment_id": equipment_id,
                "data": None,
                "message": "No active cycle",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, websocket)

    finally:
        db.close()


async def send_equipment_alerts(websocket: WebSocket, equipment_id: int):
    """Send equipment alerts to client."""
    db = SessionLocal()

    try:
        # Get cached active alerts
        alerts = cache_service.get_active_alerts(equipment_id)

        await manager.send_personal_message({
            "type": "equipment_alerts",
            "equipment_id": equipment_id,
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, websocket)

    finally:
        db.close()


async def broadcast_cycle_completed(equipment_id: int, cycle_data: dict):
    """
    Broadcast cycle completion to all connected clients.

    Called by cycle detection engine.
    """
    message = {
        "type": "cycle_completed",
        "equipment_id": equipment_id,
        "data": {
            "start_time": cycle_data.get("start_time"),
            "end_time": cycle_data.get("end_time"),
            "cycle_duration": cycle_data.get("cycle_duration"),
            "status": cycle_data.get("status"),
            "detection_method": cycle_data.get("detection_method"),
            "confidence": cycle_data.get("confidence")
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Broadcast to all clients
    await manager.broadcast(message)

    # Also broadcast to equipment-specific subscribers
    await manager.broadcast_to_equipment(equipment_id, message)

    logger.info(f"Broadcasted cycle_completed for equipment {equipment_id}")


async def broadcast_alert_created(alert_data: dict):
    """
    Broadcast new alert to all connected clients.

    Called by alert engine.
    """
    equipment_id = alert_data.get("equipment_id")

    message = {
        "type": "alert_created",
        "equipment_id": equipment_id,
        "data": {
            "id": alert_data.get("id"),
            "alert_type": alert_data.get("alert_type"),
            "severity": alert_data.get("severity"),
            "message": alert_data.get("message"),
            "cycle_time": alert_data.get("cycle_time"),
            "threshold_min": alert_data.get("threshold_min"),
            "threshold_max": alert_data.get("threshold_max"),
            "created_at": alert_data.get("created_at")
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Broadcast to all clients
    await manager.broadcast(message)

    # Also broadcast to equipment-specific subscribers
    await manager.broadcast_to_equipment(equipment_id, message)

    logger.warning(f"Broadcasted alert_created: {alert_data.get('alert_type')} for equipment {equipment_id}")


async def broadcast_equipment_status_changed(equipment_id: int, status: str):
    """
    Broadcast equipment status change to connected clients.

    Called when equipment status changes.
    """
    message = {
        "type": "equipment_status_changed",
        "equipment_id": equipment_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Broadcast to all clients
    await manager.broadcast(message)

    # Also broadcast to equipment-specific subscribers
    await manager.broadcast_to_equipment(equipment_id, message)

    logger.info(f"Broadcasted status_changed for equipment {equipment_id}: {status}")
