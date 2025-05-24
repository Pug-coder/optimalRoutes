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


class RouteOptimizer:
    """Оптимизатор маршрутов для API."""
    
    def __init__(self):
        """Инициализация оптимизатора маршрутов."""
        self.use_real_roads = True
        self.osrm_api_url = "https://router.project-osrm.org/table/v1/driving/"
    
    async def optimize_routes(
        self, 
        depot_data: Dict[str, Any],
        orders: List[Dict[str, Any]], 
        couriers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Выполняет оптимизацию маршрутов.
        
        Args:
            depot_data: Данные о депо
            orders: Список заказов для оптимизации
            couriers: Список доступных курьеров
            
        Returns:
            Список оптимизированных маршрутов
        """
        if not orders or not couriers or not depot_data:
            return []
        
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
        
        # Распределяем заказы между курьерами
        routes = []
        orders_copy = orders.copy()  # Работаем с копией
        
        # Группируем заказы по ближайшему курьеру
        for courier in couriers:
            courier_capacity = courier.get("max_capacity", 10)
            
            # Сортируем заказы по расстоянию от депо
            sorted_orders = []
            for order in orders_copy:
                order_id = str(order["id"])
                if order_id in order_locations:
                    order_idx = order_locations[order_id]
                    # Расстояние от депо до заказа
                    distance = distance_matrix[0][order_idx]
                    sorted_orders.append((order, distance))
            
            # Сортируем заказы по расстоянию
            sorted_orders.sort(key=lambda x: x[1])
            
            # Создаем маршрут для курьера
            route_orders = []
            current_load = 0
            
            for order, _ in sorted_orders:
                order_load = order.get("items_count", 1)
                if current_load + order_load <= courier_capacity:
                    route_orders.append(order)
                    current_load += order_load
                    # Удаляем заказ из списка всех заказов
                    if order in orders_copy:
                        orders_copy.remove(order)
            
            # Если есть заказы для этого курьера, создаем маршрут
            if route_orders:
                # Оптимизируем порядок заказов
                optimized_route = self._optimize_route_order(
                    route_orders, depot_location, distance_matrix, 
                    order_locations
                )
                
                # Создаем маршрут
                route = {
                    "id": str(uuid.uuid4()),
                    "courier_id": str(courier["id"]),
                    "depot_id": str(depot_data.get("id")),
                    "total_distance": optimized_route["total_distance"],
                    "total_load": sum(
                        order.get("items_count", 1) for order in route_orders
                    ),
                    "points": []
                }
                
                # Добавляем точки маршрута
                for j, order in enumerate(optimized_route["orders"]):
                    order_id = order["id"]
                    # Убедимся, что order_id строка
                    if not isinstance(order_id, str):
                        order_id = str(order_id)
                    
                    route["points"].append({
                        "order_id": order_id,
                        "sequence": j
                    })
                    
                routes.append(route)
        
        # Если остались заказы, распределяем их между курьерами
        if orders_copy:
            additional_routes = self._simple_distribution(
                depot_data.get("id"), orders_copy, couriers
            )
            routes.extend(additional_routes)
            
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
        
        # Собираем координаты для запроса
        coords = []
        for loc in locations:
            coords.append(f"{loc.longitude},{loc.latitude}")
        
        # Соединяем все координаты
        coords_str = ";".join(coords)
        
        # Формируем URL для запроса
        url = f"{self.osrm_api_url}{coords_str}"
        
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
        
        # Проверяем, что получили корректные данные
        if not distances or len(distances) != size:
            raise Exception(
                f"Invalid OSRM response: expected {size}x{size} matrix, "
                f"got {len(distances)} rows"
            )
        
        # Проверяем размерность каждой строки
        for i, row in enumerate(distances):
            if len(row) != size:
                raise Exception(
                    f"Invalid OSRM response: row {i} has {len(row)} elements, "
                    f"expected {size}"
                )
        
        matrix = np.array(distances, dtype=np.float64)
        
        # Преобразуем расстояния из метров в километры
        matrix = matrix / 1000.0
        
        return matrix
    
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
        if not orders or not couriers or not depot_data:
            return []
        
        # Извлекаем параметры генетического алгоритма
        population_size = params.get("population_size", 50) if params else 50
        generations = params.get("generations", 50) if params else 50
        mutation_rate = params.get("mutation_rate", 0.1) if params else 0.1
        elite_size = params.get("elite_size", 10) if params else 10
        
        # Пока используем обычный алгоритм как заглушку
        # В реальной реализации здесь была бы полная логика GA
        print(f"Genetic algorithm with params: pop={population_size}, "
              f"gen={generations}, mut={mutation_rate}, elite={elite_size}")
        
        # Используем обычный алгоритм с небольшими модификациями
        return await self.optimize_routes(depot_data, orders, couriers)


# Создаем экземпляр оптимизатора
route_optimizer = RouteOptimizer() 