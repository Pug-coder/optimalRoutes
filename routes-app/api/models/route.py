from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from .order import Order


class RoutePoint(BaseModel):
    """A point in a delivery route."""
    order_id: UUID = Field(..., description="ID of the order for this stop")
    sequence: int = Field(..., description="Position in the delivery sequence")
    estimated_arrival: Optional[datetime] = Field(
        None, description="Estimated arrival time"
    )


class Route(BaseModel):
    """A complete delivery route for a courier."""
    id: UUID = Field(default_factory=uuid4, description="Unique route identifier")
    courier_id: UUID = Field(..., description="ID of the courier")
    depot_id: UUID = Field(..., description="ID of the depot")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Route creation timestamp"
    )
    points: List[RoutePoint] = Field(
        default=[], description="Ordered sequence of delivery points"
    )
    total_distance: float = Field(
        default=0.0, description="Total distance of the route in km"
    )
    total_load: int = Field(
        default=0, description="Total number of items in the route"
    ) 