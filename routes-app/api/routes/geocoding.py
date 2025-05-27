"""API-маршруты для геокодирования адресов."""

from fastapi import APIRouter, HTTPException
from ..schemas.geocoding import (
    GeocodeRequest, 
    GeocodeResponse, 
    ReverseGeocodeRequest, 
    ReverseGeocodeResponse
)
from ..services.geocoding_service import geocoding_service

# Создаем роутер для геокодирования
router = APIRouter()


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode_address(request: GeocodeRequest):
    """
    Получить координаты по адресу.
    
    Args:
        request: Запрос с адресом для геокодирования
        
    Returns:
        Координаты адреса или информация о том, что адрес не найден
    """
    try:
        coordinates = await geocoding_service.geocode_address(request.address)
        
        if coordinates:
            latitude, longitude = coordinates
            return GeocodeResponse(
                latitude=latitude,
                longitude=longitude,
                address=request.address,
                found=True
            )
        else:
            return GeocodeResponse(
                latitude=None,
                longitude=None,
                address=request.address,
                found=False
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при геокодировании адреса: {str(e)}"
        )


@router.post("/reverse-geocode", response_model=ReverseGeocodeResponse)
async def reverse_geocode_coordinates(request: ReverseGeocodeRequest):
    """
    Получить адрес по координатам.
    
    Args:
        request: Запрос с координатами для обратного геокодирования
        
    Returns:
        Адрес по координатам или информация о том, что адрес не найден
    """
    try:
        address = await geocoding_service.reverse_geocode(
            request.latitude, 
            request.longitude
        )
        
        return ReverseGeocodeResponse(
            address=address,
            latitude=request.latitude,
            longitude=request.longitude,
            found=address is not None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обратном геокодировании: {str(e)}"
        ) 