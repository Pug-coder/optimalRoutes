from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from .depot import Depot


class CourierBase(BaseModel):
    """Base model for courier information."""
    name: str = Field(..., description="Name of the courier")
    phone: str = Field(None, description="Courier's phone number")
    depot_id: UUID = Field(..., description="ID of the depot the courier belongs to")
    max_capacity: int = Field(default=10, description="Maximum carrying capacity")
    max_distance: float = Field(
        default=float('inf'),
        description="Maximum travel distance in km"
    )
    
    
class CourierCreate(CourierBase):
    """Model for creating a new courier."""
    pass


class Courier(CourierBase):
    """Full courier model with ID."""
    id: UUID = Field(default_factory=uuid4, description="Unique courier identifier") 