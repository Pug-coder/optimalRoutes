"""
Сервис оптимизации маршрутов.
Этот модуль содержит реализацию оптимизатора маршрутов для API.
"""

from typing import List, Dict, Any, Optional
import uuid
import numpy as np
import requests
import time

from ..models import Location

try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    OR_TOOLS_AVAILABLE = True
except ImportError:
    OR_TOOLS_AVAILABLE = False
    print("OR-Tools not available. Install with: pip install ortools")


class RouteOptimizer:
    """Оптимизатор маршрутов для API."""
    
    def __init__(self):
        """Инициализация оптимизатора маршрутов."""
        self.use_real_roads = False  # Отключаем OSRM для стабильной работы
        self.osrm_api_url = "https://router.project-osrm.org/table/v1/driving/"
    
    async def optimize_routes(
        self, 
        depot_data: Dict[str, Any],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]],
        algorithm: str = "nearest_neighbor"
    ) -> List[Dict[str, Any]]:
        """
        Выполняет оптимизацию маршрутов.
        
        Args:
            depot_data: Данные о депо
            orders: Список заказов для оптимизации
            couriers: Список доступных курьеров
            algorithm: Алгоритм оптимизации 
                ("nearest_neighbor", "or_tools", "genetic")
            
        Returns:
            Список оптимизированных маршрутов
        """
        if not orders or not couriers or not depot_data:
            return []
        
        # Выбираем алгоритм оптимизации
        if algorithm == "or_tools" and OR_TOOLS_AVAILABLE:
            return await self._optimize_with_or_tools(
                depot_data, orders, couriers
            )
        elif algorithm == "genetic":
            return await self.optimize_routes_genetic(
                depot_data, orders, couriers
            )
        else:
            # По умолчанию используем алгоритм ближайшего соседа
            return await self._optimize_with_nearest_neighbor(
                depot_data, orders, couriers
            )
    
    async def _optimize_with_nearest_neighbor(
        self, 
        depot_data: Dict[str, Any],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Оптимизация маршрутов алгоритмом ближайшего соседа.
        Использует справедливое распределение заказов между курьерами.
        """
        # Создаем список локаций для расчета матрицы расстояний
        locations = []
        
        # Добавляем депо как первую локацию
        depot_location = self._create_location_from_dict(
            depot_data.get("location", {})
        )
        if not depot_location:
            return self._simple_distribution(
                depot_data.get("id"), orders, couriers
            )
        
        locations.append(depot_location)
        
        # Добавляем локации заказов
        order_locations = {}
        for order in orders:
            order_location = self._create_location_from_dict(
                order.get("location", {})
            )
            if order_location:
                locations.append(order_location)
                order_locations[str(order["id"])] = len(locations) - 1
        
        # Если нет локаций заказов, возвращаем простое распределение
        if not order_locations:
            return self._simple_distribution(
                depot_data.get("id"), orders, couriers
            )
        
        # Рассчитываем матрицу расстояний
        distance_matrix = self._compute_distance_matrix(locations)
        
        # НОВЫЙ АЛГОРИТМ: Справедливое распределение заказов
        routes = []
        orders_copy = orders.copy()
        
        # Сортируем заказы по расстоянию от депо (ближайшие первыми)
        sorted_orders = []
        for order in orders_copy:
            order_id = str(order["id"])
            if order_id in order_locations:
                order_idx = order_locations[order_id]
                distance = distance_matrix[0][order_idx]
                sorted_orders.append((order, distance))
        
        sorted_orders.sort(key=lambda x: x[1])
        
        # Создаем словарь для отслеживания маршрутов курьеров
        courier_routes = {}
        for courier in couriers:
            courier_routes[courier["id"]] = {
                "orders": [],
                "current_load": 0,
                "courier": courier
            }
        
        # Распределяем заказы по принципу "round-robin" с проверками
        courier_index = 0
        
        for order, order_distance in sorted_orders:
            assigned = False
            attempts = 0
            
            # Пытаемся назначить заказ, начиная с текущего курьера
            while not assigned and attempts < len(couriers):
                courier = couriers[courier_index]
                courier_id = courier["id"]
                route_info = courier_routes[courier_id]
                
                order_load = order.get("items_count", 1)
                courier_capacity = courier.get("max_capacity", 10)
                courier_max_distance = courier.get("max_distance", 50.0)
                
                # Проверяем ограничения по грузоподъемности
                if route_info["current_load"] + order_load <= courier_capacity:
                    # Временно добавляем заказ для проверки расстояния
                    temp_orders = route_info["orders"] + [order]
                    
                    # Проверяем ограничения по расстоянию
                    temp_optimized = self._optimize_route_order(
                        temp_orders, depot_location, distance_matrix, 
                        order_locations
                    )
                    
                    if temp_optimized["total_distance"] <= courier_max_distance:
                        # Назначаем заказ этому курьеру
                        route_info["orders"].append(order)
                        route_info["current_load"] += order_load
                        assigned = True
                        print(f"Заказ {order['id']} назначен курьеру {courier['name']} "
                              f"(груз: {route_info['current_load']}/{courier_capacity}, "
                              f"расст: {temp_optimized['total_distance']:.2f}/{courier_max_distance})")
                
                # Переходим к следующему курьеру
                courier_index = (courier_index + 1) % len(couriers)
                attempts += 1
            
            if not assigned:
                print(f"⚠️ Заказ {order['id']} не удалось назначить ни одному курьеру")
        
        # Создаем маршруты для курьеров, у которых есть заказы
        for courier_id, route_info in courier_routes.items():
            if route_info["orders"]:
                courier = route_info["courier"]
                
                # Оптимизируем порядок заказов
                optimized_route = self._optimize_route_order(
                    route_info["orders"], depot_location, distance_matrix, 
                    order_locations
                )
                
                # Создаем маршрут
                route = {
                    "id": str(uuid.uuid4()),
                    "courier_id": str(courier["id"]),
                    "depot_id": str(depot_data.get("id")),
                    "total_distance": optimized_route["total_distance"],
                    "total_load": route_info["current_load"],
                    "points": []
                }
                
                # Добавляем точки маршрута
                for j, order in enumerate(optimized_route["orders"]):
                    order_id = order["id"]
                    if not isinstance(order_id, str):
                        order_id = str(order_id)
                    
                    route["points"].append({
                        "order_id": order_id,
                        "sequence": j
                    })
                    
                routes.append(route)
                
                print(f"Маршрут создан для {courier['name']}: "
                      f"{len(route_info['orders'])} заказов, "
                      f"{route_info['current_load']} груза, "
                      f"{optimized_route['total_distance']:.2f} км")
            
        return routes
    
    async def _optimize_with_or_tools(
        self, 
        depot_data: Dict[str, Any],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Оптимизация маршрутов с использованием OR-Tools.
        """
        if not OR_TOOLS_AVAILABLE:
            print("OR-Tools not available, falling back to nearest neighbor")
            return await self._optimize_with_nearest_neighbor(
                depot_data, orders, couriers
            )
        
        # Создаем список локаций
        locations = []
        
        # Добавляем депо как первую локацию
        depot_location = self._create_location_from_dict(
            depot_data.get("location", {})
        )
        if not depot_location:
            return self._simple_distribution(
                depot_data.get("id"), orders, couriers
            )
        
        locations.append(depot_location)
        
        # Добавляем локации заказов
        order_locations = {}
        for order in orders:
            order_location = self._create_location_from_dict(
                order.get("location", {})
            )
            if order_location:
                locations.append(order_location)
                order_locations[str(order["id"])] = len(locations) - 1
        
        if not order_locations:
            return self._simple_distribution(
                depot_data.get("id"), orders, couriers
            )
        
        # Рассчитываем матрицу расстояний
        distance_matrix = self._compute_distance_matrix(locations)
        
        # Преобразуем в целые числа для OR-Tools (умножаем на 1000)
        distance_matrix_int = (distance_matrix * 1000).astype(int)
        
        # Создаем модель OR-Tools
        manager = pywrapcp.RoutingIndexManager(
            len(locations), len(couriers), 0
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # Функция расчета расстояния
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix_int[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(
            distance_callback
        )
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Добавляем ограничения по грузоподъемности
        demands = [0]  # Депо не имеет спроса
        for order in orders:
            order_id = str(order["id"])
            if order_id in order_locations:
                demands.append(order.get("items_count", 1))
        
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(
            demand_callback
        )
        
        # Собираем все грузоподъемности курьеров в один список
        vehicle_capacities = []
        for courier in couriers:
            capacity = courier.get("max_capacity", 10)
            vehicle_capacities.append(capacity)
        
        # Добавляем одно измерение с ограничениями по грузоподъемности для всех курьеров
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            vehicle_capacities,  # список грузоподъемностей для всех курьеров
            True,  # start cumul to zero
            'Capacity'
        )
        
        # Добавляем ограничения по расстоянию
        max_distance = int(
            max(
                courier.get("max_distance", 50.0) * 1000
                for courier in couriers
            )
        )
        routing.AddDimension(
            transit_callback_index,
            0,  # no slack
            max_distance,  # maximum distance
            True,  # start cumul to zero
            'Distance'
        )
        
        # Настройки поиска
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 30
        
        # Решаем задачу
        solution = routing.SolveWithParameters(search_parameters)
        
        if not solution:
            print("OR-Tools couldn't find solution, using nearest neighbor")
            return await self._optimize_with_nearest_neighbor(
                depot_data, orders, couriers
            )
        
        # Извлекаем маршруты из решения
        routes = []
        for vehicle_id in range(len(couriers)):
            route_orders = []
            index = routing.Start(vehicle_id)
            route_distance = 0
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                if node_index > 0:  # Пропускаем депо
                    # Находим заказ по индексу локации
                    for order in orders:
                        order_id = str(order["id"])
                        order_in_locations = (
                            order_id in order_locations and 
                            order_locations[order_id] == node_index
                        )
                        if order_in_locations:
                            route_orders.append(order)
                            break
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            # Создаем маршрут, если есть заказы
            if route_orders:
                route = {
                    "id": str(uuid.uuid4()),
                    "courier_id": str(couriers[vehicle_id]["id"]),
                    "depot_id": str(depot_data.get("id")),
                    "total_distance": route_distance / 1000.0,  # Обратно в км
                    "total_load": sum(
                        order.get("items_count", 1) for order in route_orders
                    ),
                    "points": []
                }
                
                # Добавляем точки маршрута
                for j, order in enumerate(route_orders):
                    order_id = order["id"]
                    if not isinstance(order_id, str):
                        order_id = str(order_id)
                    
                    route["points"].append({
                        "order_id": order_id,
                        "sequence": j
                    })
                
                routes.append(route)
        
        return routes
    
    def _simple_distribution(
        self, 
        depot_id: str, 
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Простое распределение заказов между курьерами.
        
        Args:
            depot_id: ID депо
            orders: Список заказов для распределения
            couriers: Список доступных курьеров
            
        Returns:
            Список маршрутов
        """
        routes = []
        
        # Равномерно распределить заказы между курьерами
        orders_per_courier = max(1, len(orders) // len(couriers))
        
        for i, courier in enumerate(couriers):
            # Определить заказы для этого курьера
            start_idx = i * orders_per_courier
            end_idx = min(start_idx + orders_per_courier, len(orders))
            courier_orders = orders[start_idx:end_idx]
            
            if not courier_orders:
                continue
                
            # Создаем маршрут
            route = {
                "id": str(uuid.uuid4()),
                "courier_id": str(courier["id"]),
                "depot_id": str(depot_id),
                "total_distance": 0.0,
                "total_load": sum(
                    order.get("items_count", 1) for order in courier_orders
                ),
                "points": []
            }
            
            # Добавляем точки маршрута
            for j, order in enumerate(courier_orders):
                order_id = order["id"]
                # Убедимся, что order_id строка
                if not isinstance(order_id, str):
                    order_id = str(order_id)
                
                route["points"].append({
                    "order_id": order_id,
                    "sequence": j
                })
                
            routes.append(route)
            
        return routes
    
    def _create_location_from_dict(
        self, location_dict: Dict[str, Any]
    ) -> Optional[Location]:
        """
        Создает объект Location из словаря.
        
        Args:
            location_dict: Словарь с данными локации
            
        Returns:
            Объект Location или None, если данные некорректны
        """
        if not location_dict:
            return None
            
        try:
            return Location(
                id=str(uuid.uuid4()),
                latitude=location_dict.get("latitude"),
                longitude=location_dict.get("longitude"),
                address=location_dict.get("address", "")
            )
        except Exception:
            return None
    
    def _compute_distance_matrix(
        self, locations: List[Location]
    ) -> np.ndarray:
        """
        Вычисляет матрицу расстояний между всеми локациями.
        
        Args:
            locations: Список локаций
            
        Returns:
            Матрица расстояний
        """
        if not self.use_real_roads:
            # Используем прямые расстояния
            size = len(locations)
            matrix = np.zeros((size, size), dtype=np.float64)
            
            for i in range(size):
                for j in range(size):
                    if i != j:
                        matrix[i, j] = locations[i].distance_to(locations[j])
            
            return matrix
        else:
            # Используем OSRM для получения реальных расстояний по дорогам
            return self._compute_osrm_distance_matrix(locations)
    
    def _compute_osrm_distance_matrix(
        self, locations: List[Location]
    ) -> np.ndarray:
        """
        Вычисляет матрицу расстояний используя OSRM API.
        
        Args:
            locations: Список локаций
            
        Returns:
            Матрица расстояний
        """
        size = len(locations)
        matrix = np.zeros((size, size), dtype=np.float64)
        
        try:
            # Максимальное количество местоположений в одном запросе
            batch_size = 100
            
            # Если меньше точек чем макс размер пакета, делаем один запрос
            if size <= batch_size:
                return self._get_osrm_matrix_batch(locations)
            
            # Иначе разбиваем на несколько запросов
            for i in range(0, size, batch_size):
                batch_end = min(i + batch_size, size)
                
                for j in range(0, size, batch_size):
                    sub_batch_end = min(j + batch_size, size)
                    
                    source_locations = locations[i:batch_end]
                    destination_locations = locations[j:sub_batch_end]
                    
                    sub_matrix = self._get_osrm_matrix_for_locations(
                        source_locations, destination_locations
                    )
                    
                    # Копируем значения из подматрицы в основную матрицу
                    for sub_i, main_i in enumerate(range(i, batch_end)):
                        for sub_j, main_j in enumerate(
                            range(j, sub_batch_end)
                        ):
                            matrix[main_i, main_j] = sub_matrix[sub_i, sub_j]
                    
                    # Добавляем задержку, чтобы не перегружать API
                    time.sleep(0.2)
            
            return matrix
            
        except Exception as e:
            print(f"Error getting OSRM distance matrix: {e}")
            print("Falling back to direct distance calculation")
            
            # В случае ошибки возвращаемся к прямым расстояниям
            for i in range(size):
                for j in range(size):
                    if i != j:
                        matrix[i, j] = locations[i].distance_to(locations[j])
            
            return matrix
    
    def _get_osrm_matrix_for_locations(
        self, 
        source_locations: List[Location], 
        destination_locations: List[Location]
    ) -> np.ndarray:
        """
        Получает матрицу расстояний для конкретного набора локаций.
        
        Args:
            source_locations: Список исходных локаций
            destination_locations: Список конечных локаций
            
        Returns:
            Матрица расстояний
        """
        coordinates = []
        
        # Собираем все координаты
        for loc in source_locations + destination_locations:
            coordinates.append(f"{loc.longitude},{loc.latitude}")
        
        # Формируем URL для запроса
        coords_str = ";".join(coordinates)
        source_indices = ";".join(str(i) for i in range(len(source_locations)))
        dest_indices = ";".join(
            str(i + len(source_locations)) 
            for i in range(len(destination_locations))
        )
        
        url = (f"{self.osrm_api_url}{coords_str}?"
               f"sources={source_indices}&destinations={dest_indices}")
        
        # Делаем запрос
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(
                f"OSRM API error: {response.status_code}, {response.text}"
            )
        
        # Получаем данные
        data = response.json()
        
        if data.get("code") != "Ok":
            raise Exception(f"OSRM returned error: {data.get('code')}")
        
        # Создаем матрицу расстояний
        distances = data.get("distances", [])
        matrix = np.array(distances, dtype=np.float64)
        
        # Преобразуем расстояния из метров в километры
        matrix = matrix / 1000.0
        
        return matrix
    
    def _get_osrm_matrix_batch(self, locations: List[Location]) -> np.ndarray:
        """
        Получает матрицу расстояний для всех локаций в одном пакете.
        
        Args:
            locations: Список локаций
            
        Returns:
            Матрица расстояний
        """
        size = len(locations)
        
        # Проверяем валидность локаций
        valid_locations = []
        for loc in locations:
            if (loc and hasattr(loc, 'latitude') and 
                hasattr(loc, 'longitude') and 
                loc.latitude is not None and loc.longitude is not None and
                not (loc.latitude == 0 and loc.longitude == 0)):
                valid_locations.append(loc)
        
        if len(valid_locations) != size:
            msg = f"Warning: {size - len(valid_locations)} invalid locations"
            print(msg)
            if len(valid_locations) < 2:
                raise Exception("Not enough valid locations for OSRM request")
        
        # Собираем координаты для запроса (долгота, широта для OSRM)
        coords = []
        for loc in valid_locations:
            coords.append(f"{loc.longitude},{loc.latitude}")
        
        # Соединяем все координаты
        coords_str = ";".join(coords)
        
        # Формируем URL для запроса (для table API)
        url = f"{self.osrm_api_url}{coords_str}"
        
        print(f"OSRM URL: {url}")  # Для отладки
        
        try:
            # Делаем запрос с таймаутом
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                raise Exception(
                    f"OSRM API error: {response.status_code}, "
                    f"{response.text[:200]}"
                )
            
            # Получаем данные
            data = response.json()
            
            if data.get("code") != "Ok":
                raise Exception(f"OSRM returned error: {data.get('code')}")
            
            # Создаем матрицу расстояний
            distances = data.get("distances", [])
            
            # Проверяем, что получили корректные данные
            if not distances or len(distances) != len(valid_locations):
                raise Exception(
                    f"Invalid OSRM response: expected "
                    f"{len(valid_locations)}x{len(valid_locations)} matrix, "
                    f"got {len(distances)} rows. Response: {data}"
                )
            
            # Проверяем размерность каждой строки
            for i, row in enumerate(distances):
                if len(row) != len(valid_locations):
                    raise Exception(
                        f"Invalid OSRM response: row {i} has "
                        f"{len(row)} elements, expected {len(valid_locations)}"
                    )
            
            matrix = np.array(distances, dtype=np.float64)
            
            # Преобразуем расстояния из метров в километры
            matrix = matrix / 1000.0
            
            # Если размер отличается от исходного, дополняем матрицу
            if len(valid_locations) != size:
                full_matrix = np.zeros((size, size), dtype=np.float64)
                for i in range(min(len(valid_locations), size)):
                    for j in range(min(len(valid_locations), size)):
                        full_matrix[i, j] = matrix[i, j]
                return full_matrix
            
            return matrix
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OSRM API request failed: {e}")
        except Exception as e:
            raise Exception(f"OSRM processing error: {e}")
    
    def _optimize_route_order(
        self, 
        orders: List[Dict[str, Any]], 
        depot_location: Location, 
        distance_matrix: np.ndarray, 
        order_locations: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Оптимизирует порядок заказов для минимизации пройденного пути.
        Использует алгоритм ближайшего соседа.
        
        Args:
            orders: Список заказов
            depot_location: Локация депо
            distance_matrix: Матрица расстояний
            order_locations: Словарь с индексами локаций заказов
            
        Returns:
            Словарь с оптимизированным маршрутом
        """
        if not orders:
            return {"orders": [], "total_distance": 0.0}
        
        # Начинаем с депо (индекс 0)
        current_idx = 0
        route_orders = []
        unvisited = orders.copy()
        total_distance = 0.0
        
        while unvisited:
            # Находим ближайший заказ
            nearest_order = None
            nearest_idx = None
            min_distance = float('inf')
            
            for order in unvisited:
                order_id = str(order["id"])
                if order_id in order_locations:
                    order_idx = order_locations[order_id]
                    distance = distance_matrix[current_idx][order_idx]
                    if distance < min_distance:
                        min_distance = distance
                        nearest_order = order
                        nearest_idx = order_idx
            
            if nearest_order:
                # Добавляем заказ в маршрут
                route_orders.append(nearest_order)
                unvisited.remove(nearest_order)
                
                # Добавляем расстояние
                total_distance += min_distance
                
                # Обновляем текущий индекс
                current_idx = nearest_idx
        
        # Добавляем расстояние возврата в депо
        if route_orders and current_idx is not None:
            total_distance += distance_matrix[current_idx][0]
        
        return {
            "orders": route_orders,
            "total_distance": total_distance
        }
        
    async def optimize_routes_genetic(
        self, 
        depot_data: Dict[str, Any],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]],
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет оптимизацию маршрутов с использованием
        генетического алгоритма.
        
        Args:
            depot_data: Данные о депо
            orders: Список заказов для оптимизации
            couriers: Список доступных курьеров
            params: Параметры генетического алгоритма
            
        Returns:
            Список оптимизированных маршрутов
        """
        print(f"=== GENETIC OPTIMIZATION CALLED ===")
        print(f"Depot: {depot_data.get('id') if depot_data else 'None'}")
        print(f"Orders: {len(orders) if orders else 0}")
        print(f"Couriers: {len(couriers) if couriers else 0}")
        
        if not orders or not couriers or not depot_data:
            print("Missing data, returning empty list")
            return []
        
        # Импортируем генетический оптимизатор
        from .genetic_optimizer import GeneticOptimizer
        
        # Извлекаем параметры генетического алгоритма
        population_size = params.get("population_size", 50) if params else 50
        generations = params.get("generations", 50) if params else 50
        mutation_rate = params.get("mutation_rate", 0.1) if params else 0.1
        elite_size = params.get("elite_size", 10) if params else 10
        timeout_seconds = params.get("timeout_seconds", 3600) if params else 3600  # Увеличиваем до 1 часа
        
        print(f"Genetic algorithm with params: pop={population_size}, "
              f"gen={generations}, mut={mutation_rate}, elite={elite_size}")
        
        # Создаем экземпляр генетического оптимизатора
        genetic_optimizer = GeneticOptimizer(
            population_size=population_size,
            max_generations=generations,
            mutation_rate=mutation_rate,
            elitism_rate=elite_size / population_size,  # Преобразуем в долю
            timeout_seconds=timeout_seconds
        )
        
        # Добавляем данные в оптимизатор
        genetic_optimizer.add_depot(depot_data)
        
        for courier in couriers:
            genetic_optimizer.add_courier(courier)
            
        for order in orders:
            genetic_optimizer.add_order(order)
        
        # Запускаем оптимизацию
        try:
            print(f"Starting genetic optimization with {len(orders)} orders, {len(couriers)} couriers")
            optimized_routes = genetic_optimizer.optimize_routes()
            print(f"Genetic optimization completed, got {len(optimized_routes)} routes")
            
            # Очищаем оптимизатор
            genetic_optimizer.reset()
            
            return optimized_routes
            
        except Exception as e:
            print(f"Error in genetic optimization: {e}")
            import traceback
            traceback.print_exc()
            # В случае ошибки возвращаемся к алгоритму ближайшего соседа
            genetic_optimizer.reset()
            print("Falling back to nearest neighbor algorithm")
            return await self._optimize_with_nearest_neighbor(
                depot_data, orders, couriers
            )

    async def optimize_routes_multi_depot(
        self,
        depots_data: List[Dict[str, Any]],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]],
        algorithm: str = "nearest_neighbor"
    ) -> List[Dict[str, Any]]:
        """
        Выполняет оптимизацию маршрутов для множественных депо 
        (Multi-Depot VRP).
        
        Args:
            depots_data: Список данных о депо
            orders: Список заказов для оптимизации
            couriers: Список доступных курьеров
            algorithm: Алгоритм оптимизации для каждого депо
            
        Returns:
            Список оптимизированных маршрутов
        """
        if not orders or not couriers or not depots_data:
            return []
        
        all_routes = []
        
        # Группируем курьеров по депо
        couriers_by_depot = {}
        for courier in couriers:
            depot_id = str(courier.get("depot_id"))
            if depot_id not in couriers_by_depot:
                couriers_by_depot[depot_id] = []
            couriers_by_depot[depot_id].append(courier)
        
        # Распределяем заказы между депо на основе расстояния
        orders_by_depot = self._assign_orders_to_depots(
            orders, depots_data
        )
        
        print(f"Multi-depot optimization with algorithm: {algorithm}")
        print(f"Depots: {len(depots_data)}, Orders: {len(orders)}, "
              f"Couriers: {len(couriers)}")
        
        # Оптимизируем маршруты для каждого депо
        for depot_data in depots_data:
            depot_id = str(depot_data.get("id"))
            depot_name = depot_data.get("name", f"Depot {depot_id}")
            depot_orders = orders_by_depot.get(depot_id, [])
            depot_couriers = couriers_by_depot.get(depot_id, [])
            
            print(f"Processing depot {depot_name}: "
                  f"{len(depot_orders)} orders, {len(depot_couriers)} couriers")
            
            if depot_orders and depot_couriers:
                # Используем выбранный алгоритм для этого депо
                depot_routes = await self.optimize_routes(
                    depot_data, depot_orders, depot_couriers, algorithm
                )
                all_routes.extend(depot_routes)
                print(f"Depot {depot_name} generated {len(depot_routes)} routes")
            elif depot_orders and not depot_couriers:
                print(f"Depot {depot_name}: has orders but no couriers")
            elif not depot_orders and depot_couriers:
                print(f"Depot {depot_name}: has couriers but no orders")
        
        print(f"Total routes generated: {len(all_routes)}")
        return all_routes
    
    async def optimize_routes_genetic_multi_depot(
        self,
        depots_data: List[Dict[str, Any]],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]],
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет генетическую оптимизацию маршрутов для множественных депо.
        
        Args:
            depots_data: Список данных о депо
            orders: Список заказов для оптимизации
            couriers: Список доступных курьеров
            params: Параметры генетического алгоритма
            
        Returns:
            Список оптимизированных маршрутов
        """
        if not orders or not couriers or not depots_data:
            return []
        
        all_routes = []
        
        # Группируем курьеров по депо
        couriers_by_depot = {}
        for courier in couriers:
            depot_id = str(courier.get("depot_id"))
            if depot_id not in couriers_by_depot:
                couriers_by_depot[depot_id] = []
            couriers_by_depot[depot_id].append(courier)
        
        # Распределяем заказы между депо на основе расстояния
        orders_by_depot = self._assign_orders_to_depots(
            orders, depots_data
        )
        
        # Оптимизируем маршруты для каждого депо 
        # с помощью генетического алгоритма
        for depot_data in depots_data:
            depot_id = str(depot_data.get("id"))
            depot_orders = orders_by_depot.get(depot_id, [])
            depot_couriers = couriers_by_depot.get(depot_id, [])
            
            if depot_orders and depot_couriers:
                # Используем генетический алгоритм для этого депо
                depot_routes = await self.optimize_routes_genetic(
                    depot_data, depot_orders, depot_couriers, params
                )
                all_routes.extend(depot_routes)
        
        return all_routes
    
    def _assign_orders_to_depots(
        self, 
        orders: List[Dict[str, Any]], 
        depots_data: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Распределяет заказы между депо на основе минимального расстояния.
        
        Args:
            orders: Список заказов
            depots_data: Список депо
            
        Returns:
            Словарь depot_id -> список заказов
        """
        orders_by_depot = {}
        
        # Инициализируем словарь
        for depot_data in depots_data:
            depot_id = str(depot_data.get("id"))
            orders_by_depot[depot_id] = []
        
        # Создаем локации депо
        depot_locations = []
        for depot_data in depots_data:
            depot_location = self._create_location_from_dict(
                depot_data.get("location", {})
            )
            depot_locations.append(depot_location)
        
        # Для каждого заказа находим ближайшее депо
        for order in orders:
            order_location = self._create_location_from_dict(
                order.get("location", {})
            )
            
            if not order_location:
                # Если не можем определить локацию, добавляем к первому депо
                first_depot_id = str(depots_data[0].get("id"))
                orders_by_depot[first_depot_id].append(order)
                continue
            
            # Находим ближайшее депо
            min_distance = float('inf')
            best_depot_id = str(depots_data[0].get("id"))
            
            for i, depot_location in enumerate(depot_locations):
                if depot_location:
                    distance = order_location.distance_to(depot_location)
                    if distance < min_distance:
                        min_distance = distance
                        best_depot_id = str(depots_data[i].get("id"))
            
            orders_by_depot[best_depot_id].append(order)
        
        return orders_by_depot


# Создаем экземпляр оптимизатора
route_optimizer = RouteOptimizer() 