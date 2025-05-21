from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from .location import Location


class OrderStatus(str, Enum):
    """Enumeration of possible order statuses."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELED = "canceled"


class OrderBase(BaseModel):
    """Base model for order information."""
    customer_name: str = Field(..., description="Name of the customer")
    customer_phone: str = Field(..., description="Customer's phone number")
    location: Location = Field(..., description="Delivery location")
    items_count: int = Field(default=1, description="Number of items in the order")
    weight: float = Field(default=1.0, description="Weight of the order in kg")
    delivery_window_start: Optional[datetime] = Field(
        None, description="Start of delivery time window"
    )
    delivery_window_end: Optional[datetime] = Field(
        None, description="End of delivery time window"
    )
    
    
class OrderCreate(OrderBase):
    """Model for creating a new order."""
    pass


class Order(OrderBase):
    """Full order model with ID and status."""
    id: UUID = Field(default_factory=uuid4, description="Unique order identifier")
    status: OrderStatus = Field(
        default=OrderStatus.PENDING, description="Current status of the order"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Order creation timestamp"
    )
    courier_id: Optional[UUID] = Field(None, description="ID of assigned courier")
    depot_id: Optional[UUID] = Field(None, description="ID of assigned depot") 