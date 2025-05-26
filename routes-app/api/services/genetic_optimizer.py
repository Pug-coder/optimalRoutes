from typing import Dict, List, Tuple, Set, Any, Optional
import random
import copy
import numpy as np
import uuid
from datetime import datetime, timedelta
import requests
import time

from ..models import Location


class Individual:
    """
    Represents a single solution (individual) in the genetic algorithm.
    A solution is a set of routes that satisfy all constraints.
    """
    def __init__(self, routes: List[Dict[str, Any]], fitness: float = 0.0):
        self.routes = routes
        self.fitness = fitness
        
    def __lt__(self, other):
        """Enable sorting by fitness (lower is better)"""
        return self.fitness < other.fitness


class GeneticOptimizer:
    """
    A genetic algorithm implementation for solving the Multi-Depot 
    Vehicle Routing Problem. Adapted to work with API data structures.
    """
    
    def __init__(
        self, 
        population_size: int = 50,  # Уменьшил для быстрой сходимости
        max_generations: int = 200,  # Увеличил для лучшего поиска
        mutation_rate: float = 0.2,  # Увеличил для большего разнообразия
        crossover_rate: float = 0.8,
        elitism_rate: float = 0.2,  # Увеличил для сохранения лучших решений
        timeout_seconds: int = 600
    ):
        """
        Initialize the genetic optimizer.
        
        Args:
            population_size: Number of individuals in the population
            max_generations: Maximum number of generations to run
            mutation_rate: Probability of mutation for each individual (0-1)
            crossover_rate: Probability of crossover for each pair of 
                individuals (0-1)
            elitism_rate: Proportion of best individuals to keep 
                unchanged (0-1)
            timeout_seconds: Maximum time to run in seconds
        """
        self.population_size = population_size
        self.max_generations = max_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_rate = elitism_rate
        self.timeout_seconds = timeout_seconds
        
        # Data containers
        self.depots: Dict[str, Dict[str, Any]] = {}
        self.couriers: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.distance_matrix = None
        self.locations = []
        self.depot_indices = []
        self.courier_depot_indices = []
        self.order_indices = {}
        
        # OSRM configuration
        self.use_real_roads: bool = False  # Отключаем OSRM для тестирования
        self.osrm_api_url: str = (
            "https://router.project-osrm.org/table/v1/driving/"
        )
        
    def add_depot(self, depot_data: Dict[str, Any]) -> None:
        """Add a depot to the optimizer."""
        depot_id = str(depot_data["id"])
        self.depots[depot_id] = depot_data
        
    def add_courier(self, courier_data: Dict[str, Any]) -> None:
        """Add a courier to the optimizer."""
        courier_id = str(courier_data["id"])
        self.couriers[courier_id] = courier_data
    
    def add_order(self, order_data: Dict[str, Any]) -> None:
        """Add an order to the optimizer."""
        order_id = str(order_data["id"])
        self.orders[order_id] = order_data
        
    def _create_location_from_dict(
        self, location_dict: Dict[str, Any]
    ) -> Optional[Location]:
        """Create Location object from dictionary."""
        if not location_dict:
            return None
            
        try:
            return Location(
                id=str(location_dict.get("id", "")),
                latitude=float(location_dict.get("latitude", 0.0)),
                longitude=float(location_dict.get("longitude", 0.0)),
                address=location_dict.get("address", "")
            )
        except (ValueError, TypeError):
            return None
        
    def _compute_distance_matrix(
        self, locations: List[Location]
    ) -> np.ndarray:
        """
        Compute the distance matrix between all locations.
        
        Args:
            locations: List of all locations (depots and delivery points)
            
        Returns:
            A 2D numpy array with distances between all locations
        """
        if not self.use_real_roads:
            # Используем прямые расстояния (по прямой)
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
        Compute the distance matrix using OSRM API.
        
        Args:
            locations: List of all locations (depots and delivery points)
            
        Returns:
            A 2D numpy array with driving distances between all locations
        """
        size = len(locations)
        matrix = np.zeros((size, size), dtype=np.float64)
        
        try:
            # Максимальное количество местоположений в одном запросе
            batch_size = 100
            
            # Если у нас меньше точек, чем максимальный размер пакета, 
            # делаем один запрос
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
        Get distance matrix for a specific set of source and 
        destination locations.
        
        Args:
            source_locations: List of starting points
            destination_locations: List of ending points
            
        Returns:
            A 2D numpy array with distances
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
        Get a complete distance matrix for all locations in one batch.
        
        Args:
            locations: List of all locations
            
        Returns:
            A 2D numpy array with distances
        """
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
        matrix = np.array(distances, dtype=np.float64)
        
        # Преобразуем расстояния из метров в километры
        matrix = matrix / 1000.0
        
        return matrix
        
    def _initialize_data(self) -> bool:
        """
        Prepare the data for the genetic algorithm.
        Returns:
            True if initialization was successful, False otherwise
        """
        # Reset data structures
        self.locations = []
        self.depot_indices = []
        depot_id_to_index = {}
        
        print(f"Initializing data with {len(self.depots)} depots, {len(self.couriers)} couriers, {len(self.orders)} orders")
        
        # Add depot locations first
        for i, (depot_id, depot_data) in enumerate(self.depots.items()):
            print(f"Processing depot {depot_id}: {depot_data}")
            depot_location = self._create_location_from_dict(
                depot_data.get("location", {})
            )
            if depot_location:
                print(f"Added depot location: {depot_location.latitude}, {depot_location.longitude}")
                self.locations.append(depot_location)
                self.depot_indices.append(i)
                depot_id_to_index[depot_id] = i
            else:
                print(f"Failed to create depot location for {depot_id}")
        
        # Add order locations
        self.order_indices = {}
        for order_id, order_data in self.orders.items():
            print(f"Processing order {order_id}: status={order_data.get('status')}")
            if order_data.get("status") == "pending":
                order_location = self._create_location_from_dict(
                    order_data.get("location", {})
                )
                if order_location:
                    idx = len(self.locations)
                    self.locations.append(order_location)
                    self.order_indices[order_id] = idx
                    print(f"Added order location: {order_location.latitude}, {order_location.longitude}")
                else:
                    print(f"Failed to create order location for {order_id}")
        
        print(f"Total locations: {len(self.locations)}, order indices: {len(self.order_indices)}")
        
        # Mapping couriers to their depots
        self.courier_depot_indices = []
        for courier_id, courier_data in self.couriers.items():
            depot_id = str(courier_data.get("depot_id"))
            depot_idx = depot_id_to_index.get(depot_id, 0)
            self.courier_depot_indices.append((courier_id, depot_idx))
        
        # Compute distance matrix
        if self.locations:
            print(f"Computing distance matrix for {len(self.locations)} locations")
            self.distance_matrix = self._compute_distance_matrix(
                self.locations
            )
            print(f"Distance matrix shape: {self.distance_matrix.shape}")
        else:
            print("No locations found, cannot compute distance matrix")
            self.distance_matrix = np.array([])
        
        # Check if we have valid data
        if not self.depots or not self.couriers or not self.order_indices:
            print(f"Missing data: depots={len(self.depots)}, "
                  f"couriers={len(self.couriers)}, "
                  f"orders={len(self.order_indices)}")
            return False
            
        return True
        
    def _create_initial_population(self) -> List[Individual]:
        """
        Create an initial population of individuals with random solutions.
        
        Returns:
            List of Individual objects
        """
        population = []
        
        # Create multiple random solutions
        for _ in range(self.population_size):
            # Create a greedy random solution
            routes = self._create_random_solution()
            
            # Calculate fitness
            fitness = self._calculate_fitness(routes)
            
            # Add to population
            population.append(Individual(routes, fitness))
            
        return population
        
    def _create_random_solution(self) -> List[Dict[str, Any]]:
        """
        Create a random feasible solution with proper depot-order assignment.
        
        Returns:
            List of route dictionaries
        """
        routes = []
        
        # Сначала распределяем заказы между депо
        orders_by_depot = self._assign_orders_to_depots()
        
        print("Orders distribution by depot:")
        for depot_id, order_ids in orders_by_depot.items():
            depot_name = self.depots[depot_id].get("name", depot_id)
            print(f"  {depot_name}: {len(order_ids)} orders")
        
        # Группируем курьеров по депо
        couriers_by_depot = {}
        for courier_id, courier_data in self.couriers.items():
            depot_id = str(courier_data.get("depot_id"))
            if depot_id not in couriers_by_depot:
                couriers_by_depot[depot_id] = []
            couriers_by_depot[depot_id].append(courier_id)
        
        # Для каждого депо создаем маршруты
        all_remaining_orders = set()
        
        for depot_id, order_ids in orders_by_depot.items():
            if not order_ids:
                continue  # Пропускаем депо без заказов
                
            depot_couriers = couriers_by_depot.get(depot_id, [])
            if not depot_couriers:
                print(f"No couriers for depot {depot_id}, "
                      f"skipping {len(order_ids)} orders")
                # Добавляем эти заказы к общему списку нераспределенных
                all_remaining_orders.update(order_ids)
                continue
            
            # Перемешиваем заказы для случайности
            remaining_orders = order_ids.copy()
            random.shuffle(remaining_orders)
            
            # Назначаем заказы курьерам этого депо
            for courier_id in depot_couriers:
                if not remaining_orders:
                    break
                    
                courier_data = self.couriers[courier_id]
                max_capacity = courier_data.get("max_capacity", 10)
                
                # Create a new route
                route = {
                    "id": str(uuid.uuid4()),
                    "courier_id": courier_id,
                    "depot_id": depot_id,
                    "points": [],
                    "total_distance": 0.0,
                    "total_load": 0
                }
                
                # Assign orders to this courier while respecting capacity
                current_capacity = 0
                sequence = 0
                orders_to_remove = []
                
                for order_id in remaining_orders:
                    order_data = self.orders[order_id]
                    order_load = order_data.get("items_count", 1)
                    
                    # Check if adding this order exceeds capacity
                    if current_capacity + order_load <= max_capacity:
                        # Create temporary route to check distance constraint
                        temp_route = {
                            "courier_id": courier_id,
                            "depot_id": depot_id,
                            "points": route["points"] + [{
                                "order_id": order_id,
                                "sequence": sequence
                            }],
                            "total_distance": 0.0,
                            "total_load": 0
                        }
                        
                        # Calculate distance for temporary route
                        self._update_route_metrics(temp_route)
                        
                        # Check distance constraint
                        max_distance = courier_data.get("max_distance", float('inf'))
                        
                        if temp_route["total_distance"] <= max_distance:
                            # Add to route
                            route["points"].append({
                                "order_id": order_id,
                                "sequence": sequence
                            })
                            
                            # Update capacity
                            current_capacity += order_load
                            orders_to_remove.append(order_id)
                            sequence += 1
                            
                            # Stop adding orders if route is full
                            if current_capacity >= max_capacity:
                                break
                
                # Remove assigned orders from remaining
                for order_id in orders_to_remove:
                    remaining_orders.remove(order_id)
                
                # Only add routes with orders
                if route["points"]:
                    # Update route metrics
                    self._update_route_metrics(route)
                    routes.append(route)
                    
                    courier_name = courier_data.get("name", courier_id)
                    print(f"  Assigned {len(route['points'])} orders to "
                          f"{courier_name}")
            
            # If there are still remaining orders in this depot, 
            # try to add them to existing routes
            if remaining_orders:
                print(f"  {len(remaining_orders)} orders remaining for "
                      f"depot {depot_id}")
                # Try to add to existing routes of this depot
                for route in routes:
                    if route["depot_id"] != depot_id:
                        continue
                        
                    courier_data = self.couriers[route["courier_id"]]
                    max_capacity = courier_data.get("max_capacity", 10)
                    current_load = sum(
                        self.orders[point["order_id"]].get("items_count", 1) 
                        for point in route["points"]
                    )
                    
                    orders_to_remove = []
                    for order_id in remaining_orders:
                        order_data = self.orders[order_id]
                        order_load = order_data.get("items_count", 1)
                        
                        # Check if adding this order exceeds capacity
                        if current_load + order_load <= max_capacity:
                            # Create temporary route to check distance constraint
                            temp_route = {
                                "courier_id": route["courier_id"],
                                "depot_id": route["depot_id"],
                                "points": route["points"] + [{
                                    "order_id": order_id,
                                    "sequence": len(route["points"])
                                }],
                                "total_distance": 0.0,
                                "total_load": 0
                            }
                            
                            # Calculate distance for temporary route
                            self._update_route_metrics(temp_route)
                            
                            # Check distance constraint
                            max_distance = courier_data.get("max_distance", float('inf'))
                            
                            if temp_route["total_distance"] <= max_distance:
                                # Add to route
                                route["points"].append({
                                    "order_id": order_id,
                                    "sequence": len(route["points"])
                                })
                                
                                # Update capacity
                                current_load += order_load
                                orders_to_remove.append(order_id)
                                
                                # Stop adding orders if route is full
                                if current_load >= max_capacity:
                                    break
                    
                    # Remove assigned orders
                    for order_id in orders_to_remove:
                        remaining_orders.remove(order_id)
                        
                    # Update route metrics
                    if orders_to_remove:
                        self._update_route_metrics(route)
                    
                    if not remaining_orders:
                        break
                
                # Добавляем оставшиеся заказы к общему списку
                all_remaining_orders.update(remaining_orders)
        
        # Обрабатываем все оставшиеся нераспределенные заказы
        if all_remaining_orders:
            print(f"Processing {len(all_remaining_orders)} remaining orders")
            self._assign_remaining_orders(routes, all_remaining_orders)
            
            # Проверяем, остались ли еще нераспределенные заказы
            if all_remaining_orders:
                print(f"WARNING: {len(all_remaining_orders)} orders still "
                      f"unassigned after processing")
                
        return routes
        
    def _assign_remaining_orders(
        self, routes: List[Dict[str, Any]], remaining_orders: Set[str]
    ) -> None:
        """
        Assign any remaining orders to existing routes or create new routes if needed.
        
        Args:
            routes: Existing routes
            remaining_orders: Set of order IDs that still need to be assigned
        """
        # First try to add to existing routes
        for route in routes:
            courier_data = self.couriers[route["courier_id"]]
            max_capacity = courier_data.get("max_capacity", 10)
            current_load = sum(
                self.orders[point["order_id"]].get("items_count", 1) 
                for point in route["points"]
            )
            
            orders_to_remove = set()
            for order_id in remaining_orders:
                order_data = self.orders[order_id]
                order_load = order_data.get("items_count", 1)
                
                # Check if adding this order exceeds capacity
                if current_load + order_load <= max_capacity:
                    # Create temporary route to check distance constraint
                    temp_route = {
                        "courier_id": route["courier_id"],
                        "depot_id": route["depot_id"],
                        "points": route["points"] + [{
                            "order_id": order_id,
                            "sequence": len(route["points"])
                        }],
                        "total_distance": 0.0,
                        "total_load": 0
                    }
                    
                    # Calculate distance for temporary route
                    self._update_route_metrics(temp_route)
                    
                    # Check distance constraint
                    max_distance = courier_data.get("max_distance", float('inf'))
                    
                    if temp_route["total_distance"] <= max_distance:
                        # Add to route
                        route["points"].append({
                            "order_id": order_id,
                            "sequence": len(route["points"])
                        })
                        
                        # Update capacity
                        current_load += order_load
                        orders_to_remove.add(order_id)
                        
                        # Stop adding orders if route is full
                        if current_load >= max_capacity:
                            break
            
            # Remove assigned orders
            remaining_orders -= orders_to_remove
            
            # Update route metrics
            self._update_route_metrics(route)
            
            # If no more remaining orders, stop
            if not remaining_orders:
                break
        
        # If still remaining orders, assign randomly to couriers 
        # (creating new routes if needed)
        if remaining_orders:
            courier_ids = list(self.couriers.keys())
            random.shuffle(courier_ids)
            
            for courier_id in courier_ids:
                if not remaining_orders:
                    break
                    
                courier_data = self.couriers[courier_id]
                max_capacity = courier_data.get("max_capacity", 10)
                
                # Check if courier already has a route
                existing_route = None
                for route in routes:
                    if route["courier_id"] == courier_id:
                        existing_route = route
                        break
                
                if existing_route:
                    # If route exists but is full, skip
                    current_load = sum(
                        self.orders[point["order_id"]].get("items_count", 1)
                        for point in existing_route["points"]
                    )
                    if current_load >= max_capacity:
                        continue
                else:
                    # Create a new route
                    existing_route = {
                        "id": str(uuid.uuid4()),
                        "courier_id": courier_id,
                        "depot_id": str(courier_data.get("depot_id")),
                        "points": [],
                        "total_distance": 0.0,
                        "total_load": 0
                    }
                    routes.append(existing_route)
                
                # Try to add orders to this route
                current_load = sum(
                    self.orders[point["order_id"]].get("items_count", 1)
                    for point in existing_route["points"]
                )
                
                orders_to_remove = set()
                for order_id in remaining_orders:
                    order_data = self.orders[order_id]
                    order_load = order_data.get("items_count", 1)
                    
                    # Check if adding this order exceeds capacity
                    if current_load + order_load <= max_capacity:
                        # Create temporary route to check distance constraint
                        temp_route = {
                            "courier_id": courier_id,
                            "depot_id": str(courier_data.get("depot_id")),
                            "points": existing_route["points"] + [{
                                "order_id": order_id,
                                "sequence": len(existing_route["points"])
                            }],
                            "total_distance": 0.0,
                            "total_load": 0
                        }
                        
                        # Calculate distance for temporary route
                        self._update_route_metrics(temp_route)
                        
                        # Check distance constraint
                        max_distance = courier_data.get("max_distance", float('inf'))
                        
                        if temp_route["total_distance"] <= max_distance:
                            # Add to route
                            existing_route["points"].append({
                                "order_id": order_id,
                                "sequence": len(existing_route["points"])
                            })
                            
                            # Update load
                            current_load += order_load
                            orders_to_remove.add(order_id)
                            
                            # Stop adding orders if route is full
                            if current_load >= max_capacity:
                                break
                
                # Remove assigned orders
                remaining_orders -= orders_to_remove
                
                # Update route metrics
                self._update_route_metrics(existing_route)
    
    def _update_route_metrics(self, route: Dict[str, Any]) -> None:
        """
        Update the total_distance and total_load for a route.
        
        Args:
            route: The route dictionary to update
        """
        if not route["points"]:
            route["total_distance"] = 0.0
            route["total_load"] = 0
            return
        
        # Get depot index
        depot_id = route["depot_id"]
        depot_idx = None
        for i, (d_id, _) in enumerate(self.depots.items()):
            if d_id == depot_id:
                depot_idx = i
                break
                
        if depot_idx is None:
            print(f"Error: Depot {depot_id} not found")
            return
        
        # Calculate total distance
        total_distance = 0.0
        
        # Distance from depot to first order
        first_order_id = route["points"][0]["order_id"]
        first_order_idx = self.order_indices[first_order_id]
        total_distance += self.distance_matrix[depot_idx][first_order_idx]
        
        # Distance between consecutive orders
        for i in range(len(route["points"]) - 1):
            current_order_id = route["points"][i]["order_id"]
            next_order_id = route["points"][i + 1]["order_id"]
            current_idx = self.order_indices[current_order_id]
            next_idx = self.order_indices[next_order_id]
            total_distance += self.distance_matrix[current_idx][next_idx]
        
        # Distance from last order back to depot
        last_order_id = route["points"][-1]["order_id"]
        last_order_idx = self.order_indices[last_order_id]
        total_distance += self.distance_matrix[last_order_idx][depot_idx]
        
        # Calculate total load
        total_load = sum(
            self.orders[point["order_id"]].get("items_count", 1) 
            for point in route["points"]
        )
        
        # Update route
        route["total_distance"] = total_distance
        route["total_load"] = total_load
        
    def _calculate_fitness(self, routes: List[Dict[str, Any]]) -> float:
        """
        Calculate the fitness score for a solution.
        Lower fitness is better.
        
        Args:
            routes: List of route dictionaries representing a solution
            
        Returns:
            Fitness score (lower is better)
        """
        if not routes:
            return float('inf')
        
        total_distance = sum(route["total_distance"] for route in routes)
        num_routes = len(routes)
        
        # Penalize for orders not assigned to any route
        assigned_orders = set()
        for route in routes:
            for point in route["points"]:
                assigned_orders.add(point["order_id"])
                
        pending_orders = set(self.order_indices.keys())
        unassigned_orders = pending_orders - assigned_orders
        
        # Log unassigned orders for debugging
        if unassigned_orders:
            print(f"  Unassigned orders: {len(unassigned_orders)} out of "
                  f"{len(pending_orders)}")
        
        # Heavy penalty for unassigned orders
        unassigned_penalty = len(unassigned_orders) * 1000.0
        
        # NEW: Heavy penalty for routes exceeding distance constraints
        distance_violation_penalty = 0.0
        for route in routes:
            courier_data = self.couriers[route["courier_id"]]
            max_distance = courier_data.get("max_distance", 50.0)
            
            if route["total_distance"] > max_distance:
                # Penalty proportional to the violation
                violation = route["total_distance"] - max_distance
                distance_violation_penalty += violation * 10000.0  # Much heavier penalty
        
        # Main fitness components
        fitness = (total_distance + (num_routes * 10.0) + 
                  unassigned_penalty + distance_violation_penalty)
        
        return fitness
        
    def _select_parents(self, population: List[Individual]) -> List[Individual]:
        """
        Select parents for reproduction using tournament selection.
        
        Args:
            population: List of individuals in the current population
            
        Returns:
            List of selected parents
        """
        tournament_size = max(2, int(len(population) * 0.1))
        parents = []
        
        for _ in range(len(population)):
            # Select tournament_size random individuals
            tournament = random.sample(population, tournament_size)
            
            # Select the best individual from tournament
            winner = min(tournament, key=lambda ind: ind.fitness)
            
            # Add to parents
            parents.append(winner)
            
        return parents
        
    def _crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        """
        Perform crossover between two parents to create two children.
        
        Args:
            parent1: First parent
            parent2: Second parent
            
        Returns:
            Tuple of two new individuals (children)
        """
        # Skip crossover with probability (1 - crossover_rate)
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        # If empty parents, return copies
        if not parent1.routes or not parent2.routes:
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        # Create children by deep copying parents
        child1 = copy.deepcopy(parent1)
        child2 = copy.deepcopy(parent2)
        
        # Choose a random route to swap
        try:
            route_idx1 = random.randint(0, len(child1.routes) - 1)
            route_idx2 = random.randint(0, len(child2.routes) - 1)
            
            # Exchange routes
            temp_route = copy.deepcopy(child1.routes[route_idx1])
            child1.routes[route_idx1] = copy.deepcopy(child2.routes[route_idx2])
            child2.routes[route_idx2] = temp_route
            
            # Check and fix order assignments to avoid duplicates
            self._fix_duplicate_orders(child1.routes)
            self._fix_duplicate_orders(child2.routes)
            
            # Update metrics and fitness
            for route in child1.routes:
                self._update_route_metrics(route)
            for route in child2.routes:
                self._update_route_metrics(route)
                
            child1.fitness = self._calculate_fitness(child1.routes)
            child2.fitness = self._calculate_fitness(child2.routes)
            
        except (ValueError, IndexError) as e:
            print(f"Error in crossover: {e}")
            # Return original parents if error
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        return child1, child2
        
    def _fix_duplicate_orders(self, routes: List[Dict[str, Any]]) -> None:
        """
        Fix any duplicate order assignments across routes.
        
        Args:
            routes: List of routes to fix
        """
        seen_orders = set()
        removed_orders = []
        
        for route in routes:
            # Collect duplicates
            new_points = []
            
            for point in route["points"]:
                if point["order_id"] in seen_orders:
                    # Skip duplicate and collect for reassignment
                    removed_orders.append(point["order_id"])
                    continue
                else:
                    seen_orders.add(point["order_id"])
                    new_points.append(point)
            
            # Update route points (removing duplicates)
            route["points"] = new_points
            
            # Update sequences
            for i, point in enumerate(route["points"]):
                point["sequence"] = i
        
        # Reassign removed orders
        if removed_orders:
            print(f"Reassigning {len(removed_orders)} duplicate orders")
            self._assign_remaining_orders(routes, set(removed_orders))
    
    def _mutate(self, individual: Individual) -> Individual:
        """
        Apply mutation to an individual.
        
        Args:
            individual: Individual to mutate
            
        Returns:
            Mutated individual
        """
        # Skip mutation with probability (1 - mutation_rate)
        if random.random() > self.mutation_rate:
            return individual
        
        # If empty routes, return unchanged
        if not individual.routes:
            return individual
        
        # Choose a random mutation operator
        mutation_type = random.choice([
            'swap_orders',
            'move_order',
            'reverse_segment'
        ])
        
        if mutation_type == 'swap_orders':
            # Swap two random orders within or between routes
            if random.random() < 0.5 and len(individual.routes) > 1:
                # Swap between routes
                route1_idx = random.randint(0, len(individual.routes) - 1)
                route2_idx = random.randint(0, len(individual.routes) - 1)
                while route2_idx == route1_idx:
                    route2_idx = random.randint(0, len(individual.routes) - 1)
                
                route1 = individual.routes[route1_idx]
                route2 = individual.routes[route2_idx]
                
                if route1["points"] and route2["points"]:
                    point1_idx = random.randint(0, len(route1["points"]) - 1)
                    point2_idx = random.randint(0, len(route2["points"]) - 1)
                    
                    # Swap order IDs
                    (route1["points"][point1_idx]["order_id"], 
                     route2["points"][point2_idx]["order_id"]) = (
                        route2["points"][point2_idx]["order_id"], 
                        route1["points"][point1_idx]["order_id"]
                    )
            else:
                # Swap within route
                route_idx = random.randint(0, len(individual.routes) - 1)
                route = individual.routes[route_idx]
                
                if len(route["points"]) >= 2:
                    point1_idx = random.randint(0, len(route["points"]) - 1)
                    point2_idx = random.randint(0, len(route["points"]) - 1)
                    while point2_idx == point1_idx:
                        point2_idx = random.randint(
                            0, len(route["points"]) - 1
                        )
                    
                    # Swap order IDs
                    (route["points"][point1_idx]["order_id"], 
                     route["points"][point2_idx]["order_id"]) = (
                        route["points"][point2_idx]["order_id"], 
                        route["points"][point1_idx]["order_id"]
                    )
        
        elif mutation_type == 'move_order':
            # Move an order from one route to another (within same depot)
            if len(individual.routes) > 1:
                # Find routes from the same depot
                depot_routes = {}
                for i, route in enumerate(individual.routes):
                    depot_id = route["depot_id"]
                    if depot_id not in depot_routes:
                        depot_routes[depot_id] = []
                    depot_routes[depot_id].append(i)
                
                # Find a depot with multiple routes
                valid_depots = [depot_id for depot_id, route_indices 
                               in depot_routes.items() 
                               if len(route_indices) > 1]
                
                if valid_depots:
                    # Choose random depot with multiple routes
                    chosen_depot = random.choice(valid_depots)
                    route_indices = depot_routes[chosen_depot]
                    
                    source_idx = random.choice(route_indices)
                    target_idx = random.choice(route_indices)
                    while target_idx == source_idx:
                        target_idx = random.choice(route_indices)
                    
                    source_route = individual.routes[source_idx]
                    target_route = individual.routes[target_idx]
                    
                    if source_route["points"]:
                        # Check capacity constraints
                        courier_data = self.couriers[target_route["courier_id"]]
                        max_capacity = courier_data.get("max_capacity", 10)
                        current_load = sum(
                            self.orders[point["order_id"]].get("items_count", 1)
                            for point in target_route["points"]
                        )
                        
                        # Remove random point from source
                        point_idx = random.randint(
                            0, len(source_route["points"]) - 1
                        )
                        point = source_route["points"][point_idx]
                        order_load = self.orders[point["order_id"]].get(
                            "items_count", 1
                        )
                        
                        # Check if target route can accommodate this order
                        if current_load + order_load <= max_capacity:
                            # Remove from source
                            source_route["points"].pop(point_idx)
                            
                            # Add to target
                            point["sequence"] = len(target_route["points"])
                            target_route["points"].append(point)
                            
                            # Update sequences in source route
                            for i, p in enumerate(source_route["points"]):
                                p["sequence"] = i
        
        elif mutation_type == 'reverse_segment':
            # Reverse a segment of a route
            route_idx = random.randint(0, len(individual.routes) - 1)
            route = individual.routes[route_idx]
            
            if len(route["points"]) >= 3:
                # Select random segment
                start = random.randint(0, len(route["points"]) - 3)
                end = random.randint(start + 1, len(route["points"]) - 1)
                
                # Reverse segment
                segment = route["points"][start:end+1]
                segment.reverse()
                route["points"][start:end+1] = segment
                
                # Update sequences
                for i, point in enumerate(route["points"]):
                    point["sequence"] = i
        
        # Update metrics
        for route in individual.routes:
            self._update_route_metrics(route)
            
        # Update fitness
        individual.fitness = self._calculate_fitness(individual.routes)
        
        return individual
             
    def optimize_routes(self) -> List[Dict[str, Any]]:
        """
        Solve the MDVRP problem using a genetic algorithm.
        
        Returns:
            List of optimized route dictionaries
        """
        print("Starting genetic algorithm optimization...")
        
        # Initialize data
        if not self._initialize_data():
            print("Initialization failed, returning empty solution")
            return []
        
        # Create initial population
        population = self._create_initial_population()
        print(f"Initial population created with {len(population)} individuals")
        
        # Track best solution
        best_individual = min(population, key=lambda ind: ind.fitness)
        print(f"Initial best fitness: {best_individual.fitness}")
        
        # Set timeout
        start_time = datetime.now()
        timeout = timedelta(seconds=self.timeout_seconds)
        
        # Main evolutionary loop
        for generation in range(self.max_generations):
            # Check timeout
            if datetime.now() - start_time > timeout:
                print(f"Timeout reached after {generation} generations")
                break
                
            # Select parents for reproduction
            parents = self._select_parents(population)
            
            # Create new population
            new_population = []
            
            # Elitism: Keep best individuals
            elites_count = max(1, int(self.population_size * self.elitism_rate))
            population.sort(key=lambda ind: ind.fitness)
            new_population.extend(copy.deepcopy(population[:elites_count]))
            
            # Crossover and mutation
            for i in range(0, len(parents) - 1, 2):
                if len(new_population) >= self.population_size:
                    break
                    
                parent1 = parents[i]
                parent2 = parents[i + 1] if i + 1 < len(parents) else parents[0]
                
                # Crossover
                child1, child2 = self._crossover(parent1, parent2)
                
                # Mutation
                child1 = self._mutate(child1)
                child2 = self._mutate(child2)
                
                # Add to new population
                new_population.append(child1)
                if len(new_population) < self.population_size:
                    new_population.append(child2)
            
            # Replace population
            population = new_population
            
            # Update best solution
            current_best = min(population, key=lambda ind: ind.fitness)
            if current_best.fitness < best_individual.fitness:
                best_individual = copy.deepcopy(current_best)
                print(f"New best fitness at generation {generation}: "
                      f"{best_individual.fitness}")
        
        print(f"Genetic algorithm completed. "
              f"Best fitness: {best_individual.fitness}")
        
        # Return best routes
        return best_individual.routes

    def reset(self):
        """Reset all optimizer data."""
        self.depots = {}
        self.couriers = {}
        self.orders = {}
        # Не сбрасываем настройки OSRM
        # self.use_real_roads остается неизменным 

    def _assign_orders_to_depots(self) -> Dict[str, List[str]]:
        """
        Распределяет заказы между депо на основе минимального расстояния.
        
        Returns:
            Словарь depot_id -> список order_ids
        """
        orders_by_depot = {}
        
        # Инициализируем словарь
        for depot_id in self.depots.keys():
            orders_by_depot[depot_id] = []
        
        # Для каждого заказа находим ближайшее депо
        for order_id in self.order_indices.keys():
            order_idx = self.order_indices[order_id]
            
            min_distance = float('inf')
            best_depot_id = list(self.depots.keys())[0]  # По умолчанию первое депо
            
            # Проверяем расстояние до каждого депо
            for i, depot_id in enumerate(self.depots.keys()):
                depot_idx = i  # Депо идут первыми в списке локаций
                distance = self.distance_matrix[depot_idx][order_idx]
                
                if distance < min_distance:
                    min_distance = distance
                    best_depot_id = depot_id
            
            orders_by_depot[best_depot_id].append(order_id)
        
        return orders_by_depot 