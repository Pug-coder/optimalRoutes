from typing import Dict, List, Tuple, Optional
from uuid import UUID
import numpy as np
from datetime import datetime, timedelta
import requests
import time

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from api.models import Depot, Courier, Order, Route, RoutePoint, Location


class RouteOptimizer:
    """Service for optimizing delivery routes using OR-Tools."""
    
    def __init__(self):
        """Initialize the route optimizer."""
        self.depots: Dict[UUID, Depot] = {}
        self.couriers: Dict[UUID, Courier] = {}
        self.orders: Dict[UUID, Order] = {}
        self.use_real_roads: bool = True
        self.osrm_api_url: str = "https://router.project-osrm.org/table/v1/driving/"
        
    def add_depot(self, depot: Depot) -> None:
        """Add a depot to the optimizer."""
        self.depots[depot.id] = depot
        
    def add_courier(self, courier: Courier) -> None:
        """Add a courier to the optimizer."""
        self.couriers[courier.id] = courier
    
    def add_order(self, order: Order) -> None:
        """Add an order to the optimizer."""
        self.orders[order.id] = order
    
    def _compute_distance_matrix(self, locations: List[Location]) -> np.ndarray:
        """
        Compute the distance matrix between all locations.
        
        Args:
            locations: List of all locations (depots and delivery points)
            
        Returns:
            A 2D numpy array with distances between all locations
        """
        if not self.use_real_roads:
            # Используем прямые расстояния, как было раньше
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
    
    def _compute_osrm_distance_matrix(self, locations: List[Location]) -> np.ndarray:
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
            
            # Если у нас меньше точек, чем максимальный размер пакета, делаем один запрос
            if size <= batch_size:
                return self._get_osrm_matrix_batch(locations)
            
            # Иначе разбиваем на несколько запросов
            for i in range(0, size, batch_size):
                batch_end = min(i + batch_size, size)
                sources = f"sources={';'.join(str(idx) for idx in range(i, batch_end))}"
                
                for j in range(0, size, batch_size):
                    sub_batch_end = min(j + batch_size, size)
                    destinations = f"destinations={';'.join(str(idx) for idx in range(j, sub_batch_end))}"
                    
                    source_locations = locations[i:batch_end]
                    destination_locations = locations[j:sub_batch_end]
                    
                    sub_matrix = self._get_osrm_matrix_for_locations(source_locations, destination_locations)
                    
                    # Копируем значения из подматрицы в основную матрицу
                    for sub_i, main_i in enumerate(range(i, batch_end)):
                        for sub_j, main_j in enumerate(range(j, sub_batch_end)):
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
    
    def _get_osrm_matrix_for_locations(self, source_locations: List[Location], 
                                      destination_locations: List[Location]) -> np.ndarray:
        """
        Get distance matrix for a specific set of source and destination locations.
        
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
        dest_indices = ";".join(str(i + len(source_locations)) for i in range(len(destination_locations)))
        
        url = f"{self.osrm_api_url}{coords_str}?sources={source_indices}&destinations={dest_indices}"
        
        # Делаем запрос
        response = requests.get(url)
        
        if response.status_code != 200:
            raise Exception(f"OSRM API error: {response.status_code}, {response.text}")
        
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
            raise Exception(f"OSRM API error: {response.status_code}, {response.text}")
        
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
        
    def optimize_routes(self) -> List[Route]:
        """
        Solve the MDVRP problem and return optimized routes.
        
        Returns:
            List of optimized Route objects
        """
        print("Starting route optimization...")
        if not self.depots or not self.couriers or not self.orders:
            print(f"Missing data: depots={len(self.depots)}, couriers={len(self.couriers)}, orders={len(self.orders)}")
            return []
        
        # Create data model
        data = self._create_data_model()
        print(f"Data model created: {len(data['distance_matrix'])} locations, {data['num_vehicles']} vehicles")
        
        # Check if we have pending orders
        if not data.get('order_indices'):
            print("No pending orders found")
            return []
            
        # Check if we have depot indices
        if not data.get('depot_indices'):
            print("No depot indices found")
            return []
        
        print(f"Order indices: {data['order_indices']}")
        print(f"Depot indices: {data['depot_indices']}")
        print(f"Starts: {data['starts']}")
        print(f"Ends: {data['ends']}")
        
        # Create the routing index manager
        try:
            manager = pywrapcp.RoutingIndexManager(
                len(data['distance_matrix']),
                data['num_vehicles'],
                data['starts'],
                data['ends']
            )
            
            # Create routing model
            routing = pywrapcp.RoutingModel(manager)
            
            # Create distance callback
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                # Convert distance from km to meters and ensure it's an integer
                distance_km = data['distance_matrix'][from_node][to_node]
                distance_meters = int(distance_km * 1000)
                return distance_meters
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Add capacity constraint
            def demand_callback(from_index):
                from_node = manager.IndexToNode(from_index)
                return data['demands'][from_node]
            
            demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
            
            for i, courier_id in enumerate(data['couriers']):
                courier = self.couriers[courier_id]
                routing.AddDimension(
                    demand_callback_index,
                    0,  # null capacity slack
                    courier.max_capacity,  # vehicle maximum capacity
                    True,  # start cumul to zero
                    f'Capacity_{i}'
                )
            
            # Add distance constraint for each courier
            distance_callback_index = routing.RegisterTransitCallback(distance_callback)
            
            for i, courier_id in enumerate(data['couriers']):
                courier = self.couriers[courier_id]
                # Convert max_distance from km to meters (OR-Tools typically uses meters)
                max_distance_meters = int(courier.max_distance * 1000)
                
                routing.AddDimension(
                    distance_callback_index,
                    0,  # no slack
                    max_distance_meters,  # maximum distance for this courier
                    True,  # start cumul to zero
                    f'Distance_{i}'
                )
                
                # Get the distance dimension for this courier
                distance_dimension = routing.GetDimensionOrDie(f'Distance_{i}')
                
                # Set the global span cost coefficient to minimize total distance
                distance_dimension.SetGlobalSpanCostCoefficient(100)
            
            # Setting solution parameters
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = 30
            
            print("Solving routing problem...")
            # Solve the problem
            solution = routing.SolveWithParameters(search_parameters)
            
            # Return the solution
            if solution:
                print("Solution found!")
                routes = self._get_solution_routes(data, manager, routing, solution)
                print(f"Routes created: {len(routes)}")
                return routes
            else:
                print("No solution found by the solver")
        except Exception as e:
            print(f"Error during optimization: {e}")
        
        return []
    
    def _create_data_model(self) -> Dict:
        """
        Create the data model for the OR-Tools solver.
        
        Returns:
            Dictionary with all the data for the solver
        """
        data = {}
        
        # Collect all locations (depots first, then orders)
        locations = []
        depot_indices = []
        depot_id_to_index = {}
        
        # Add depot locations first
        for i, (depot_id, depot) in enumerate(self.depots.items()):
            locations.append(depot.location)
            depot_indices.append(i)
            depot_id_to_index[depot_id] = i
        
        # Add order locations
        order_indices = {}
        for order_id, order in self.orders.items():
            if order.status == "pending":
                idx = len(locations)
                locations.append(order.location)
                order_indices[order_id] = idx
        
        # Create distance matrix
        data['distance_matrix'] = self._compute_distance_matrix(locations)
        data['depot_indices'] = depot_indices
        
        # Courier information
        data['num_vehicles'] = len(self.couriers)
        data['couriers'] = list(self.couriers.keys())
        
        # Mapping couriers to their depots
        courier_depot_indices = []
        for courier_id in data['couriers']:
            courier = self.couriers[courier_id]
            depot_idx = depot_id_to_index.get(courier.depot_id, 0)
            courier_depot_indices.append(depot_idx)
        
        # Set start and end points for each vehicle (courier)
        starts = []
        ends = []
        for idx in courier_depot_indices:
            starts.append(idx)
            ends.append(idx)
            
        data['starts'] = starts
        data['ends'] = ends
        
        # Order demands (capacity requirements)
        demands = [0] * len(locations)  # Initialize with 0 for depots
        for order_id, order_idx in order_indices.items():
            order = self.orders[order_id]
            demands[order_idx] = order.items_count
        
        data['demands'] = demands
        data['order_indices'] = order_indices
        data['courier_depot_indices'] = courier_depot_indices
        
        return data
    
    def _get_solution_routes(
        self,
        data: Dict,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        solution: pywrapcp.Assignment
    ) -> List[Route]:
        """
        Extract the solution into Route objects.
        
        Args:
            data: Data model dictionary
            manager: RoutingIndexManager instance
            routing: RoutingModel instance
            solution: Assignment instance with the solution
            
        Returns:
            List of Route objects
        """
        routes = []
        
        try:
            # Extract solution routes
            for vehicle_idx in range(data['num_vehicles']):
                courier_id = data['couriers'][vehicle_idx]
                courier = self.couriers[courier_id]
                depot_id = courier.depot_id
                
                # Create a new route
                route = Route(
                    courier_id=courier_id,
                    depot_id=depot_id,
                    points=[],
                    total_distance=0.0,
                    total_load=0
                )
                
                # Follow the route for this vehicle
                index = routing.Start(vehicle_idx)
                route_distance = 0
                route_load = 0
                order_sequence = 0
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    
                    # Check if this node is an order (not a depot)
                    if node_index not in data['depot_indices']:
                        # Find which order this node represents
                        order_id = None
                        for o_id, o_idx in data['order_indices'].items():
                            if o_idx == node_index:
                                order_id = o_id
                                break
                        
                        if order_id:
                            order = self.orders[order_id]
                            
                            # Add to route points
                            route.points.append(RoutePoint(
                                order_id=order_id,
                                sequence=order_sequence,
                                estimated_arrival=None  # Could calculate ETA if needed
                            ))
                            
                            order_sequence += 1
                            route_load += order.items_count
                    
                    # Move to next node
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    
                    # Add distance
                    route_distance += routing.GetArcCostForVehicle(
                        previous_index, index, vehicle_idx)
                
                # Update route metrics
                # Convert distance from meters back to kilometers
                route.total_distance = route_distance / 1000.0
                route.total_load = route_load
                
                # Only add routes that have deliveries
                if route.points:
                    routes.append(route)
        except Exception as e:
            print(f"Error extracting solution routes: {e}")
        
        # Если решение не дало маршрутов, создадим простые маршруты вручную
        if not routes:
            print("Creating manual routes for demonstration")
            # Распределим заказы между курьерами вручную
            courier_orders = {}
            
            # Получаем список активных заказов
            pending_orders = {}
            for order_id, order in self.orders.items():
                if order.status == "pending":
                    pending_orders[order_id] = order
                    
            print(f"Pending orders: {len(pending_orders)}")
            
            if not pending_orders:
                print("No pending orders to create routes for")
                return []
            
            # Сгруппируем заказы по депо
            for order_id, order in pending_orders.items():
                # Находим ближайшее депо
                min_distance = float('inf')
                closest_depot_id = None
                
                for depot_id, depot in self.depots.items():
                    distance = order.location.distance_to(depot.location)
                    if distance < min_distance:
                        min_distance = distance
                        closest_depot_id = depot_id
                
                if closest_depot_id:
                    # Найти курьера из этого депо
                    for courier_id, courier in self.couriers.items():
                        if courier.depot_id == closest_depot_id:
                            if courier_id not in courier_orders:
                                courier_orders[courier_id] = []
                            courier_orders[courier_id].append((order_id, min_distance))
                            print(f"Assigned order {order_id} to courier {courier_id} with distance {min_distance:.2f}")
                            break
            
            print(f"Couriers with assigned orders: {len(courier_orders)}")
            
            # Создаем маршруты для каждого курьера
            for courier_id, orders_with_distance in courier_orders.items():
                if not orders_with_distance:
                    continue
                    
                # Сортируем заказы по расстоянию
                orders_with_distance.sort(key=lambda x: x[1])
                
                courier = self.couriers[courier_id]
                depot_id = courier.depot_id
                
                route = Route(
                    courier_id=courier_id,
                    depot_id=depot_id,
                    points=[],
                    total_distance=sum(distance for _, distance in orders_with_distance),
                    total_load=sum(self.orders[order_id].items_count for order_id, _ in orders_with_distance)
                )
                
                print(f"Creating route for courier {courier_id} with {len(orders_with_distance)} orders")
                
                # Добавляем точки в маршрут
                for i, (order_id, _) in enumerate(orders_with_distance):
                    route.points.append(RoutePoint(
                        order_id=order_id,
                        sequence=i,
                        estimated_arrival=None
                    ))
                    print(f"  Added order {order_id} to route at position {i}")
                
                routes.append(route)
            
            print(f"Total routes created: {len(routes)}")
                
        return routes 

    def reset(self):
        """Reset all optimizer data."""
        self.depots = {}
        self.couriers = {}
        self.orders = {} 