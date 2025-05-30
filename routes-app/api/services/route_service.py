from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime

from ..models import Route, RoutePoint, Order, Courier, Depot
from ..schemas import (
    RouteCreate, RoutePointBase, RouteResponse, RoutePointResponse
)
from ..models.order import OrderStatus


class RouteService:
    """Сервис для работы с маршрутами."""
    
    @staticmethod
    async def create_route(
        db: AsyncSession, 
        route_data: RouteCreate
    ) -> RouteResponse:
        """
        Создает новый маршрут.
        
        Args:
            db: Сессия базы данных
            route_data: Данные для создания маршрута
            
        Returns:
            Созданный маршрут
            
        Raises:
            ValueError: Если данные неверны
        """
        # Валидация дополнительных бизнес-правил
        
        # Проверяем существование курьера
        courier = await RouteService._get_courier(db, route_data.courier_id)
        if not courier:
            raise ValueError(
                f"Courier with ID {route_data.courier_id} not found"
            )
        
        # Проверяем существование депо
        depot = await RouteService._get_depot(db, route_data.depot_id)
        if not depot:
            raise ValueError(f"Depot with ID {route_data.depot_id} not found")
        
        # Проверяем, что курьер принадлежит указанному депо
        if courier.depot_id != route_data.depot_id:
            raise ValueError(
                "Courier must belong to the specified depot"
            )
        
        # Проверяем общий вес маршрута
        if (len(route_data.points) > 0 and
                not await RouteService._validate_route_capacity(
                    db, route_data.points, courier.max_capacity
                )):
            raise ValueError(
                f"Route exceeds courier capacity of {courier.max_capacity}"
            )
        
        # Создаем маршрут
        route = Route(
            id=uuid.uuid4(),
            courier_id=route_data.courier_id,
            depot_id=route_data.depot_id,
            total_distance=route_data.total_distance,
            total_load=route_data.total_load,
            total_weight=route_data.total_weight,
            created_at=datetime.utcnow()
        )
        
        # Добавляем маршрут в базу данных
        db.add(route)
        await db.commit()
        await db.refresh(route)
        
        # Создаем точки маршрута
        route_points = []
        for point_data in route_data.points:
            # Проверяем существование заказа
            order = await RouteService._get_order(db, point_data.order_id)
            if not order:
                raise ValueError(
                    f"Order with ID {point_data.order_id} not found"
                )
            
            # Проверяем, что заказ в правильном статусе
            if order.status != OrderStatus.PENDING:
                raise ValueError(
                    f"Order {order.id} must be in PENDING status "
                    f"to add to route"
                )
            
            # Создаем точку маршрута
            route_point = RoutePoint(
                id=uuid.uuid4(),
                route_id=route.id,
                order_id=point_data.order_id,
                sequence=point_data.sequence,
                estimated_arrival=point_data.estimated_arrival
            )
            
            # Обновляем статус заказа
            order.status = OrderStatus.ASSIGNED
            order.courier_id = route.courier_id
            
            route_points.append(route_point)
            db.add(route_point)
        
        # Сохраняем изменения
        await db.commit()
        
        # Обновляем маршрут с точками
        await db.refresh(route)
        
        response = RouteResponse(
            id=route.id,
            courier_id=route.courier_id,
            depot_id=route.depot_id,
            total_distance=route.total_distance,
            total_load=route.total_load,
            total_weight=route.total_weight,
            created_at=route.created_at,
            points=[
                RoutePointResponse(
                    id=point.id,
                    order_id=point.order_id,
                    sequence=point.sequence,
                    estimated_arrival=point.estimated_arrival
                )
                for point in route_points
            ]
        )
        
        return response
    
    @staticmethod
    async def get_route(
        db: AsyncSession, 
        route_id: UUID
    ) -> Optional[RouteResponse]:
        """
        Получает информацию о маршруте по ID.
        
        Args:
            db: Сессия базы данных
            route_id: ID маршрута
            
        Returns:
            Информация о маршруте или None, если маршрут не найден
        """
        # Получаем маршрут из БД
        result = await db.execute(select(Route).where(Route.id == route_id))
        route = result.scalar_one_or_none()
        
        if not route:
            return None
            
        # Получаем все точки маршрута
        points_result = await db.execute(
            select(RoutePoint)
            .where(RoutePoint.route_id == route.id)
            .order_by(RoutePoint.sequence)
        )
        points = points_result.scalars().all()
        
        # Создаем объекты точек маршрута для ответа
        point_responses = []
        for point in points:
            point_response = RoutePointResponse(
                id=point.id,
                order_id=point.order_id,
                sequence=point.sequence,
                estimated_arrival=point.estimated_arrival
            )
            point_responses.append(point_response)
        
        # Создаем объект маршрута для ответа
        return RouteResponse(
            id=route.id,
            courier_id=route.courier_id,
            depot_id=route.depot_id,
            total_distance=route.total_distance,
            total_load=route.total_load,
            total_weight=route.total_weight,
            created_at=route.created_at,
            points=point_responses
        )
    
    @staticmethod
    async def get_all_routes(db: AsyncSession) -> List[RouteResponse]:
        """
        Получает список всех маршрутов.
        
        Args:
            db: Сессия базы данных
            
        Returns:
            Список маршрутов
        """
        # Получаем все маршруты из БД
        result = await db.execute(select(Route))
        routes = result.scalars().all()
        
        # Формируем ответ
        response_routes = []
        
        for route in routes:
            # Получаем все точки маршрута
            points_result = await db.execute(
                select(RoutePoint)
                .where(RoutePoint.route_id == route.id)
                .order_by(RoutePoint.sequence)
            )
            points = points_result.scalars().all()
            
            # Создаем объекты точек маршрута для ответа
            point_responses = []
            for point in points:
                point_response = RoutePointResponse(
                    id=point.id,
                    order_id=point.order_id,
                    sequence=point.sequence,
                    estimated_arrival=point.estimated_arrival
                )
                point_responses.append(point_response)
            
            # Создаем объект маршрута для ответа
            route_response = RouteResponse(
                id=route.id,
                courier_id=route.courier_id,
                depot_id=route.depot_id,
                total_distance=route.total_distance,
                total_load=route.total_load,
                total_weight=route.total_weight,
                created_at=route.created_at,
                points=point_responses
            )
            
            response_routes.append(route_response)
        
        return response_routes
    
    @staticmethod
    async def get_routes_by_courier(
        db: AsyncSession, 
        courier_id: UUID
    ) -> List[Route]:
        """
        Получает маршруты по курьеру.
        
        Args:
            db: Сессия базы данных
            courier_id: ID курьера
            
        Returns:
            Список маршрутов для указанного курьера
        """
        result = await db.execute(
            select(Route).where(Route.courier_id == courier_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_routes_by_depot(
        db: AsyncSession, 
        depot_id: UUID
    ) -> List[Route]:
        """
        Получает маршруты по депо.
        
        Args:
            db: Сессия базы данных
            depot_id: ID депо
            
        Returns:
            Список маршрутов для указанного депо
        """
        result = await db.execute(
            select(Route).where(Route.depot_id == depot_id)
        )
        return result.scalars().all()
    
    @staticmethod
    async def delete_route(
        db: AsyncSession, 
        route_id: UUID
    ) -> bool:
        """
        Удаляет маршрут.
        
        Args:
            db: Сессия базы данных
            route_id: ID маршрута
            
        Returns:
            True, если маршрут был удален, иначе False
            
        Raises:
            ValueError: Если маршрут не найден или нельзя удалить
        """
        # Получаем маршрут
        route = await RouteService.get_route(db, route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        
        # Получаем все точки маршрута
        result = await db.execute(
            select(RoutePoint).where(RoutePoint.route_id == route_id)
        )
        route_points = result.scalars().all()
        
        # Обновляем статусы заказов
        for point in route_points:
            # Получаем заказ
            order = await RouteService._get_order(db, point.order_id)
            if order and order.status == OrderStatus.ASSIGNED:
                # Возвращаем заказ в статус ожидания
                order.status = OrderStatus.PENDING
                order.courier_id = None
        
        # Удаляем точки маршрута
        await db.execute(
            delete(RoutePoint).where(RoutePoint.route_id == route_id)
        )
        
        # Удаляем маршрут
        await db.execute(delete(Route).where(Route.id == route_id))
        
        # Коммитим изменения
        await db.commit()
        
        return True
    
    @staticmethod
    async def update_route_points(
        db: AsyncSession, 
        route_id: UUID, 
        points: List[RoutePointBase]
    ) -> Optional[Route]:
        """
        Обновляет точки маршрута.
        
        Args:
            db: Сессия базы данных
            route_id: ID маршрута
            points: Новый список точек маршрута
            
        Returns:
            Обновленный маршрут или None, если маршрут не найден
            
        Raises:
            ValueError: Если данные неверны
        """
        # Получаем маршрут
        route = await RouteService.get_route(db, route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        
        # Получаем курьера для проверки вместимости
        courier = await RouteService._get_courier(db, route.courier_id)
        if not courier:
            raise ValueError(f"Courier with ID {route.courier_id} not found")
        
        # Проверяем вместимость
        if (len(points) > 0 and 
            not await RouteService._validate_route_capacity(
                db, points, courier.max_capacity
            )):
            raise ValueError(
                f"Route exceeds courier capacity of {courier.max_capacity}"
            )
        
        # Получаем текущие точки маршрута
        result = await db.execute(
            select(RoutePoint).where(RoutePoint.route_id == route_id)
        )
        current_points = result.scalars().all()
        
        # Собираем ID заказов из текущих точек
        current_order_ids = {point.order_id for point in current_points}
        
        # Собираем ID заказов из новых точек
        new_order_ids = {point.order_id for point in points}
        
        # Заказы, которые нужно удалить из маршрута
        to_remove = current_order_ids - new_order_ids
        
        # Заказы, которые нужно добавить в маршрут
        to_add = new_order_ids - current_order_ids
        
        # Обновляем статусы заказов, которые удаляются из маршрута
        for order_id in to_remove:
            order = await RouteService._get_order(db, order_id)
            if order and order.status == OrderStatus.ASSIGNED:
                order.status = OrderStatus.PENDING
                order.courier_id = None
        
        # Проверяем и обновляем статусы заказов, которые добавляются в маршрут
        for order_id in to_add:
            order = await RouteService._get_order(db, order_id)
            if not order:
                raise ValueError(f"Order with ID {order_id} not found")
            
            if order.status != OrderStatus.PENDING:
                raise ValueError(
                    f"Order {order.id} must be in PENDING status to add to route"
                )
            
            order.status = OrderStatus.ASSIGNED
            order.courier_id = route.courier_id
        
        # Удаляем все текущие точки маршрута
        await db.execute(
            delete(RoutePoint).where(RoutePoint.route_id == route_id)
        )
        
        # Создаем новые точки маршрута
        for point_data in points:
            route_point = RoutePoint(
                id=uuid.uuid4(),
                route_id=route.id,
                order_id=point_data.order_id,
                sequence=point_data.sequence,
                estimated_arrival=point_data.estimated_arrival
            )
            db.add(route_point)
        
        # Обновляем данные маршрута
        total_load = await RouteService._calculate_route_load(db, points)
        route.total_load = total_load
        
        # Здесь можно добавить перерасчет общего расстояния маршрута
        # если есть такая функциональность
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(route)
        
        return route
    
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
    async def _get_depot(
        db: AsyncSession, 
        depot_id: UUID
    ) -> Optional[Depot]:
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
    async def _get_order(
        db: AsyncSession, 
        order_id: UUID
    ) -> Optional[Order]:
        """
        Внутренний метод для получения заказа по ID.
        
        Args:
            db: Сессия базы данных
            order_id: ID заказа
            
        Returns:
            Объект заказа или None, если не найден
        """
        result = await db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _validate_route_capacity(
        db: AsyncSession, 
        points: List[RoutePointBase], 
        max_capacity: int
    ) -> bool:
        """
        Проверяет, что общий вес заказов не превышает вместимость курьера.
        
        Args:
            db: Сессия базы данных
            points: Список точек маршрута
            max_capacity: Максимальная вместимость курьера
            
        Returns:
            True, если вместимость не превышена, иначе False
        """
        total_items = await RouteService._calculate_route_load(db, points)
        return total_items <= max_capacity
    
    @staticmethod
    async def _calculate_route_load(
        db: AsyncSession, 
        points: List[RoutePointBase]
    ) -> int:
        """
        Вычисляет общую нагрузку для маршрута.
        
        Args:
            db: Сессия базы данных
            points: Точки маршрута
            
        Returns:
            Общая нагрузка маршрута
        """
        total_load = 0
        for point in points:
            order = await RouteService._get_order(db, point.order_id)
            if order:
                total_load += order.items_count
        return total_load
    
    @staticmethod
    async def reset_all_routes(db: AsyncSession) -> None:
        """
        Удаляет все маршруты и сбрасывает статусы заказов на "ожидание".
        
        Args:
            db: Сессия базы данных
        """
        # Получаем все маршруты
        result = await db.execute(select(Route))
        routes = result.scalars().all()
        
        for route in routes:
            # Получаем точки маршрута
            points_result = await db.execute(
                select(RoutePoint).where(RoutePoint.route_id == route.id)
            )
            points = points_result.scalars().all()
            
            # Обновляем статусы заказов
            for point in points:
                # Получаем заказ
                order_result = await db.execute(
                    select(Order).where(Order.id == point.order_id)
                )
                order = order_result.scalar_one_or_none()
                
                if order:
                    # Сбрасываем статус заказа на "ожидание"
                    order.status = OrderStatus.PENDING
                    order.courier_id = None
            
            # Удаляем точки маршрута
            await db.execute(
                delete(RoutePoint).where(RoutePoint.route_id == route.id)
            )
        
        # Удаляем все маршруты
        await db.execute(delete(Route))
        
        # Фиксируем изменения
        await db.commit() 