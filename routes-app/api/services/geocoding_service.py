"""Сервис для геокодирования адресов."""

import asyncio
from typing import Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging

logger = logging.getLogger(__name__)


class GeocodingService:
    """Сервис для получения координат по адресу."""
    
    def __init__(self):
        """Инициализация геокодера."""
        self.geolocator = Nominatim(
            user_agent="optimal-routes-app",
            timeout=10
        )
    
    async def geocode_address(
        self, address: str
    ) -> Optional[Tuple[float, float]]:
        """
        Получает координаты по адресу.
        
        Args:
            address: Адрес для геокодирования
            
        Returns:
            Кортеж (широта, долгота) или None, если адрес не найден
        """
        if not address or not address.strip():
            return None
            
        try:
            # Выполняем геокодирование в отдельном потоке
            loop = asyncio.get_event_loop()
            location = await loop.run_in_executor(
                None, 
                self._geocode_sync, 
                address.strip()
            )
            
            if location:
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"Адрес не найден: {address}")
                return None
                
        except GeocoderTimedOut:
            logger.error(f"Таймаут при геокодировании адреса: {address}")
            return None
        except GeocoderServiceError as e:
            logger.error(
                f"Ошибка сервиса геокодирования для адреса {address}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при геокодировании адреса {address}: {e}"
            )
            return None
    
    def _geocode_sync(self, address: str):
        """
        Синхронное геокодирование адреса.
        
        Args:
            address: Адрес для геокодирования
            
        Returns:
            Объект Location или None
        """
        try:
            return self.geolocator.geocode(address)
        except Exception as e:
            logger.error(f"Ошибка при синхронном геокодировании: {e}")
            return None
    
    async def reverse_geocode(
        self, latitude: float, longitude: float
    ) -> Optional[str]:
        """
        Получает адрес по координатам (обратное геокодирование).
        
        Args:
            latitude: Широта
            longitude: Долгота
            
        Returns:
            Адрес или None, если не найден
        """
        try:
            # Выполняем обратное геокодирование в отдельном потоке
            loop = asyncio.get_event_loop()
            location = await loop.run_in_executor(
                None, 
                self._reverse_geocode_sync, 
                latitude, 
                longitude
            )
            
            if location:
                return location.address
            else:
                logger.warning(f"Адрес не найден для координат: {latitude}, {longitude}")
                return None
                
        except GeocoderTimedOut:
            logger.error(f"Таймаут при обратном геокодировании: {latitude}, {longitude}")
            return None
        except GeocoderServiceError as e:
            logger.error(f"Ошибка сервиса при обратном геокодировании: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обратном геокодировании: {e}")
            return None
    
    def _reverse_geocode_sync(self, latitude: float, longitude: float):
        """
        Синхронное обратное геокодирование.
        
        Args:
            latitude: Широта
            longitude: Долгота
            
        Returns:
            Объект Location или None
        """
        try:
            return self.geolocator.reverse((latitude, longitude))
        except Exception as e:
            logger.error(f"Ошибка при синхронном обратном геокодировании: {e}")
            return None


# Глобальный экземпляр сервиса
geocoding_service = GeocodingService() 