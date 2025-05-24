from pydantic import BaseModel, Field, model_validator
from uuid import UUID

from .location import LocationCreate, LocationResponse


class DepotBase(BaseModel):
    """Base depot schema."""
    name: str = Field(
        ..., 
        description="Name of the depot", 
        min_length=2,
        max_length=100
    )
    
    @model_validator(mode='before')
    @classmethod
    def name_not_empty(cls, data):
        if isinstance(data, dict) and 'name' in data:
            name = data.get('name', '')
            if isinstance(name, str) and name.strip() == '':
                raise ValueError('depot name cannot be empty')
            # Очищаем пробелы если имя передано
            if isinstance(name, str):
                data['name'] = name.strip()
        return data


class DepotCreate(DepotBase):
    """Schema for creating a new depot."""
    location: LocationCreate = Field(
        ..., 
        description="Location of the depot"
    )
    
    @model_validator(mode='after')
    def validate_location(self):
        if not self.location:
            raise ValueError('location is required for depot creation')
        return self


class DepotResponse(DepotBase):
    """Schema for depot responses."""
    id: UUID = Field(..., description="Depot identifier")
    location: LocationResponse = Field(
        ..., 
        description="Location of the depot"
    )
    
    model_config = {"from_attributes": True} 