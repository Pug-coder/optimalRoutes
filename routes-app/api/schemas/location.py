from pydantic import BaseModel, Field, model_validator
from typing import Optional


class LocationBase(BaseModel):
    """Base location schema."""
    latitude: float = Field(
        ..., 
        description="Latitude coordinate",
        ge=-90.0,
        le=90.0
    )
    longitude: float = Field(
        ..., 
        description="Longitude coordinate",
        ge=-180.0,
        le=180.0
    )
    address: Optional[str] = Field(
        None, 
        description="Address of the location",
        min_length=3,
        max_length=200
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_address(cls, data):
        if isinstance(data, dict) and 'address' in data:
            address = data.get('address')
            if address is not None and isinstance(address, str) and address.strip() == '':
                raise ValueError('address cannot be an empty string if provided')
        return data


class LocationCreate(LocationBase):
    """Schema for creating a new location."""
    pass


class LocationResponse(LocationBase):
    """Schema for location responses."""
    id: str = Field(..., description="Location identifier")
    
    model_config = {"from_attributes": True} 