"""WebSocket manager for real-time order updates."""
from typing import Dict, Set
from fastapi import WebSocket


class OrdersWebSocketManager:
    """Manager for WebSocket connections to broadcast order updates."""

    def __init__(self):
        # Maps connection to set of watched order IDs (None = watching all orders)
        self.active_connections: Dict[WebSocket, Set[int] | None] = {}

    async def connect(self, websocket: WebSocket, order_id: int | None = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if order_id:
            self.active_connections[websocket] = {order_id}
        else:
            # None means watching all orders (for admin orders list page)
            self.active_connections[websocket] = None

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def broadcast_order_update(self, order_id: int, html: str, field: str = "status"):
        """
        Broadcast an order update to all relevant clients.

        Args:
            order_id: The ID of the updated order
            html: The HTML fragment to send
            field: The field that was updated (status, ttn, etc.)
        """
        disconnected = []

        for connection, watched_orders in self.active_connections.items():
            # Send to connections watching all orders OR watching this specific order
            if watched_orders is None or order_id in watched_orders:
                try:
                    await connection.send_json({
                        "type": "order_update",
                        "order_id": order_id,
                        "field": field,
                        "html": html
                    })
                except Exception:
                    # Connection is broken, mark for removal
                    disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global WebSocket manager instance
ws_manager = OrdersWebSocketManager()
