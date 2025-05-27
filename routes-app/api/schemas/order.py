from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import re

from .location import LocationCreate, LocationResponse
from api.models.order import OrderStatus


class OrderBase(BaseModel):
    """Base order schema."""
    customer_name: str = Field(
        ..., 
        description="Name of the customer",
        min_length=2,
        max_length=100
    )
    customer_phone: str = Field(
        ..., 
        description="Customer's phone number",
        max_length=20
    )
    items_count: int = Field(
        1, 
        description="Number of items in the order",
        gt=0,
        le=100
    )
    weight: float = Field(
        1.0, 
        description="Weight of the order in kg",
        gt=0,
        le=1000
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_input(cls, data):
        if isinstance(data, dict):
            # Проверка имени клиента
            name = data.get('customer_name')
            if isinstance(name, str) and name.strip() == '':
                raise ValueError('customer name cannot be empty')
            elif isinstance(name, str):
                data['customer_name'] = name.strip()
            
            # Проверка телефона
            phone = data.get('customer_phone')
            if phone is not None and not re.match(
                r'^\+?[0-9\s\-\(\)]{7,20}$', phone
            ):
                raise ValueError('phone number format is invalid')
        
        return data


class OrderCreate(OrderBase):
    """Schema for creating a new order."""
    location: LocationCreate = Field(
        ..., 
        description="Delivery location"
    )
    depot_id: Optional[UUID] = Field(
        None, 
        description="ID of assigned depot"
    )
    
    @model_validator(mode='after')
    def validate_location(self):
        if not self.location:
            raise ValueError('location is required for order creation')
        return self


class OrderCreateWithAddress(OrderBase):
    """Schema for creating a new order with address only (coordinates will be geocoded)."""
    address: str = Field(
        ..., 
        description="Delivery address",
        min_length=3,
        max_length=200
    )
    depot_id: Optional[UUID] = Field(
        None, 
        description="ID of assigned depot"
    )


class OrderResponse(OrderBase):
    """Schema for order responses."""
    id: UUID = Field(..., description="Order identifier")
    customer_phone: Optional[str] = Field(
        None, 
        description="Customer's phone number",
        max_length=20
    )
    location: LocationResponse = Field(..., description="Delivery location")
    status: OrderStatus = Field(..., description="Current status of the order")
    created_at: datetime = Field(..., description="Order creation timestamp")
    courier_id: Optional[UUID] = Field(
        None, description="ID of assigned courier"
    )
    depot_id: Optional[UUID] = Field(
        None, description="ID of assigned depot"
    )
    
    model_config = {"from_attributes": True}


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status."""
    status: OrderStatus = Field(..., description="New order status")
    
    @model_validator(mode='before')
    @classmethod
    def validate_status(cls, data):
        if isinstance(data, dict) and 'status' in data:
            status = data.get('status')
            allowed_values = [status.value for status in OrderStatus]
            if status not in allowed_values:
                raise ValueError(
                    f'status must be one of {", ".join(allowed_values)}'
                )
        return data


class BulkOrderCreate(BaseModel):
    """Модель для массового создания заказов."""
    
    orders: List[OrderCreate] = Field(..., description="Список заказов для создания") 