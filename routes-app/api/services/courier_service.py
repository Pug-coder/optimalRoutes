from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from typing import List, Optional
from uuid import UUID
import uuid
import re

from ..models import Courier, Depot
from ..schemas import CourierCreate, CourierResponse


class CourierService:
    """Сервис для работы с курьерами."""
    
    @staticmethod
    async def create_courier(
        db: AsyncSession, 
        courier_data: CourierCreate
    ) -> CourierResponse:
        """
        Создает нового курьера.
        
        Args:
            db: Сессия базы данных
            courier_data: Данные для создания курьера
            
        Returns:
            Созданный курьер
            
        Raises:
            ValueError: Если данные неверны
        """
        # Проверяем существование депо
        depot = await CourierService._get_depot(db, courier_data.depot_id)
        if not depot:
            raise ValueError(
                f"Депо с ID {courier_data.depot_id} не найдено"
            )
        
        # Валидация телефона
        if courier_data.phone:
            CourierService._validate_phone(courier_data.phone)
        
        # Создаем курьера
        courier = Courier(
            id=uuid.uuid4(),
            name=courier_data.name,
            phone=courier_data.phone,
            max_capacity=courier_data.max_capacity,
            depot_id=courier_data.depot_id
        )
        
        # Добавляем запись в базу данных
        db.add(courier)
        await db.commit()
        await db.refresh(courier)
        
        # Формируем ответ
        return CourierResponse(
            id=courier.id,
            name=courier.name,
            phone=courier.phone,
            max_capacity=courier.max_capacity,
            depot_id=courier.depot_id
        )
    
    @staticmethod
    async def get_courier(
        db: AsyncSession, 
        courier_id: UUID
    ) -> Optional[CourierResponse]:
        """
        Получает информацию о курьере по ID.
        
        Args:
            db: Сессия базы данных
            courier_id: ID курьера
            
        Returns:
            Информация о курьере или None, если курьер не найден
        """
        # Получаем курьера из базы данных
        result = await db.execute(
            select(Courier).where(Courier.id == courier_id)
        )
        courier = result.scalar_one_or_none()
        
        # Если курьер не найден, возвращаем None
        if not courier:
            return None
        
        # Формируем ответ
        return CourierResponse(
            id=courier.id,
            name=courier.name,
            phone=courier.phone,
            max_capacity=courier.max_capacity,
            depot_id=courier.depot_id
        )
    
    @staticmethod
    async def get_all_couriers(db: AsyncSession) -> List[CourierResponse]:
        """
        Получает список всех курьеров.
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список курьеров
        """
        # Получаем все записи о курьерах
        result = await db.execute(select(Courier))
        couriers = result.scalars().all()
        
        # Формируем список ответов
        return [
            CourierResponse(
                id=courier.id,
                name=courier.name,
                phone=courier.phone,
                max_capacity=courier.max_capacity,
                depot_id=courier.depot_id
            )
            for courier in couriers
        ]
    
    @staticmethod
    async def get_couriers_by_depot(
        db: AsyncSession, 
        depot_id: UUID
    ) -> List[CourierResponse]:
        """
        Получает всех курьеров, связанных с указанным депо.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            Список курьеров
        """
        result = await db.execute(
            select(Courier).where(Courier.depot_id == depot_id)
        )
        couriers = result.scalars().all()
        
        # Преобразуем модели в объекты ответа
        return [
            CourierResponse(
                id=courier.id,
                name=courier.name,
                phone=courier.phone,
                max_capacity=courier.max_capacity,
                depot_id=courier.depot_id
            )
            for courier in couriers
        ]
    
    @staticmethod
    async def delete_courier(
        db: AsyncSession, 
        courier_id: UUID
    ) -> bool:
        """
        Удаляет курьера.
        
        Args:
            db: Сессия базы данных
            courier_id: ID курьера
            
        Returns:
            True, если курьер был удален, иначе False
            
        Raises:
            ValueError: Если курьер не найден или нельзя удалить
        """
        # Получаем курьера напрямую из базы данных
        result = await db.execute(select(Courier).where(Courier.id == courier_id))
        courier = result.scalar_one_or_none()
        
        if not courier:
            raise ValueError(f"Courier with ID {courier_id} not found")
        
        # Автоматически отменяем все назначенные заказы
        from ..models import Order
        from ..models.order import OrderStatus
        
        orders_result = await db.execute(
            select(Order).where(Order.courier_id == courier_id)
        )
        assigned_orders = orders_result.scalars().all()
        
        # Отменяем назначение заказов
        for order in assigned_orders:
            order.status = OrderStatus.PENDING
            order.courier_id = None
        
        # Удаляем курьера
        await db.execute(delete(Courier).where(Courier.id == courier_id))
        
        # Коммитим изменения
        await db.commit()
        
        return True
    
    @staticmethod
    async def update_courier(
        db: AsyncSession, 
        courier_id: UUID, 
        name: Optional[str] = None,
        phone: Optional[str] = None,
        max_capacity: Optional[int] = None,
        depot_id: Optional[UUID] = None
    ) -> Optional[CourierResponse]:
        """
        Обновляет информацию о курьере.
        
        Args:
            db: Сессия базы данных
            courier_id: ID курьера
            name: Новое имя курьера
            phone: Новый телефон
            max_capacity: Новая максимальная емкость
            depot_id: Новое ID депо
            
        Returns:
            Обновленный курьер или None, если курьер не найден
            
        Raises:
            ValueError: Если данные неверны
        """
        # Получаем курьера напрямую из базы данных
        result = await db.execute(select(Courier).where(Courier.id == courier_id))
        courier = result.scalar_one_or_none()
        
        if not courier:
            raise ValueError(f"Courier with ID {courier_id} not found")
        
        # Обновляем имя, если указано
        if name is not None:
            courier.name = name
        
        # Обновляем телефон, если указан
        if phone is not None:
            CourierService._validate_phone(phone)
            courier.phone = phone
        
        # Обновляем максимальную емкость, если указана
        if max_capacity is not None:
            if max_capacity <= 0:
                raise ValueError("Max capacity must be positive")
            courier.max_capacity = max_capacity
        
        # Обновляем депо, если указано
        if depot_id is not None:
            depot = await CourierService._get_depot(db, depot_id)
            if not depot:
                raise ValueError(f"Depot with ID {depot_id} not found")
            
            # Если курьер переназначается в другое депо, отменяем все его заказы
            if courier.depot_id != depot_id:
                from ..models import Order
                from ..models.order import OrderStatus
                
                orders_result = await db.execute(
                    select(Order).where(Order.courier_id == courier_id)
                )
                assigned_orders = orders_result.scalars().all()
                
                # Отменяем назначение заказов
                for order in assigned_orders:
                    order.status = OrderStatus.PENDING
                    order.courier_id = None
            
            courier.depot_id = depot_id
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(courier)
        
        # Возвращаем CourierResponse
        return CourierResponse(
            id=courier.id,
            name=courier.name,
            phone=courier.phone,
            max_capacity=courier.max_capacity,
            depot_id=courier.depot_id
        )
    
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
    def _validate_phone(phone: str) -> None:
        """
        Валидирует телефонный номер.
        
        Args:
            phone: Телефонный номер для валидации
            
        Raises:
            ValueError: Если телефон неверного формата
        """
        if not re.match(r'^\+?[0-9\s\-\(\)]{7,20}$', phone):
            raise ValueError("Неверный формат телефонного номера") 