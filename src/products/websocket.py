"""WebSocket manager for real-time product updates."""
from typing import Dict, Set
from fastapi import WebSocket


class ProductsWebSocketManager:
    """Manager for WebSocket connections to broadcast product updates."""

    def __init__(self):
        # Maps connection to set of watched product IDs (None = watching all products)
        self.active_connections: Dict[WebSocket, Set[int] | None] = {}

    async def connect(self, websocket: WebSocket, product_id: int | None = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if product_id:
            self.active_connections[websocket] = {product_id}
        else:
            # None means watching all products (for admin products list page)
            self.active_connections[websocket] = None

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            del self.active_connections[websocket]

    async def broadcast_product_update(self, product_id: int, field: str, html: str):
        """
        Broadcast a product update to all relevant clients.

        Args:
            product_id: The ID of the updated product
            field: The field that was updated (name, price, in_stock, etc.)
            html: The HTML fragment to send
        """
        disconnected = []

        for connection, watched_products in self.active_connections.items():
            # Send to connections watching all products OR watching this specific product
            if watched_products is None or product_id in watched_products:
                try:
                    await connection.send_json({
                        "type": "product_update",
                        "product_id": product_id,
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
ws_manager = ProductsWebSocketManager()
