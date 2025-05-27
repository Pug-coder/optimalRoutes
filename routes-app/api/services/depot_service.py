from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional, Tuple
from uuid import UUID
import uuid

from ..models import Depot, Location, Courier, Order
from ..schemas import (
    DepotCreate, DepotCreateWithAddress, DepotResponse, LocationResponse
)
from ..services.geocoding_service import geocoding_service


class DepotService:
    """Сервис для работы с депо."""
    
    @staticmethod
    async def get_all_depots(db: AsyncSession) -> List[DepotResponse]:
        """
        Получает список всех депо.
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список депо
        """
        # Получаем все депо из базы данных
        result = await db.execute(select(Depot))
        depots = result.scalars().all()
        
        # Формируем ответ
        response_depots = []
        for depot in depots:
            # Получаем местоположение для каждого депо
            location_result = await db.execute(
                select(Location).where(Location.id == depot.location_id)
            )
            location = location_result.scalar_one_or_none()
            
            if location:
                # Создаем объект ответа
                location_response = LocationResponse(
                    id=location.id,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    address=location.address
                )
                
                depot_response = DepotResponse(
                    id=depot.id,
                    name=depot.name,
                    location=location_response
                )
                
                response_depots.append(depot_response)
        
        return response_depots
    
    @staticmethod
    async def get_depot(
        db: AsyncSession, depot_id: UUID
    ) -> Optional[DepotResponse]:
        """
        Получает информацию о депо по ID.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            Информация о депо или None, если депо не найдено
        """
        # Получаем депо из базы данных
        result = await db.execute(select(Depot).where(Depot.id == depot_id))
        depot = result.scalar_one_or_none()
        
        if not depot:
            return None
            
        # Получаем местоположение депо
        location_result = await db.execute(
            select(Location).where(Location.id == depot.location_id)
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            return None
            
        # Создаем объект ответа
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        return DepotResponse(
            id=depot.id,
            name=depot.name,
            location=location_response
        )
    
    @staticmethod
    async def create_depot(
        db: AsyncSession, 
        depot_data: DepotCreate
    ) -> Tuple[DepotResponse, Depot]:
        """
        Создает новое депо.
        
        Args:
            db: Сессия базы данных
            depot_data: Данные для создания депо
            
        Returns:
            Кортеж из ответа API и созданного депо
        """
        # Проверяем уникальность имени
        existing_depot = await DepotService._get_depot_by_name(
            db, depot_data.name
        )
        if existing_depot:
            raise ValueError(
                f"Депо с именем '{depot_data.name}' уже существует"
            )
        
        # Создаем местоположение
        location = Location(
            id=str(uuid.uuid4()),
            latitude=depot_data.location.latitude,
            longitude=depot_data.location.longitude,
            address=depot_data.location.address
        )
        
        # Добавляем местоположение в базу данных
        db.add(location)
        await db.flush()  # Выполняем, чтобы получить ID
        
        # Создаем депо
        depot = Depot(
            id=uuid.uuid4(),
            name=depot_data.name,
            location_id=location.id
        )
        
        # Добавляем депо в базу данных
        db.add(depot)
        await db.commit()  # Фиксируем изменения
        await db.refresh(depot)  # Обновляем объект из базы данных
        
        # Создаем объект ответа
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        depot_response = DepotResponse(
            id=depot.id,
            name=depot.name,
            location=location_response
        )
        
        return depot_response, depot
    
    @staticmethod
    async def create_depot_with_address(
        db: AsyncSession, 
        depot_data: DepotCreateWithAddress
    ) -> Tuple[DepotResponse, Depot]:
        """
        Создает новое депо с автоматическим геокодированием адреса.
        
        Args:
            db: Сессия базы данных
            depot_data: Данные для создания депо с адресом
            
        Returns:
            Кортеж из ответа API и созданного депо
            
        Raises:
            ValueError: Если адрес не найден или депо с таким именем уже существует
        """
        # Проверяем уникальность имени
        existing_depot = await DepotService._get_depot_by_name(
            db, depot_data.name
        )
        if existing_depot:
            raise ValueError(
                f"Депо с именем '{depot_data.name}' уже существует"
            )
        
        # Геокодируем адрес
        coordinates = await geocoding_service.geocode_address(depot_data.address)
        if not coordinates:
            raise ValueError(f"Не удалось найти координаты для адреса: {depot_data.address}")
        
        latitude, longitude = coordinates
        
        # Создаем местоположение
        location = Location(
            id=str(uuid.uuid4()),
            latitude=latitude,
            longitude=longitude,
            address=depot_data.address
        )
        
        # Добавляем местоположение в базу данных
        db.add(location)
        await db.flush()  # Выполняем, чтобы получить ID
        
        # Создаем депо
        depot = Depot(
            id=uuid.uuid4(),
            name=depot_data.name,
            location_id=location.id
        )
        
        # Добавляем депо в базу данных
        db.add(depot)
        await db.commit()  # Фиксируем изменения
        await db.refresh(depot)  # Обновляем объект из базы данных
        
        # Создаем объект ответа
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        depot_response = DepotResponse(
            id=depot.id,
            name=depot.name,
            location=location_response
        )
        
        return depot_response, depot
    
    @staticmethod
    async def get_depot_location(
        db: AsyncSession, location_id: str
    ) -> Optional[Location]:
        """
        Получает местоположение депо по ID.
        
        Args:
            db: Сессия базы данных
            location_id: ID местоположения
            
        Returns:
            Объект местоположения или None, если не найдено
        """
        result = await db.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def delete_depot(db: AsyncSession, depot_id: UUID) -> bool:
        """
        Удаляет депо.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            True, если депо было удалено, иначе False
            
        Raises:
            ValueError: Если депо не найдено или нельзя удалить
        """
        # Получаем депо напрямую из базы данных
        result = await db.execute(select(Depot).where(Depot.id == depot_id))
        depot = result.scalar_one_or_none()
        
        if not depot:
            raise ValueError(f"Depot with ID {depot_id} not found")
        
        # Проверяем, есть ли связанные курьеры
        couriers_result = await db.execute(
            select(Courier).where(Courier.depot_id == depot_id)
        )
        couriers = couriers_result.scalars().all()
        
        if couriers:
            courier_names = [courier.name for courier in couriers]
            raise ValueError(
                f"Невозможно удалить депо. К нему привязано курьеров: {len(couriers)} ({', '.join(courier_names)}). "
                f"Сначала переназначьте или удалите курьеров."
            )
        
        # Проверяем, есть ли связанные заказы
        orders_result = await db.execute(
            select(Order).where(Order.depot_id == depot_id)
        )
        orders = orders_result.scalars().all()
        
        if orders:
            raise ValueError(
                f"Невозможно удалить депо. К нему привязано заказов: {len(orders)}. "
                f"Сначала переназначьте или удалите заказы."
            )
        
        location_id = depot.location_id
        
        # Удаляем депо
        await db.execute(delete(Depot).where(Depot.id == depot_id))
        
        # Удаляем связанное местоположение
        await db.execute(delete(Location).where(Location.id == location_id))
        
        # Коммитим изменения
        await db.commit()
        
        return True
    
    @staticmethod
    async def update_depot(
        db: AsyncSession, 
        depot_id: UUID, 
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None
    ) -> Optional[Depot]:
        """
        Обновляет информацию о депо.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            name: Новое название депо
            latitude: Новая широта
            longitude: Новая долгота
            address: Новый адрес
            
        Returns:
            Обновленное депо или None, если депо не найдено
            
        Raises:
            ValueError: Если данные неверны
        """
        # Получаем депо
        depot = await DepotService.get_depot(db, depot_id)
        if not depot:
            raise ValueError(f"Depot with ID {depot_id} not found")
        
        # Обновляем название депо, если указано
        if name is not None:
            # Проверяем, что нет другого депо с таким названием
            if name != depot.name:
                existing_depot = await DepotService._get_depot_by_name(
                    db, name
                )
                if existing_depot and existing_depot.id != depot_id:
                    raise ValueError(
                        f"Depot with name '{name}' already exists"
                    )
                
                # Обновляем название
                depot.name = name
        
        # Обновляем местоположение, если указаны координаты
        if any(param is not None for param in [latitude, longitude, address]):
            # Получаем местоположение
            location = await DepotService.get_depot_location(
                db, depot.location_id
            )
            if not location:
                raise ValueError(f"Location for depot {depot_id} not found")
            
            # Обновляем координаты
            if latitude is not None:
                location.latitude = latitude
            if longitude is not None:
                location.longitude = longitude
            if address is not None:
                location.address = address
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(depot)
        
        return depot
    
    @staticmethod
    async def _get_depot_by_name(
        db: AsyncSession, name: str
    ) -> Optional[Depot]:
        """
        Внутренний метод для получения депо по названию.
        
        Args:
            db: Сессия базы данных
            name: Название депо
            
        Returns:
            Объект депо или None, если не найдено
        """
        result = await db.execute(select(Depot).where(Depot.name == name))
        return result.scalar_one_or_none() 