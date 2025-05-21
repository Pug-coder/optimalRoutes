import time
import uuid
import random
from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Location:
    lat: float
    lng: float
    address: str = None
    
    def distance_to(self, other: 'Location') -> float:
        return ((self.lat - other.lat) ** 2 + (self.lng - other.lng) ** 2) ** 0.5


@dataclass
class Depot:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    location: Location = None


@dataclass
class Courier:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    phone: str = ""
    depot_id: uuid.UUID = None
    max_capacity: int = 10


@dataclass
class Order:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    customer_name: str = ""
    customer_phone: str = ""
    location: Location = None
    items_count: int = 1
    weight: float = 1.0
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    courier_id: uuid.UUID = None
    depot_id: uuid.UUID = None


@dataclass
class RoutePoint:
    order_id: uuid.UUID
    sequence: int
    estimated_arrival: datetime = None


@dataclass
class Route:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    courier_id: uuid.UUID = None
    depot_id: uuid.UUID = None
    created_at: datetime = field(default_factory=datetime.now)
    points: List[RoutePoint] = field(default_factory=list)
    total_distance: float = 0.0
    total_load: int = 0


class RouteOptimizer:
    """Service for optimizing delivery routes."""
    
    def __init__(self):
        """Initialize the route optimizer."""
        self.depots: Dict[uuid.UUID, Depot] = {}
        self.couriers: Dict[uuid.UUID, Courier] = {}
        self.orders: Dict[uuid.UUID, Order] = {}
        
    def add_depot(self, depot: Depot) -> None:
        """Add a depot to the optimizer."""
        self.depots[depot.id] = depot
        
    def add_courier(self, courier: Courier) -> None:
        """Add a courier to the optimizer."""
        self.couriers[courier.id] = courier
    
    def add_order(self, order: Order) -> None:
        """Add an order to the optimizer."""
        self.orders[order.id] = order
    
    def _compute_distance_matrix(self, locations: List[Location]) -> list:
        """
        Compute the distance matrix between all locations.
        
        Args:
            locations: List of all locations (depots and delivery points)
            
        Returns:
            A 2D array with distances between all locations
        """
        size = len(locations)
        matrix = [[0.0 for _ in range(size)] for _ in range(size)]
        
        for i in range(size):
            for j in range(size):
                if i != j:
                    matrix[i][j] = locations[i].distance_to(locations[j])
        
        return matrix
    
    def optimize_routes(self) -> List[Route]:
        """
        Solve the routing problem and return optimized routes.
        This is a simplified version of the OR-Tools implementation.
        
        Returns:
            List of optimized Route objects
        """
        print("Starting route optimization...")
        
        # Create return list
        routes = []
        
        # Get pending orders
        pending_orders = {
            order_id: order for order_id, order in self.orders.items()
            if order.status == "pending"
        }
        
        if not pending_orders:
            print("No pending orders to optimize")
            return routes
            
        # Group couriers by depot
        depot_couriers = {}
        for courier_id, courier in self.couriers.items():
            if courier.depot_id not in depot_couriers:
                depot_couriers[courier.depot_id] = []
            depot_couriers[courier.depot_id].append(courier_id)
        
        # For each order, find the closest depot
        order_depot_distances = {}
        for order_id, order in pending_orders.items():
            order_depot_distances[order_id] = []
            for depot_id, depot in self.depots.items():
                distance = order.location.distance_to(depot.location)
                order_depot_distances[order_id].append((depot_id, distance))
            # Sort by distance
            order_depot_distances[order_id].sort(key=lambda x: x[1])
        
        # Assign orders to depots (closest first)
        depot_orders = {depot_id: [] for depot_id in self.depots.keys()}
        for order_id, distances in order_depot_distances.items():
            if distances:
                closest_depot_id = distances[0][0]
                depot_orders[closest_depot_id].append(order_id)
        
        # For each depot, create routes
        for depot_id, order_ids in depot_orders.items():
            if not order_ids or depot_id not in depot_couriers:
                continue
                
            # Get available couriers for this depot
            available_couriers = depot_couriers[depot_id]
            if not available_couriers:
                continue
                
            # Calculate orders per courier (equal distribution)
            orders_per_courier = max(1, len(order_ids) // len(available_couriers))
            
            # Assign orders to couriers
            for i, courier_id in enumerate(available_couriers):
                courier = self.couriers[courier_id]
                
                # Calculate start and end indices for this courier's orders
                start_idx = i * orders_per_courier
                end_idx = min((i + 1) * orders_per_courier, len(order_ids))
                
                # Get orders for this courier
                courier_order_ids = order_ids[start_idx:end_idx]
                if not courier_order_ids:
                    continue
                    
                # Create route
                route = Route(
                    courier_id=courier_id,
                    depot_id=depot_id,
                    points=[],
                    total_distance=0.0,
                    total_load=0
                )
                
                # Get depot and order locations for distance matrix
                locations = [self.depots[depot_id].location]
                for order_id in courier_order_ids:
                    locations.append(self.orders[order_id].location)
                
                # Compute distance matrix
                distance_matrix = self._compute_distance_matrix(locations)
                
                # Simple greedy algorithm: start from depot (index 0)
                current_idx = 0
                remaining_indices = list(range(1, len(locations)))
                route_points = []
                
                # While there are unvisited points
                while remaining_indices:
                    # Find closest unvisited point
                    closest_idx = min(
                        remaining_indices, 
                        key=lambda idx: distance_matrix[current_idx][idx]
                    )
                    
                    # Add to route
                    order_id = courier_order_ids[closest_idx - 1]  # Adjust for depot at index 0
                    route_points.append(
                        RoutePoint(
                            order_id=order_id,
                            sequence=len(route_points),
                            estimated_arrival=None
                        )
                    )
                    
                    # Update total distance
                    route.total_distance += distance_matrix[current_idx][closest_idx]
                    
                    # Update total load
                    route.total_load += self.orders[order_id].items_count
                    
                    # Update current index and remove from remaining
                    current_idx = closest_idx
                    remaining_indices.remove(closest_idx)
                
                # Add distance back to depot
                route.total_distance += distance_matrix[current_idx][0]
                
                # Add route points
                route.points = route_points
                
                # Add route to result
                routes.append(route)
        
        print(f"Created {len(routes)} routes")
        return routes


class GeneticOptimizer:
    """Service for optimizing delivery routes using a genetic algorithm."""
    
    def __init__(
        self, 
        population_size: int = 100, 
        max_generations: int = 100,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_rate: float = 0.1,
        timeout_seconds: int = 30
    ):
        """Initialize the genetic optimizer."""
        self.population_size = population_size
        self.max_generations = max_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_rate = elitism_rate
        self.timeout_seconds = timeout_seconds
        
        # Data containers
        self.depots: Dict[uuid.UUID, Depot] = {}
        self.couriers: Dict[uuid.UUID, Courier] = {}
        self.orders: Dict[uuid.UUID, Order] = {}
        
    def add_depot(self, depot: Depot) -> None:
        """Add a depot to the optimizer."""
        self.depots[depot.id] = depot
        
    def add_courier(self, courier: Courier) -> None:
        """Add a courier to the optimizer."""
        self.couriers[courier.id] = courier
    
    def add_order(self, order: Order) -> None:
        """Add an order to the optimizer."""
        self.orders[order.id] = order
    
    def optimize_routes(self) -> List[Route]:
        """
        Solve the routing problem using a genetic algorithm.
        This is a simplified version for demonstration purposes.
        
        Returns:
            List of optimized Route objects
        """
        print("Starting genetic algorithm optimization...")
        
        # Create return list
        routes = []
        
        # Get pending orders
        pending_orders = {
            order_id: order for order_id, order in self.orders.items()
            if order.status == "pending"
        }
        
        if not pending_orders:
            print("No pending orders to optimize")
            return routes
            
        # Group couriers by depot
        depot_couriers = {}
        for courier_id, courier in self.couriers.items():
            if courier.depot_id not in depot_couriers:
                depot_couriers[courier.depot_id] = []
            depot_couriers[courier.depot_id].append(courier_id)
        
        # For each order, find the closest depot
        order_depot_distances = {}
        for order_id, order in pending_orders.items():
            order_depot_distances[order_id] = []
            for depot_id, depot in self.depots.items():
                distance = order.location.distance_to(depot.location)
                order_depot_distances[order_id].append((depot_id, distance))
            # Sort by distance
            order_depot_distances[order_id].sort(key=lambda x: x[1])
        
        # Assign orders to depots (closest first)
        depot_orders = {depot_id: [] for depot_id in self.depots.keys()}
        for order_id, distances in order_depot_distances.items():
            if distances:
                closest_depot_id = distances[0][0]
                depot_orders[closest_depot_id].append(order_id)
        
        # For each depot, create routes with genetic algorithm optimization
        for depot_id, order_ids in depot_orders.items():
            if not order_ids or depot_id not in depot_couriers:
                continue
                
            # Get available couriers for this depot
            available_couriers = depot_couriers[depot_id]
            if not available_couriers:
                continue
                
            # Calculate orders per courier (equal distribution as initial solution)
            orders_per_courier = max(1, len(order_ids) // len(available_couriers))
            
            # Create multiple random solutions and select the best one
            best_solution = None
            best_fitness = float('inf')
            
            for _ in range(self.population_size):
                # Shuffle order IDs for randomness
                random.shuffle(order_ids)
                
                # Create routes for this solution
                solution_routes = []
                
                # Assign orders to couriers
                for i, courier_id in enumerate(available_couriers):
                    courier = self.couriers[courier_id]
                    
                    # Calculate start and end indices for this courier's orders
                    start_idx = i * orders_per_courier
                    end_idx = min((i + 1) * orders_per_courier, len(order_ids))
                    
                    # Get orders for this courier
                    courier_order_ids = order_ids[start_idx:end_idx]
                    if not courier_order_ids:
                        continue
                        
                    # Create route
                    route = Route(
                        courier_id=courier_id,
                        depot_id=depot_id,
                        points=[],
                        total_distance=0.0,
                        total_load=0
                    )
                    
                    # Get depot and order locations for distance matrix
                    locations = [self.depots[depot_id].location]
                    for order_id in courier_order_ids:
                        locations.append(self.orders[order_id].location)
                    
                    # Random permutation of visit order (genetic part)
                    visit_order = list(range(1, len(locations)))
                    random.shuffle(visit_order)
                    
                    # Calculate route metrics
                    current_idx = 0  # Start at depot
                    route_distance = 0.0
                    route_load = 0
                    route_points = []
                    
                    for idx in visit_order:
                        # Calculate distance
                        order_id = courier_order_ids[idx - 1]  # Adjust for depot at index 0
                        distance = locations[current_idx].distance_to(locations[idx])
                        route_distance += distance
                        
                        # Update load
                        route_load += self.orders[order_id].items_count
                        
                        # Add route point
                        route_points.append(
                            RoutePoint(
                                order_id=order_id,
                                sequence=len(route_points),
                                estimated_arrival=None
                            )
                        )
                        
                        # Update current index
                        current_idx = idx
                    
                    # Add distance back to depot
                    route_distance += locations[current_idx].distance_to(locations[0])
                    
                    # Update route metrics
                    route.total_distance = route_distance
                    route.total_load = route_load
                    route.points = route_points
                    
                    # Add route to solution
                    solution_routes.append(route)
                
                # Calculate fitness (total distance)
                fitness = sum(r.total_distance for r in solution_routes)
                
                # Update best solution
                if fitness < best_fitness:
                    best_fitness = fitness
                    best_solution = solution_routes
            
            # Add best solution to routes
            if best_solution:
                routes.extend(best_solution)
        
        print(f"Created {len(routes)} routes with genetic optimization")
        return routes


def generate_test_data(
    num_depots: int = 2,
    num_couriers: int = 5,
    num_orders: int = 20,
    grid_size: int = 100
):
    """
    Generate test data for optimization comparison.
    
    Args:
        num_depots: Number of depots to generate
        num_couriers: Number of couriers to generate
        num_orders: Number of orders to generate
        grid_size: Size of the grid for location coordinates
        
    Returns:
        Tuple of (depots, couriers, orders) lists
    """
    depots = []
    couriers = []
    orders = []
    
    # Generate depots
    for i in range(num_depots):
        depot = Depot(
            name=f"Depot {i+1}",
            location=Location(
                lat=float(i * grid_size // num_depots),
                lng=float(i * grid_size // num_depots),
                address=f"Depot {i+1} Address"
            )
        )
        depots.append(depot)
    
    # Generate couriers (distribute evenly across depots)
    for i in range(num_couriers):
        depot_idx = i % num_depots
        courier = Courier(
            name=f"Courier {i+1}",
            phone=f"+1234567{i:04d}",
            depot_id=depots[depot_idx].id,
            max_capacity=5
        )
        couriers.append(courier)
    
    # Generate random orders
    for i in range(num_orders):
        order = Order(
            customer_name=f"Customer {i+1}",
            customer_phone=f"+9876543{i:04d}",
            location=Location(
                lat=float(random.randint(0, grid_size)),
                lng=float(random.randint(0, grid_size)),
                address=f"Order {i+1} Address"
            ),
            items_count=random.randint(1, 3),
            weight=float(random.randint(1, 10))
        )
        orders.append(order)
    
    return depots, couriers, orders


def evaluate_route_quality(routes: List[Route]):
    """
    Evaluate the quality of routes by various metrics.
    
    Args:
        routes: List of Route objects
        
    Returns:
        Dictionary with route quality metrics
    """
    if not routes:
        return {
            "total_routes": 0,
            "total_distance": 0,
            "total_orders": 0,
            "avg_orders_per_route": 0,
            "max_route_distance": 0,
            "min_route_distance": 0
        }
    
    # Count total orders
    total_orders = sum(len(route.points) for route in routes)
    
    # Calculate distances
    total_distance = sum(route.total_distance for route in routes)
    max_route_distance = max(route.total_distance for route in routes)
    min_route_distance = min(route.total_distance for route in routes)
    
    return {
        "total_routes": len(routes),
        "total_distance": round(total_distance, 2),
        "total_orders": total_orders,
        "avg_orders_per_route": round(total_orders / len(routes), 2),
        "max_route_distance": round(max_route_distance, 2),
        "min_route_distance": round(min_route_distance, 2)
    }


def print_route_details(routes: List[Route], algorithm_name: str):
    """
    Print detailed information about routes.
    
    Args:
        routes: List of Route objects
        algorithm_name: Name of the algorithm used
    """
    print(f"\n{algorithm_name} Routes:")
    
    for i, route in enumerate(routes):
        print(f"  Route {i+1}: {len(route.points)} orders, "
              f"distance: {route.total_distance:.2f}, "
              f"load: {route.total_load}")
        
        for j, point in enumerate(route.points):
            print(f"    Stop {j+1}: Order {point.order_id}")


def run_comparison(
    num_depots: int = 2,
    num_couriers: int = 5,
    num_orders: int = 20,
    grid_size: int = 100,
    genetic_params: dict = None
):
    """
    Run a comparison between simple greedy algorithm and genetic algorithm.
    
    Args:
        num_depots: Number of depots to generate
        num_couriers: Number of couriers to generate
        num_orders: Number of orders to generate
        grid_size: Size of the grid for location coordinates
        genetic_params: Optional parameters for the genetic algorithm
    """
    print(f"\nRunning comparison with {num_depots} depots, "
          f"{num_couriers} couriers, {num_orders} orders")
    
    # Generate test data
    depots, couriers, orders = generate_test_data(
        num_depots, num_couriers, num_orders, grid_size
    )
    
    # Initialize greedy optimizer
    greedy_optimizer = RouteOptimizer()
    
    # Add data to greedy optimizer
    for depot in depots:
        greedy_optimizer.add_depot(depot)
    for courier in couriers:
        greedy_optimizer.add_courier(courier)
    for order in orders:
        greedy_optimizer.add_order(order)
    
    # Run greedy optimization and measure time
    start_time = time.time()
    greedy_routes = greedy_optimizer.optimize_routes()
    greedy_time = time.time() - start_time
    
    # Initialize Genetic Algorithm optimizer
    ga_optimizer = GeneticOptimizer(**(genetic_params or {}))
    
    # Add data to Genetic Algorithm optimizer
    for depot in depots:
        ga_optimizer.add_depot(depot)
    for courier in couriers:
        ga_optimizer.add_courier(courier)
    for order in orders:
        ga_optimizer.add_order(order)
    
    # Run Genetic Algorithm optimization and measure time
    start_time = time.time()
    ga_routes = ga_optimizer.optimize_routes()
    ga_time = time.time() - start_time
    
    # Evaluate results
    greedy_quality = evaluate_route_quality(greedy_routes)
    ga_quality = evaluate_route_quality(ga_routes)
    
    # Print comparison
    print("\nPerformance Comparison:")
    print(f"  Greedy Algorithm execution time: {greedy_time:.3f} seconds")
    print(f"  Genetic Algorithm execution time: {ga_time:.3f} seconds")
    
    print("\nRoute Quality Comparison:")
    print("  Greedy Algorithm:")
    for metric, value in greedy_quality.items():
        print(f"    {metric}: {value}")
    
    print("  Genetic Algorithm:")
    for metric, value in ga_quality.items():
        print(f"    {metric}: {value}")
        
    # Detailed route information
    if len(greedy_routes) <= 5 and len(ga_routes) <= 5:
        print_route_details(greedy_routes, "Greedy Algorithm")
        print_route_details(ga_routes, "Genetic Algorithm")


if __name__ == "__main__":
    # Small test
    run_comparison(
        num_depots=2,
        num_couriers=4,
        num_orders=10,
        grid_size=100,
        genetic_params={
            "population_size": 50,
            "max_generations": 50,
            "mutation_rate": 0.2,
            "crossover_rate": 0.8,
            "elitism_rate": 0.1,
            "timeout_seconds": 10
        }
    )
    
    # Medium test
    run_comparison(
        num_depots=3,
        num_couriers=8,
        num_orders=25,
        grid_size=200,
        genetic_params={
            "population_size": 100,
            "max_generations": 80,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "elitism_rate": 0.2,
            "timeout_seconds": 15
        }
    ) 