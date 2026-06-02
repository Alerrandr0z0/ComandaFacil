from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import WebSocket


class KdsWebSocketManager:
    """Manages active WebSocket connections for the Kitchen Display System (KDS).

    Supports multi-tenancy (X-Tenant-ID segregation) and station-based routing (Grill, Beverage, etc.).
    """

    def __init__(self) -> None:
        # Active connections dict format: tenant_id to dict of station_type to WebSocket list
        self._active_connections: dict[str, dict[str, list[WebSocket]]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, station_type: str) -> None:
        """Accepts the WebSocket connection and registers it under the correct tenant and station channel."""
        await websocket.accept()
        if tenant_id not in self._active_connections:
            self._active_connections[tenant_id] = {}
        if station_type not in self._active_connections[tenant_id]:
            self._active_connections[tenant_id][station_type] = []
        self._active_connections[tenant_id][station_type].append(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str, station_type: str) -> None:
        """Unregisters a client connection upon disconnection or drop."""
        if tenant_id in self._active_connections:
            if station_type in self._active_connections[tenant_id]:
                if websocket in self._active_connections[tenant_id][station_type]:
                    self._active_connections[tenant_id][station_type].remove(websocket)
                if not self._active_connections[tenant_id][station_type]:
                    del self._active_connections[tenant_id][station_type]
            if not self._active_connections[tenant_id]:
                del self._active_connections[tenant_id]

    async def broadcast_to_station(
        self, tenant_id: str, station_type: str, event_data: dict[str, Any]
    ) -> None:
        """Broadcasts a JSON event payload to all active connections in a specific tenant and station channel."""
        if tenant_id not in self._active_connections:
            return
        if station_type not in self._active_connections[tenant_id]:
            return

        dead_connections: list[WebSocket] = []
        for ws in self._active_connections[tenant_id][station_type]:
            try:
                await ws.send_json(event_data)
            except Exception:
                dead_connections.append(ws)

        # Clean up any dead connections caught
        for dead_ws in dead_connections:
            self.disconnect(dead_ws, tenant_id, station_type)


# Export a global instance for application handlers and API routes to share
kds_ws_manager = KdsWebSocketManager()
