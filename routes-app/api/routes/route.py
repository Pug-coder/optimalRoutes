"""API-маршруты для работы с маршрутами доставки."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
import time

from ..services import RouteService, route_optimizer
from ..services import DepotService, CourierService, OrderService
from ..schemas import (
    RouteCreate, RouteResponse, RouteWithLocationsResponse, 
    OptimizationResponse, RoutePointBase
)
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from ..schemas.route import LocationResponse, RoutePointWithLocationResponse

# Создаем роутер для маршрутов
router = APIRouter()


# Модель для параметров оптимизации
class OptimizationParams(BaseModel):
    algorithm: Optional[str] = "nearest_neighbor"
    depot_id: Optional[UUID] = None


# Модель для параметров генетического алгоритма
class GeneticParams(BaseModel):
    population_size: Optional[int] = 100
    generations: Optional[int] = 100
    mutation_rate: Optional[float] = 0.1
    elite_size: Optional[int] = 20
    depot_id: Optional[UUID] = None


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


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_routes(
    params: OptimizationParams,
    db: AsyncSession = Depends(get_db)
):
    """
    Оптимизирует маршруты для доставки заказов.
    Поддерживает различные алгоритмы оптимизации:
    - nearest_neighbor: алгоритм ближайшего соседа (по умолчанию)
    - or_tools: использует OR-Tools для оптимизации
    - genetic: генетический алгоритм
    Поддерживает Multi-Depot VRP - работает со всеми складами одновременно.
    """
    try:
        start_time = time.time()
        
        # Проверяем корректность алгоритма
        valid_algorithms = ["nearest_neighbor", "or_tools", "genetic"]
        if params.algorithm not in valid_algorithms:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый алгоритм: {params.algorithm}. "
                       f"Доступные: {', '.join(valid_algorithms)}"
            )
        
        # Если указан конкретный depot_id, работаем только с ним
        if params.depot_id:
            depot = await DepotService.get_depot(db, params.depot_id)
            if not depot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Склад с ID {params.depot_id} не найден"
                )
            depots = [depot]
        else:
            # Иначе работаем со ВСЕМИ складами (Multi-Depot VRP)
            depots = await DepotService.get_all_depots(db)
            if not depots:
                raise ValueError("Нет доступных складов для оптимизации")
        
        # Получить ТОЛЬКО СВОБОДНЫХ курьеров для всех складов
        all_couriers = []
        for depot in depots:
            # Используем новый метод для получения только свободных курьеров
            couriers = await CourierService.get_available_couriers_by_depot(
                db, depot.id
            )
            all_couriers.extend(couriers)
        
        if not all_couriers:
            raise ValueError("Нет свободных курьеров для оптимизации")
        
        # Получить нераспределенные заказы
        orders = await OrderService.get_pending_orders(db)
        if not orders:
            raise ValueError("Нет заказов для оптимизации")
        
        # Преобразуем объекты в словари для оптимизатора
        # Передаём ВСЕ склады и курьеров
        depots_data = [depot.model_dump() for depot in depots]
        couriers_data = [courier.model_dump() for courier in all_couriers]
        orders_data = [order.model_dump() for order in orders]
        
        # Выбираем метод оптимизации в зависимости от алгоритма
        if len(depots) > 1:
            # Для множественных складов
            if params.algorithm == "genetic":
                optimized_routes = await (
                    route_optimizer.optimize_routes_genetic_multi_depot(
                        depots_data, orders_data, couriers_data
                    )
                )
            elif params.algorithm == "or_tools":
                # Используем правильный Multi-Depot OR-Tools
                optimized_routes = await (
                    route_optimizer._optimize_with_or_tools_multi_depot(
                        depots_data, orders_data, couriers_data
                    )
                )
            else:
                # nearest_neighbor для multi-depot
                optimized_routes = await (
                    route_optimizer.optimize_routes_multi_depot(
                        depots_data, orders_data, couriers_data, params.algorithm
                    )
                )
        else:
            # Для одного склада используем выбранный алгоритм
            optimized_routes = await route_optimizer.optimize_routes(
                depots_data[0], orders_data, couriers_data, params.algorithm
            )
        
        # Создаем маршруты в базе данных
        routes_response = []
        used_courier_ids = set()  # Отслеживаем уже использованных курьеров
        
        for route_data in optimized_routes:
            try:
                courier_id = UUID(route_data["courier_id"])
                
                # Проверяем, не использован ли уже этот курьер в текущей сессии
                if courier_id in used_courier_ids:
                    print(f"Skipping route for courier {courier_id} - "
                          f"already used in this session")
                    continue
                
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
                    courier_id=courier_id,
                    depot_id=UUID(route_data["depot_id"]),
                    total_distance=route_data["total_distance"],
                    total_load=route_data["total_load"],
                    total_weight=route_data.get("total_weight", 0.0),
                    points=points
                )
                
                route = await RouteService.create_route(db, route_create)
                routes_response.append(route)
                
                # Добавляем курьера в список использованных
                used_courier_ids.add(courier_id)
                
            except Exception as e:
                # Log error but continue with other routes
                print(f"Error creating route: {e}")
                continue
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Подсчитываем статистику
        total_distance = sum(route.total_distance for route in routes_response)
        assigned_orders = sum(len(route.points) for route in routes_response)
        total_orders = len(orders)
        
        return OptimizationResponse(
            algorithm=params.algorithm,
            routes=routes_response,
            total_distance=total_distance,
            total_orders=total_orders,
            assigned_orders=assigned_orders,
            execution_time=execution_time
        )
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


@router.post("/optimize/genetic", response_model=OptimizationResponse)
async def optimize_routes_genetic(
    params: GeneticParams = GeneticParams(),
    db: AsyncSession = Depends(get_db)
):
    """
    Оптимизирует маршруты для доставки заказов.
    Использует генетический алгоритм для оптимизации.
    Поддерживает Multi-Depot VRP - работает со всеми складами одновременно.
    """
    try:
        start_time = time.time()
        
        # Если указан конкретный depot_id, работаем только с ним
        if params.depot_id:
            depot = await DepotService.get_depot(db, params.depot_id)
            if not depot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Склад с ID {params.depot_id} не найден"
                )
            depots = [depot]
        else:
            # Иначе работаем со ВСЕМИ складами (Multi-Depot VRP)
            depots = await DepotService.get_all_depots(db)
            if not depots:
                raise ValueError("Нет доступных складов для оптимизации")
        
        # Получить ТОЛЬКО СВОБОДНЫХ курьеров для всех складов
        all_couriers = []
        for depot in depots:
            # Используем новый метод для получения только свободных курьеров
            couriers = await CourierService.get_available_couriers_by_depot(
                db, depot.id
            )
            all_couriers.extend(couriers)
        
        if not all_couriers:
            raise ValueError("Нет свободных курьеров для оптимизации")
        
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
        if len(depots) > 1:
            optimized_routes = await (
                route_optimizer.optimize_routes_genetic_multi_depot(
                    depots_data, orders_data, couriers_data, genetic_params
                )
            )
        else:
            # Для одного склада
            optimized_routes = await route_optimizer.optimize_routes_genetic(
                depots_data[0], orders_data, couriers_data, genetic_params
            )
        
        # Создаем маршруты в базе данных
        routes_response = []
        used_courier_ids = set()  # Отслеживаем уже использованных курьеров
        
        for route_data in optimized_routes:
            try:
                courier_id = UUID(route_data["courier_id"])
                
                # Проверяем, не использован ли уже этот курьер в текущей сессии
                if courier_id in used_courier_ids:
                    print(f"Skipping route for courier {courier_id} - "
                          f"already used in this session")
                    continue
                
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
                    courier_id=courier_id,
                    depot_id=UUID(route_data["depot_id"]),
                    total_distance=route_data["total_distance"],
                    total_load=route_data["total_load"],
                    total_weight=route_data.get("total_weight", 0.0),
                    points=points
                )
                
                route = await RouteService.create_route(db, route_create)
                routes_response.append(route)
                
                # Добавляем курьера в список использованных
                used_courier_ids.add(courier_id)
                
            except Exception as e:
                # Log error but continue with other routes
                print(f"Error creating route: {e}")
                continue
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Подсчитываем статистику
        total_distance = sum(route.total_distance for route in routes_response)
        assigned_orders = sum(len(route.points) for route in routes_response)
        total_orders = len(orders)
        
        return OptimizationResponse(
            algorithm="genetic",
            routes=routes_response,
            total_distance=total_distance,
            total_orders=total_orders,
            assigned_orders=assigned_orders,
            execution_time=execution_time
        )
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


@router.post("/optimize/genetic/remaining", response_model=OptimizationResponse)
async def optimize_remaining_orders_genetic(
    params: GeneticParams = GeneticParams(),
    db: AsyncSession = Depends(get_db)
):
    """
    Оптимизирует нераспределенные заказы с помощью генетического алгоритма.
    
    Этот endpoint позволяет запустить повторную оптимизацию для заказов,
    которые не были назначены курьерам при предыдущей оптимизации.
    Все курьеры считаются свободными (вернулись в депо).
    """
    try:
        start_time = time.time()
        
        # Получаем все склады
        if params.depot_id:
            depot = await DepotService.get_depot(db, params.depot_id)
            if not depot:
                raise HTTPException(
                    status_code=404,
                    detail=f"Склад с ID {params.depot_id} не найден"
                )
            depots = [depot]
        else:
            depots = await DepotService.get_all_depots(db)
            if not depots:
                raise ValueError("Нет доступных складов для оптимизации")
        
        # Получаем всех курьеров
        all_couriers = []
        for depot in depots:
            depot_couriers = await CourierService.get_couriers_by_depot(
                db, depot.id
            )
            all_couriers.extend(depot_couriers)
        
        if not all_couriers:
            raise ValueError("Нет доступных курьеров для оптимизации")
        
        # Получаем все заказы со статусом "pending"
        all_orders = await OrderService.get_pending_orders(db)
        if not all_orders:
            raise ValueError("Нет свободных заказов для оптимизации")
        
        # Получаем существующие маршруты
        existing_routes = await RouteService.get_all_routes(db)
        
        print(f"Starting remaining orders optimization:")
        print(f"  Depots: {len(depots)}")
        print(f"  Couriers: {len(all_couriers)}")
        print(f"  All pending orders: {len(all_orders)}")
        print(f"  Existing routes: {len(existing_routes)}")
        
        # Преобразуем в формат для оптимизатора
        depots_data = []
        for depot in depots:
            depot_dict = {
                "id": depot.id,
                "name": depot.name,
                "location": {
                    "latitude": depot.location.latitude,
                    "longitude": depot.location.longitude,
                    "address": depot.location.address
                }
            }
            depots_data.append(depot_dict)
        
        couriers_data = []
        for courier in all_couriers:
            courier_dict = {
                "id": courier.id,
                "name": courier.name,
                "depot_id": courier.depot_id,
                "max_capacity": courier.max_capacity,
                "max_weight": courier.max_weight,
                "max_distance": courier.max_distance
            }
            couriers_data.append(courier_dict)
        
        orders_data = []
        for order in all_orders:
            order_dict = {
                "id": order.id,
                "customer_name": order.customer_name,
                "items_count": order.items_count,
                "weight": order.weight,
                "status": order.status,
                "location": {
                    "latitude": order.location.latitude,
                    "longitude": order.location.longitude,
                    "address": order.location.address
                }
            }
            orders_data.append(order_dict)
        
        # Преобразуем существующие маршруты в нужный формат
        existing_routes_data = []
        for route in existing_routes:
            route_dict = {
                "id": str(route.id),
                "courier_id": str(route.courier_id),
                "depot_id": str(route.depot_id),
                "points": []
            }
            for point in route.points:
                route_dict["points"].append({
                    "order_id": str(point.order_id),
                    "sequence": point.sequence
                })
            existing_routes_data.append(route_dict)
        
        # Параметры генетического алгоритма
        genetic_params = {
            "population_size": params.population_size,
            "generations": params.generations,
            "mutation_rate": params.mutation_rate,
            "elite_size": params.elite_size
        }
        
        # Запускаем оптимизацию нераспределенных заказов
        optimized_routes = await route_optimizer.optimize_remaining_orders_genetic(
            depots_data, orders_data, couriers_data, existing_routes_data, genetic_params
        )
        
        print(f"Optimization completed. Generated {len(optimized_routes)} new routes")
        
        # Сохраняем новые маршруты в базу данных
        saved_routes = []
        assigned_order_ids = []
        
        for route_data in optimized_routes:
            # Создаем данные для создания маршрута
            route_create_data = RouteCreate(
                courier_id=UUID(route_data["courier_id"]),
                depot_id=UUID(route_data["depot_id"]),
                total_distance=route_data.get("total_distance", 0.0),
                total_load=route_data.get("total_load", 0),
                total_weight=route_data.get("total_weight", 0.0),
                points=[
                    RoutePointBase(
                        order_id=UUID(point["order_id"]),
                        sequence=point["sequence"]
                    )
                    for point in route_data["points"]
                ]
            )
            
            # Создаем маршрут (автоматически обновит статусы заказов)
            saved_route = await RouteService.create_route(
                db, route_create_data
            )
            saved_routes.append(saved_route)
            
            # Собираем ID назначенных заказов для статистики
            for point in route_data["points"]:
                assigned_order_ids.append(UUID(point["order_id"]))
        
        execution_time = time.time() - start_time
        
        # Подсчитываем статистику
        total_distance = sum(route.total_distance for route in saved_routes)
        total_orders_assigned = len(assigned_order_ids)
        
        # Получаем общую статистику по всем маршрутам в системе
        all_current_routes = await RouteService.get_all_routes(db)
        total_system_distance = sum(route.total_distance for route in all_current_routes)
        total_system_assigned = len(all_orders) - len([order for order in all_orders if order.status == 'pending'])
        
        print(f"Remaining orders optimization completed:")
        print(f"  New routes created: {len(saved_routes)}")
        print(f"  Additional orders assigned: {total_orders_assigned}")
        print(f"  Total distance of new routes: {total_distance:.2f} km")
        print(f"  Execution time: {execution_time:.2f} seconds")
        
        return OptimizationResponse(
            algorithm="genetic (remaining orders)",
            total_routes=len(saved_routes),  # Только новые маршруты
            total_distance=total_distance,   # Только расстояние новых маршрутов
            assigned_orders=total_orders_assigned,  # Только новые назначенные заказы
            total_orders=len(all_orders),
            available_couriers=len(all_couriers),
            available_depots=len(depots),
            execution_time=execution_time,
            routes=saved_routes  # Только новые маршруты
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error in remaining orders optimization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при оптимизации нераспределенных заказов: {str(e)}"
        ) 