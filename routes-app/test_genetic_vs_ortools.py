import time
import uuid
from typing import List

from services.route_optimizer import RouteOptimizer
from services.genetic_optimizer import GeneticOptimizer
from api.models import Depot, Courier, Order, Location


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
            id=uuid.uuid4(),
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
            id=uuid.uuid4(),
            name=f"Courier {i+1}",
            phone=f"+1234567{i:04d}",
            depot_id=depots[depot_idx].id,
            max_capacity=5
        )
        couriers.append(courier)
    
    # Generate random orders
    import random
    for i in range(num_orders):
        order = Order(
            id=uuid.uuid4(),
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


def evaluate_route_quality(routes: List):
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


def print_route_details(routes: List, algorithm_name: str):
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
    Run a comparison between OR-Tools and Genetic Algorithm.
    
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
    
    # Initialize OR-Tools optimizer
    ortools_optimizer = RouteOptimizer()
    
    # Add data to OR-Tools optimizer
    for depot in depots:
        ortools_optimizer.add_depot(depot)
    for courier in couriers:
        ortools_optimizer.add_courier(courier)
    for order in orders:
        ortools_optimizer.add_order(order)
    
    # Run OR-Tools optimization and measure time
    start_time = time.time()
    ortools_routes = ortools_optimizer.optimize_routes()
    ortools_time = time.time() - start_time
    
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
    ortools_quality = evaluate_route_quality(ortools_routes)
    ga_quality = evaluate_route_quality(ga_routes)
    
    # Print comparison
    print("\nPerformance Comparison:")
    print(f"  OR-Tools execution time: {ortools_time:.3f} seconds")
    print(f"  Genetic Algorithm execution time: {ga_time:.3f} seconds")
    
    print("\nRoute Quality Comparison:")
    print("  OR-Tools:")
    for metric, value in ortools_quality.items():
        print(f"    {metric}: {value}")
    
    print("  Genetic Algorithm:")
    for metric, value in ga_quality.items():
        print(f"    {metric}: {value}")
        
    # Detailed route information
    if len(ortools_routes) <= 5 and len(ga_routes) <= 5:
        print_route_details(ortools_routes, "OR-Tools")
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
    
    # Large test (comment out if takes too long)
    """
    run_comparison(
        num_depots=5,
        num_couriers=15,
        num_orders=50,
        grid_size=500,
        genetic_params={
            "population_size": 150,
            "max_generations": 100,
            "mutation_rate": 0.1,
            "crossover_rate": 0.9,
            "elitism_rate": 0.2,
            "timeout_seconds": 30
        }
    )
    """ 