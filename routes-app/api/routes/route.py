"""API-маршруты для работы с маршрутами доставки."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from ..services import RouteService, route_optimizer
from ..services import DepotService, CourierService, OrderService
from ..schemas import RouteCreate, RouteResponse
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas.route import RouteWithLocationsResponse, LocationResponse, RoutePointWithLocationResponse

# Создаем роутер для маршрутов
router = APIRouter()


# Модель для параметров генетического алгоритма
class GeneticParams(BaseModel):
    population_size: Optional[int] = 100
    generations: Optional[int] = 100
    mutation_rate: Optional[float] = 0.1
    elite_size: Optional[int] = 20


@router.get("/", response_model=List[RouteResponse])
async def get_all_routes(db: AsyncSession = Depends(get_db)):
    """Получить список всех маршрутов."""
    try:
        routes = await RouteService.get_all_routes(db)
        return routes
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении списка маршрутов: {str(e)}"
        )


@router.get("/with-locations", response_model=List[RouteWithLocationsResponse])
async def get_routes_with_locations(db: AsyncSession = Depends(get_db)):
    """Получить все маршруты с полными данными о локациях."""
    try:
        # Получаем все маршруты
        routes = await RouteService.get_all_routes(db)
        
        if not routes:
            return []
        
        # Преобразуем каждый маршрут, добавляя координаты
        routes_with_locations = []
        
        for route in routes:
            # Получаем данные о депо
            depot = await DepotService.get_depot(db, route.depot_id)
            if not depot or not depot.location:
                continue
                
            depot_location = LocationResponse(
                id=depot.location.id,
                latitude=depot.location.latitude,
                longitude=depot.location.longitude,
                address=depot.location.address
            )
            
            # Получаем данные о точках заказов
            points_with_locations = []
            for point in route.points:
                order = await OrderService.get_order(db, point.order_id)
                if not order or not order.location:
                    continue
                    
                order_location = LocationResponse(
                    id=order.location.id,
                    latitude=order.location.latitude,
                    longitude=order.location.longitude,
                    address=order.location.address
                )
                
                point_with_location = RoutePointWithLocationResponse(
                    id=point.id,
                    order_id=point.order_id,
                    sequence=point.sequence,
                    estimated_arrival=point.estimated_arrival,
                    order_location=order_location,
                    customer_name=order.customer_name
                )
                points_with_locations.append(point_with_location)
            
            # Создаем маршрут с координатами
            route_with_locations = RouteWithLocationsResponse(
                id=route.id,
                courier_id=route.courier_id,
                depot_id=route.depot_id,
                depot_location=depot_location,
                total_distance=route.total_distance,
                total_load=route.total_load,
                created_at=route.created_at,
                points=points_with_locations
            )
            routes_with_locations.append(route_with_locations)
        
        return routes_with_locations
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении маршрутов с локациями: {str(e)}"
        )


@router.post("/", response_model=RouteResponse)
async def create_route(
    route_data: RouteCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новый маршрут."""
    try:
        route = await RouteService.create_route(db, route_data)
        return route
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании маршрута: {str(e)}"
        )


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о маршруте по ID."""
    route = await RouteService.get_route(db, route_id)
    if not route:
        raise HTTPException(
            status_code=404,
            detail=f"Маршрут с ID {route_id} не найден"
        )
    return route


@router.post("/optimize", response_model=List[RouteResponse])
async def optimize_routes(
    depot_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Оптимизирует маршруты для доставки заказов.
    Использует алгоритм OR-Tools для оптимизации.
    Поддерживает Multi-Depot VRP - работает со всеми складами одновременно.
    """
    try:
        # Если указан конкретный depot_id, работаем только с ним
        if depot_id:
            depot = await DepotService.get_depot(db, depot_id)
            if not depot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Склад с ID {depot_id} не найден"
                )
            depots = [depot]
        else:
            # Иначе работаем со ВСЕМИ складами (Multi-Depot VRP)
            depots = await DepotService.get_all_depots(db)
            if not depots:
                raise ValueError("Нет доступных складов для оптимизации")
        
        # Получить ВСЕХ курьеров для всех складов
        all_couriers = []
        for depot in depots:
            couriers = await CourierService.get_couriers_by_depot(db, depot.id)
            all_couriers.extend(couriers)
        
        if not all_couriers:
            raise ValueError("Нет доступных курьеров для оптимизации")
        
        # Получить нераспределенные заказы
        orders = await OrderService.get_pending_orders(db)
        if not orders:
            raise ValueError("Нет заказов для оптимизации")
        
        # Преобразуем объекты в словари для оптимизатора
        # Передаём ВСЕ склады и курьеров
        depots_data = [depot.model_dump() for depot in depots]
        couriers_data = [courier.model_dump() for courier in all_couriers]
        orders_data = [order.model_dump() for order in orders]
        
        # Вызываем оптимизатор с множественными складами
        optimized_routes = await route_optimizer.optimize_routes_multi_depot(
            depots_data, orders_data, couriers_data
        )
        
        # Создаем маршруты в базе данных
        routes_response = []
        for route_data in optimized_routes:
            try:
                # Create points list with validated UUIDs
                points = []
                for point in route_data["points"]:
                    # Make sure order_id is a valid UUID
                    try:
                        order_id = UUID(point["order_id"])
                        points.append({
                            "order_id": order_id,
                            "sequence": point["sequence"],
                            "estimated_arrival": None
                        })
                    except (ValueError, TypeError):
                        # Log error but continue with valid points
                        print(f"Invalid order_id format: {point['order_id']}")
                        continue
                
                # Only proceed if we have valid points
                if not points:
                    continue
                
                route_create = RouteCreate(
                    courier_id=UUID(route_data["courier_id"]),
                    depot_id=UUID(route_data["depot_id"]),
                    total_distance=route_data["total_distance"],
                    total_load=route_data["total_load"],
                    points=points
                )
                
                route = await RouteService.create_route(db, route_create)
                routes_response.append(route)
            except Exception as e:
                # Log error but continue with other routes
                print(f"Error creating route: {e}")
                continue
        
        return routes_response
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при оптимизации маршрутов: {str(e)}"
        )


@router.post("/optimize/genetic", response_model=List[RouteResponse])
async def optimize_routes_genetic(
    params: GeneticParams = GeneticParams(),
    depot_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Оптимизирует маршруты для доставки заказов.
    Использует генетический алгоритм для оптимизации.
    Поддерживает Multi-Depot VRP - работает со всеми складами одновременно.
    """
    try:
        # Если указан конкретный depot_id, работаем только с ним
        if depot_id:
            depot = await DepotService.get_depot(db, depot_id)
            if not depot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Склад с ID {depot_id} не найден"
                )
            depots = [depot]
        else:
            # Иначе работаем со ВСЕМИ складами (Multi-Depot VRP)
            depots = await DepotService.get_all_depots(db)
            if not depots:
                raise ValueError("Нет доступных складов для оптимизации")
        
        # Получить ВСЕХ курьеров для всех складов
        all_couriers = []
        for depot in depots:
            couriers = await CourierService.get_couriers_by_depot(db, depot.id)
            all_couriers.extend(couriers)
        
        if not all_couriers:
            raise ValueError("Нет доступных курьеров для оптимизации")
        
        # Получить нераспределенные заказы
        orders = await OrderService.get_pending_orders(db)
        if not orders:
            raise ValueError("Нет заказов для оптимизации")
        
        # Преобразуем объекты в словари для оптимизатора
        # Передаём ВСЕ склады и курьеров
        depots_data = [depot.model_dump() for depot in depots]
        couriers_data = [courier.model_dump() for courier in all_couriers]
        orders_data = [order.model_dump() for order in orders]
        
        # Подготовка параметров
        genetic_params = {
            "population_size": params.population_size,
            "generations": params.generations,
            "mutation_rate": params.mutation_rate,
            "elite_size": params.elite_size
        }
        
        # Вызываем генетический оптимизатор с множественными складами
        optimized_routes = await route_optimizer.\
            optimize_routes_genetic_multi_depot(
                depots_data, orders_data, couriers_data, genetic_params
            )
        
        # Создаем маршруты в базе данных
        routes_response = []
        for route_data in optimized_routes:
            try:
                # Create points list with validated UUIDs
                points = []
                for point in route_data["points"]:
                    # Make sure order_id is a valid UUID
                    try:
                        order_id = UUID(point["order_id"])
                        points.append({
                            "order_id": order_id,
                            "sequence": point["sequence"],
                            "estimated_arrival": None
                        })
                    except (ValueError, TypeError):
                        # Log error but continue with valid points
                        print(f"Invalid order_id format: {point['order_id']}")
                        continue
                
                # Only proceed if we have valid points
                if not points:
                    continue
                    
                route_create = RouteCreate(
                    courier_id=UUID(route_data["courier_id"]),
                    depot_id=UUID(route_data["depot_id"]),
                    total_distance=route_data["total_distance"],
                    total_load=route_data["total_load"],
                    points=points
                )
                
                route = await RouteService.create_route(db, route_create)
                routes_response.append(route)
            except Exception as e:
                # Log error but continue with other routes
                print(f"Error creating route: {e}")
                continue
        
        return routes_response
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при оптимизации маршрутов: {str(e)}"
        )


@router.post("/reset", status_code=204)
async def reset_routes(db: AsyncSession = Depends(get_db)):
    """Удаляет все существующие маршруты и сбрасывает статусы заказов."""
    try:
        await RouteService.reset_all_routes(db)
        return None
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при сбросе маршрутов: {str(e)}"
        ) 