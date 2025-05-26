from pydantic import BaseModel, Field, model_validator
from typing import Optional
from uuid import UUID
import re


class CourierBase(BaseModel):
    """Base courier schema."""
    name: str = Field(
        ..., 
        description="Name of the courier",
        min_length=2,
        max_length=100
    )
    phone: Optional[str] = Field(
        None, 
        description="Courier's phone number",
        max_length=20
    )
    max_capacity: int = Field(
        10, 
        description="Maximum carrying capacity",
        gt=0,
        le=100
    )
    max_distance: float = Field(
        50.0,
        description="Maximum travel distance in kilometers",
        gt=0,
        le=1000
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_input(cls, data):
        # Валидация телефона
        if isinstance(data, dict):
            # Проверка телефона
            phone = data.get('phone')
            if phone is not None:
                # Если телефон пустая строка, устанавливаем None
                if isinstance(phone, str) and phone.strip() == '':
                    data['phone'] = None
                elif not re.match(r'^\+?[0-9\s\-\(\)]{7,20}$', phone):
                    raise ValueError('phone number format is invalid')
            
            # Проверка имени
            name = data.get('name')
            if name is not None:
                if isinstance(name, str) and name.strip() == '':
                    raise ValueError('name cannot be empty')
                elif isinstance(name, str):
                    data['name'] = name.strip()
        
        return data


class CourierCreate(CourierBase):
    """Schema for creating a new courier."""
    depot_id: UUID = Field(
        ..., 
        description="ID of the depot the courier belongs to"
    )


class CourierUpdate(BaseModel):
    """Schema for updating a courier."""
    name: Optional[str] = Field(
        None, 
        description="Name of the courier",
        min_length=2,
        max_length=100
    )
    phone: Optional[str] = Field(
        None, 
        description="Courier's phone number",
        max_length=20
    )
    max_capacity: Optional[int] = Field(
        None, 
        description="Maximum carrying capacity",
        gt=0,
        le=100
    )
    max_distance: Optional[float] = Field(
        None,
        description="Maximum travel distance in kilometers",
        gt=0,
        le=1000
    )
    depot_id: Optional[UUID] = Field(
        None, 
        description="ID of the depot the courier belongs to"
    )
    
    @model_validator(mode='before')
    @classmethod
    def validate_input(cls, data):
        # Валидация телефона
        if isinstance(data, dict):
            # Проверка телефона
            phone = data.get('phone')
            if phone is not None:
                # Если телефон пустая строка, устанавливаем None
                if isinstance(phone, str) and phone.strip() == '':
                    data['phone'] = None
                elif not re.match(r'^\+?[0-9\s\-\(\)]{7,20}$', phone):
                    raise ValueError('phone number format is invalid')
            
            # Проверка имени
            name = data.get('name')
            if name is not None:
                if isinstance(name, str) and name.strip() == '':
                    raise ValueError('name cannot be empty')
                elif isinstance(name, str):
                    data['name'] = name.strip()
        
        return data


class CourierResponse(CourierBase):
    """Schema for courier responses."""
    id: UUID = Field(..., description="Courier identifier")
    depot_id: UUID = Field(
        ..., 
        description="ID of the depot the courier belongs to"
    )
    
    model_config = {"from_attributes": True} 