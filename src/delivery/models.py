"""Delivery domain models.

DeliveryStatus lives here (not in orders) because it describes a delivery-domain
concept. Orders imports it from here rather than defining it themselves.
"""
from enum import Enum


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RECEIVED = "received"
    RETURNED = "returned"
