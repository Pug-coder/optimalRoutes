from pydantic import BaseModel, Field


class Location(BaseModel):
    """Location model with latitude and longitude coordinates."""
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    address: str = Field(None, description="Address of the location (optional)")
    
    def distance_to(self, other: "Location") -> float:
        """Calculate Euclidean distance to another location."""
        return ((self.lat - other.lat) ** 2 + (self.lng - other.lng) ** 2) ** 0.5 