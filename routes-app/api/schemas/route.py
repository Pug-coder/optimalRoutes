from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class RoutePointBase(BaseModel):
    """Base route point schema."""
    order_id: UUID = Field(
        ..., 
        description="ID of the order for this stop"
    )
    sequence: int = Field(
        ..., 
        description="Position in the delivery sequence",
        ge=0
    )
    estimated_arrival: Optional[datetime] = Field(
        None, 
        description="Estimated arrival time"
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_sequence(cls, data):
        if isinstance(data, dict) and 'sequence' in data:
            if data['sequence'] < 0:
                raise ValueError('sequence must be non-negative')
        return data


class RoutePointResponse(RoutePointBase):
    """Schema for route point responses."""
    id: UUID = Field(..., description="Route point identifier")
    
    model_config = {"from_attributes": True}


class RouteBase(BaseModel):
    """Base route schema."""
    total_distance: float = Field(
        0.0, 
        description="Total distance of the route in km",
        ge=0.0
    )
    total_load: int = Field(
        0, 
        description="Total number of items in the route",
        ge=0
    )
    total_weight: float = Field(
        0.0,
        description="Total weight of items in the route in kg",
        ge=0.0
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_values(cls, data):
        if isinstance(data, dict):
            # Проверка расстояния
            if 'total_distance' in data and data['total_distance'] < 0:
                raise ValueError('total distance cannot be negative')
            
            # Проверка нагрузки
            if 'total_load' in data and data['total_load'] < 0:
                raise ValueError('total load cannot be negative')
            
            # Проверка веса
            if 'total_weight' in data and data['total_weight'] < 0:
                raise ValueError('total weight cannot be negative')
        return data


class RouteCreate(RouteBase):
    """Schema for creating a new route."""
    courier_id: UUID = Field(
        ..., 
        description="ID of the courier"
    )
    depot_id: UUID = Field(
        ..., 
        description="ID of the depot"
    )
    points: List[RoutePointBase] = Field(
        default=[], 
        description="Ordered sequence of delivery points"
    )
    
    @model_validator(mode='after')
    def validate_points_sequence(self):
        points = self.points
        if not points:
            return self
            
        sequences = [p.sequence for p in points]
        
        # Проверка дубликатов в последовательности
        if len(sequences) != len(set(sequences)):
            raise ValueError('route points cannot have duplicate sequence numbers')
        
        # Проверка отсортированности последовательности
        if sorted(sequences) != list(range(min(sequences), max(sequences) + 1)):
            raise ValueError('sequence numbers must be consecutive')
        
        return self


class RouteResponse(RouteBase):
    """Schema for route responses."""
    id: UUID = Field(..., description="Route identifier")
    courier_id: UUID = Field(..., description="ID of the courier")
    depot_id: UUID = Field(..., description="ID of the depot")
    created_at: datetime = Field(..., description="Route creation timestamp")
    points: List[RoutePointResponse] = Field(
        ..., 
        description="Ordered sequence of delivery points"
    )
    
    model_config = {"from_attributes": True}


class OptimizationResponse(BaseModel):
    """Schema for optimization results."""
    algorithm: str = Field(
        ..., description="Algorithm used for optimization"
    )
    routes: List[RouteResponse] = Field(
        ..., description="Optimized routes"
    )
    total_distance: float = Field(
        ..., description="Total distance of all routes"
    )
    total_orders: int = Field(
        ..., description="Total number of orders processed"
    )
    assigned_orders: int = Field(
        ..., description="Number of orders assigned to routes"
    )
    execution_time: float = Field(
        ..., description="Optimization execution time in seconds"
    )
    
    model_config = {"from_attributes": True}


# Добавляем схему для локации
class LocationResponse(BaseModel):
    """Schema for location in responses."""
    id: str = Field(..., description="Location identifier")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    address: Optional[str] = Field(None, description="Address description")
    
    model_config = {"from_attributes": True}


class RoutePointWithLocationResponse(RoutePointBase):
    """Schema for route point responses with location data."""
    id: UUID = Field(..., description="Route point identifier")
    order_location: LocationResponse = Field(
        ..., 
        description="Location data for this order"
    )
    customer_name: str = Field(..., description="Customer name")
    
    model_config = {"from_attributes": True}


class RouteWithLocationsResponse(RouteBase):
    """Schema for route responses with full location data."""
    id: UUID = Field(..., description="Route identifier")
    courier_id: UUID = Field(..., description="ID of the courier")
    depot_id: UUID = Field(..., description="ID of the depot")
    depot_location: LocationResponse = Field(
        ..., 
        description="Depot location data"
    )
    created_at: datetime = Field(..., description="Route creation timestamp")
    points: List[RoutePointWithLocationResponse] = Field(
        ..., 
        description="Ordered sequence of delivery points with locations"
    )
    
    model_config = {"from_attributes": True} 