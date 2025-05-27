from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update, func
from typing import List, Optional, Tuple, Dict
from uuid import UUID
import uuid
import re
from datetime import datetime
import random

from ..models import Order, Location, Depot, Courier
from ..schemas import (
    OrderCreate, OrderCreateWithAddress, OrderStatusUpdate, OrderResponse, 
    LocationResponse, LocationCreate
)
from ..models.order import OrderStatus
from ..services.geocoding_service import geocoding_service


class OrderService:
    """Сервис для работы с заказами."""
    
    @staticmethod
    async def create_order_with_address(
        db: AsyncSession, 
        order_data: OrderCreateWithAddress
    ) -> Tuple[OrderResponse, Order]:
        """
        Создает новый заказ с автоматическим геокодированием адреса.
        
        Args:
            db: Сессия базы данных
            order_data: Данные для создания заказа с адресом
            
        Returns:
            Кортеж из ответа API и созданного заказа
            
        Raises:
            ValueError: Если адрес не найден или депо не существует
        """
        # Проверяем депо, если указано
        if order_data.depot_id:
            depot = await OrderService._get_depot(db, order_data.depot_id)
            if not depot:
                raise ValueError(f"Депо с ID {order_data.depot_id} не найдено")
        
        # Геокодируем адрес
        coordinates = await geocoding_service.geocode_address(order_data.address)
        if not coordinates:
            raise ValueError(f"Не удалось найти координаты для адреса: {order_data.address}")
        
        latitude, longitude = coordinates
        
        # Создаем местоположение
        location = Location(
            id=str(uuid.uuid4()),
            latitude=latitude,
            longitude=longitude,
            address=order_data.address
        )
        
        # Добавляем местоположение в БД
        db.add(location)
        await db.flush()
        
        # Создаем заказ
        order = Order(
            id=uuid.uuid4(),
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            location_id=location.id,
            items_count=order_data.items_count,
            weight=order_data.weight,
            status=OrderStatus.PENDING,
            depot_id=order_data.depot_id,
            created_at=datetime.now()
        )
        
        # Добавляем заказ в БД
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        # Создаем объект для ответа
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        order_response = OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items_count=order.items_count,
            weight=order.weight,
            status=order.status,
            created_at=order.created_at,
            courier_id=order.courier_id,
            depot_id=order.depot_id,
            location=location_response
        )
        
        return order_response, order
    
    @staticmethod
    async def create_bulk_orders(
        db: AsyncSession, 
        orders_data: List[OrderCreate]
    ) -> List[OrderResponse]:
        """
        Создает массово новые заказы.
        
        Args:
            db: Сессия базы данных
            orders_data: Список данных для создания заказов
            
        Returns:
            Список созданных заказов
        """
        created_orders = []
        
        for order_data in orders_data:
            # Проверяем депо, если указано
            if order_data.depot_id:
                depot = await OrderService._get_depot(db, order_data.depot_id)
                if not depot:
                    raise ValueError(f"Депо с ID {order_data.depot_id} не найдено")
            
            # Создаем местоположение
            location = Location(
                id=str(uuid.uuid4()),
                latitude=order_data.location.latitude,
                longitude=order_data.location.longitude,
                address=order_data.location.address
            )
            
            # Добавляем местоположение в БД
            db.add(location)
            await db.flush()
            
            # Создаем заказ
            order = Order(
                id=uuid.uuid4(),
                customer_name=order_data.customer_name,
                customer_phone=order_data.customer_phone,
                location_id=location.id,
                items_count=order_data.items_count,
                weight=order_data.weight,
                status=OrderStatus.PENDING,
                depot_id=order_data.depot_id,
                created_at=datetime.now()
            )
            
            # Добавляем заказ в БД
            db.add(order)
            created_orders.append((order, location))
        
        # Фиксируем все изменения в БД
        await db.commit()
        
        # Обновляем объекты из БД
        for order, _ in created_orders:
            await db.refresh(order)
        
        # Формируем ответ
        response_orders = []
        for order, location in created_orders:
            location_response = LocationResponse(
                id=location.id,
                latitude=location.latitude,
                longitude=location.longitude,
                address=location.address
            )
            
            order_response = OrderResponse(
                id=order.id,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone,
                items_count=order.items_count,
                weight=order.weight,
                status=order.status,
                created_at=order.created_at,
                courier_id=order.courier_id,
                depot_id=order.depot_id,
                location=location_response
            )
            
            response_orders.append(order_response)
        
        return response_orders
    
    @staticmethod
    async def generate_random_orders(
        db: AsyncSession, 
        count: int,
        min_lat: float = 55.7, 
        max_lat: float = 55.8,
        min_lng: float = 37.5, 
        max_lng: float = 37.7
    ) -> List[OrderResponse]:
        """
        Генерирует случайные заказы в указанном географическом районе.
        
        Args:
            db: Сессия базы данных
            count: Количество заказов для генерации
            min_lat: Минимальная широта
            max_lat: Максимальная широта
            min_lng: Минимальная долгота
            max_lng: Максимальная долгота
            
        Returns:
            Список созданных случайных заказов
        """
        orders_data = []
        
        for i in range(count):
            # Генерируем случайное местоположение
            lat = min_lat + random.random() * (max_lat - min_lat)
            lng = min_lng + random.random() * (max_lng - min_lng)
            
            # Создаем данные заказа
            order_data = OrderCreate(
                customer_name=f"Клиент {i+1}",
                customer_phone=f"+7-{random.randint(900, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                items_count=random.randint(1, 5),
                weight=round(0.1 + random.random() * 9.9, 1),
                location=LocationCreate(
                    latitude=lat,
                    longitude=lng,
                    address=f"Тестовый адрес {i+1}"
                )
            )
            
            orders_data.append(order_data)
        
        # Создаем заказы массово
        return await OrderService.create_bulk_orders(db, orders_data)
    
    @staticmethod
    async def count_orders(
        db: AsyncSession, 
        assigned: Optional[bool] = None
    ) -> int:
        """
        Подсчитывает количество заказов с возможностью фильтрации.
        
        Args:
            db: Сессия базы данных
            assigned: Если True, подсчитывает только назначенные заказы,
                     если False - только неназначенные, если None - все заказы
            
        Returns:
            Количество заказов
        """
        query = select(func.count()).select_from(Order)
        
        # Фильтрация по статусу назначения
        if assigned is not None:
            if assigned:
                # Заказы с назначенным курьером
                query = query.where(Order.courier_id.is_not(None))
            else:
                # Заказы без назначенного курьера
                query = query.where(Order.courier_id.is_(None))
        
        result = await db.execute(query)
        return result.scalar_one()
    
    @staticmethod
    async def get_all_orders(db: AsyncSession) -> List[OrderResponse]:
        """
        Получает список всех заказов.
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список заказов
        """
        # Получаем все заказы из БД
        result = await db.execute(select(Order))
        orders = result.scalars().all()
        
        # Формируем ответ
        response_orders = []
        
        for order in orders:
            # Получаем местоположение
            location_result = await db.execute(
                select(Location).where(Location.id == order.location_id)
            )
            location = location_result.scalar_one_or_none()
            
            if location:
                # Создаем объект местоположения
                location_response = LocationResponse(
                    id=location.id,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    address=location.address
                )
                
                # Создаем объект заказа для ответа
                order_response = OrderResponse(
                    id=order.id,
                    customer_name=order.customer_name,
                    customer_phone=order.customer_phone,
                    items_count=order.items_count,
                    weight=order.weight,
                    status=order.status,
                    created_at=order.created_at,
                    courier_id=order.courier_id,
                    depot_id=order.depot_id,
                    location=location_response
                )
                
                response_orders.append(order_response)
        
        return response_orders
    
    @staticmethod
    async def get_order(db: AsyncSession, order_id: UUID) -> Optional[OrderResponse]:
        """
        Получает информацию о заказе по ID.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            
        Returns:
            Информация о заказе или None, если заказ не найден
        """
        # Получаем заказ из БД
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            return None
            
        # Получаем местоположение
        location_result = await db.execute(
            select(Location).where(Location.id == order.location_id)
        )
        location = location_result.scalar_one_or_none()
        
        if not location:
            return None
            
        # Создаем объект местоположения
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        # Формируем ответ
        return OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items_count=order.items_count,
            weight=order.weight,
            status=order.status,
            created_at=order.created_at,
            courier_id=order.courier_id,
            depot_id=order.depot_id,
            location=location_response
        )
    
    @staticmethod
    async def create_order(
        db: AsyncSession, 
        order_data: OrderCreate
    ) -> Tuple[OrderResponse, Order]:
        """
        Создает новый заказ.
        
        Args:
            db: Сессия базы данных
            order_data: Данные для создания заказа
            
        Returns:
            Кортеж из ответа API и созданного заказа
        """
        # Проверяем депо, если указано
        if order_data.depot_id:
            depot = await OrderService._get_depot(db, order_data.depot_id)
            if not depot:
                raise ValueError(f"Депо с ID {order_data.depot_id} не найдено")
        
        # Создаем местоположение
        location = Location(
            id=str(uuid.uuid4()),
            latitude=order_data.location.latitude,
            longitude=order_data.location.longitude,
            address=order_data.location.address
        )
        
        # Добавляем местоположение в БД
        db.add(location)
        await db.flush()
        
        # Создаем заказ
        order = Order(
            id=uuid.uuid4(),
            customer_name=order_data.customer_name,
            customer_phone=order_data.customer_phone,
            location_id=location.id,
            items_count=order_data.items_count,
            weight=order_data.weight,
            status=OrderStatus.PENDING,
            depot_id=order_data.depot_id,
            created_at=datetime.now()
        )
        
        # Добавляем заказ в БД
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        # Создаем объект для ответа
        location_response = LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address
        )
        
        order_response = OrderResponse(
            id=order.id,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            items_count=order.items_count,
            weight=order.weight,
            status=order.status,
            created_at=order.created_at,
            courier_id=order.courier_id,
            depot_id=order.depot_id,
            location=location_response
        )
        
        return order_response, order
    
    @staticmethod
    async def update_order_status(
        db: AsyncSession,
        order_id: UUID,
        status_update: OrderStatusUpdate
    ) -> Optional[OrderResponse]:
        """
        Обновляет статус заказа.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            status_update: Данные для обновления статуса
            
        Returns:
            Обновленный заказ или None, если заказ не найден
        """
        # Получаем заказ
        order = await OrderService.get_order(db, order_id)
        if not order:
            return None
            
        # Получаем оригинальный объект для обновления
        result = await db.execute(select(Order).where(Order.id == order_id))
        db_order = result.scalar_one_or_none()
        
        if not db_order:
            return None
            
        # Проверяем корректность перехода статуса
        OrderService._validate_status_transition(
            db_order.status, 
            status_update.status
        )
        
        # Обновляем статус
        db_order.status = status_update.status
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(db_order)
        
        # Обновляем объект ответа с новыми данными
        updated_order = await OrderService.get_order(db, order_id)
        return updated_order
    
    @staticmethod
    async def get_order_location(
        db: AsyncSession, 
        location_id: str
    ) -> Optional[Location]:
        """
        Получает местоположение заказа по ID.
        
        Args:
            db: Сессия базы данных
            location_id: ID местоположения
            
        Returns:
            Объект местоположения или None, если не найден
        """
        result = await db.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_orders_by_status(
        db: AsyncSession, 
        status: OrderStatus
    ) -> List[Order]:
        """
        Получает заказы по статусу.
        
        Args:
            db: Сессия базы данных
            status: Статус заказа
            
        Returns:
            Список заказов с указанным статусом
        """
        result = await db.execute(select(Order).where(Order.status == status))
        return result.scalars().all()
    
    @staticmethod
    async def get_orders_by_depot(
        db: AsyncSession, 
        depot_id: UUID
    ) -> List[Order]:
        """
        Получает заказы по депо.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            Список заказов, связанных с указанным депо
        """
        result = await db.execute(
            select(Order).where(Order.depot_id == depot_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_pending_orders(db: AsyncSession) -> List[OrderResponse]:
        """
        Получает список всех заказов со статусом "ожидание".
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список заказов со статусом "ожидание"
        """
        # Получаем все ожидающие заказы из БД
        result = await db.execute(
            select(Order).where(Order.status == OrderStatus.PENDING)
        )
        orders = result.scalars().all()
        
        # Формируем ответ
        response_orders = []
        for order in orders:
            # Получаем местоположение заказа
            location_result = await db.execute(
                select(Location).where(Location.id == order.location_id)
            )
            location = location_result.scalar_one_or_none()
            
            if location:
                # Создаем объект местоположения для ответа
                location_response = LocationResponse(
                    id=location.id,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    address=location.address
                )
                
                # Создаем объект заказа для ответа
                order_response = OrderResponse(
                    id=order.id,
                    customer_name=order.customer_name,
                    customer_phone=order.customer_phone,
                    items_count=order.items_count,
                    weight=order.weight,
                    status=order.status,
                    created_at=order.created_at,
                    location=location_response,
                    courier_id=order.courier_id,
                    depot_id=order.depot_id
                )
                
                response_orders.append(order_response)
        
        return response_orders
    
    @staticmethod
    async def assign_order_to_courier(
        db: AsyncSession, 
        order_id: UUID, 
        courier_id: UUID
    ) -> Optional[Order]:
        """
        Назначает заказ курьеру.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            courier_id: ID курьера
            
        Returns:
            Обновленный заказ или None, если заказ не найден
            
        Raises:
            ValueError: Если данные неверны
        """
        # Получаем заказ
        order = await OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        
        # Получаем курьера
        courier = await OrderService._get_courier(db, courier_id)
        if not courier:
            raise ValueError(f"Courier with ID {courier_id} not found")
        
        # Проверяем, что заказ и курьер принадлежат одному депо
        if order.depot_id != courier.depot_id:
            raise ValueError(
                "Order and courier must belong to the same depot"
            )
        
        # Проверяем статус заказа
        if order.status != OrderStatus.PENDING:
            raise ValueError(
                f"Cannot assign order in status {order.status}"
            )
        
        # Назначаем курьера и меняем статус
        order.courier_id = courier_id
        order.status = OrderStatus.ASSIGNED
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(order)
        
        return order
    
    @staticmethod
    async def assign_order_to_depot(
        db: AsyncSession, 
        order_id: UUID, 
        depot_id: UUID
    ) -> Optional[Order]:
        """
        Назначает заказ депо.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            depot_id: ID депо
            
        Returns:
            Обновленный заказ или None, если заказ не найден
            
        Raises:
            ValueError: Если данные неверны
        """
        # Получаем заказ
        order = await OrderService.get_order(db, order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        
        # Получаем депо
        depot = await OrderService._get_depot(db, depot_id)
        if not depot:
            raise ValueError(f"Depot with ID {depot_id} not found")
        
        # Проверяем статус заказа
        if order.status != OrderStatus.PENDING:
            raise ValueError(
                f"Cannot reassign order in status {order.status}"
            )
        
        # Назначаем депо
        order.depot_id = depot_id
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(order)
        
        return order
    
    @staticmethod
    async def delete_order(db: AsyncSession, order_id: UUID) -> bool:
        """
        Удаляет заказ.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            
        Returns:
            True, если заказ был удален, иначе False
            
        Raises:
            ValueError: Если заказ не найден или нельзя удалить
        """
        # Получаем заказ напрямую из базы данных
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        
        # Если заказ назначен курьеру, автоматически отменяем назначение
        if order.status == OrderStatus.ASSIGNED:
            order.status = OrderStatus.CANCELLED
            order.courier_id = None
            await db.commit()
            await db.refresh(order)
        
        # Проверяем, что заказ можно удалить
        if order.status not in [OrderStatus.PENDING, OrderStatus.CANCELLED]:
            raise ValueError(
                f"Cannot delete order in status {order.status}. Only PENDING and CANCELLED orders can be deleted."
            )
        
        location_id = order.location_id
        
        # Удаляем заказ
        await db.execute(delete(Order).where(Order.id == order_id))
        
        # Удаляем связанное местоположение
        await db.execute(delete(Location).where(Location.id == location_id))
        
        # Коммитим изменения
        await db.commit()
        
        return True
    
    @staticmethod
    async def delete_all_orders(db: AsyncSession) -> int:
        """
        Удаляет все заказы.
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Количество удаленных заказов
        """
        # Получаем все заказы
        result = await db.execute(select(Order))
        orders = result.scalars().all()
        
        if not orders:
            return 0
        
        # Собираем ID всех местоположений для удаления
        location_ids = [order.location_id for order in orders if order.location_id]
        
        # Удаляем все заказы
        await db.execute(delete(Order))
        
        # Удаляем все связанные местоположения
        if location_ids:
            await db.execute(delete(Location).where(Location.id.in_(location_ids)))
        
        # Коммитим изменения
        await db.commit()
        
        return len(orders)
    
    @staticmethod
    async def _get_depot(db: AsyncSession, depot_id: UUID) -> Optional[Depot]:
        """
        Внутренний метод для получения депо по ID.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            Объект депо или None, если не найден
        """
        result = await db.execute(select(Depot).where(Depot.id == depot_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _get_courier(
        db: AsyncSession, 
        courier_id: UUID
    ) -> Optional[Courier]:
        """
        Внутренний метод для получения курьера по ID.
        
        Args:
            db: Сессия базы данных
            courier_id: ID курьера
            
        Returns:
            Объект курьера или None, если не найден
        """
        result = await db.execute(
            select(Courier).where(Courier.id == courier_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _validate_phone(phone: str) -> None:
        """
        Валидирует телефонный номер.
        
        Args:
            phone: Телефонный номер для валидации
            
        Raises:
            ValueError: Если телефон неверного формата
        """
        if not re.match(r'^\+?[0-9\s\-\(\)]{7,20}$', phone):
            raise ValueError("Phone number format is invalid")
    
    @staticmethod
    def _validate_status_transition(
        current_status: OrderStatus, 
        new_status: OrderStatus
    ) -> None:
        """
        Проверяет корректность перехода статуса заказа.
        
        Args:
            current_status: Текущий статус
            new_status: Новый статус
            
        Raises:
            ValueError: Если переход статуса недопустим
        """
        # Словарь допустимых переходов статусов
        allowed_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.ASSIGNED, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.ASSIGNED: [
                OrderStatus.IN_TRANSIT, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.IN_TRANSIT: [
                OrderStatus.DELIVERED, 
                OrderStatus.CANCELLED
            ],
            OrderStatus.DELIVERED: [],  # Конечный статус
            OrderStatus.CANCELLED: [OrderStatus.PENDING]  # Можно восстановить
        }
        
        # Проверяем допустимость перехода
        if new_status not in allowed_transitions.get(current_status, []):
            raise ValueError(
                f"Недопустимый переход статуса с {current_status} на {new_status}"
            ) 