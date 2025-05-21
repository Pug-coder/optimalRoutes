from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from .location import Location


class DepotBase(BaseModel):
    """Base model for depot locations."""
    name: str = Field(..., description="Name of the depot")
    location: Location = Field(..., description="Location of the depot")
    
    
class DepotCreate(DepotBase):
    """Model for creating a new depot."""
    pass


class Depot(DepotBase):
    """Full depot model with ID."""
    id: UUID = Field(default_factory=uuid4, description="Unique depot identifier") 