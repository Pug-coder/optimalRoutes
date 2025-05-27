"""Схемы для геокодирования адресов."""

from pydantic import BaseModel, Field
from typing import Optional


class GeocodeRequest(BaseModel):
    """Запрос на геокодирование адреса."""
    address: str = Field(
        ..., 
        description="Адрес для геокодирования",
        min_length=3,
        max_length=200
    )


class GeocodeResponse(BaseModel):
    """Ответ с координатами адреса."""
    latitude: Optional[float] = Field(
        None, 
        description="Широта",
        ge=-90.0,
        le=90.0
    )
    longitude: Optional[float] = Field(
        None, 
        description="Долгота",
        ge=-180.0,
        le=180.0
    )
    address: str = Field(..., description="Исходный адрес")
    found: bool = Field(..., description="Найден ли адрес")


class ReverseGeocodeRequest(BaseModel):
    """Запрос на обратное геокодирование."""
    latitude: float = Field(
        ..., 
        description="Широта",
        ge=-90.0,
        le=90.0
    )
    longitude: float = Field(
        ..., 
        description="Долгота",
        ge=-180.0,
        le=180.0
    )


class ReverseGeocodeResponse(BaseModel):
    """Ответ с адресом по координатам."""
    address: Optional[str] = Field(None, description="Найденный адрес")
    latitude: float = Field(..., description="Широта")
    longitude: float = Field(..., description="Долгота")
    found: bool = Field(..., description="Найден ли адрес") 