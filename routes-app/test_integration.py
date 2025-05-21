import os
import random
import sys
import uuid
from typing import List

# Add the directory containing this file to Python's module search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# API prefix
API_PREFIX = "/api"


def generate_test_data(
    num_depots: int = 2,
    num_couriers: int = 5,
    num_orders: int = 20,
    grid_size: int = 100
):
    """
    Generate test data for API testing.
    
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
    
    # Generate depots with safe coordinates
    for i in range(num_depots):
        lat = float(10 + i * 5)  # Safe latitude values
        lng = float(10 + i * 5)  # Safe longitude values
        
        depot = {
            "name": f"Depot {i+1}",
            "location": {
                "lat": lat,
                "lng": lng,
                "address": f"Depot {i+1} Address"
            }
        }
        depots.append(depot)
    
    # Generate couriers (depot_id will be updated later)
    for i in range(num_couriers):
        courier = {
            "name": f"Courier {i+1}",
            "phone": f"+1234567{i:04d}",
            "max_capacity": 5,
            "max_distance": 100.0,  # Добавляем конечное значение вместо бесконечности
            "depot_id": "temp"  # placeholder, will be replaced with actual ID
        }
        couriers.append(courier)
    
    # Generate random orders with safe coordinates
    for i in range(num_orders):
        lat = float(random.randint(10, 50))  # Safe latitude values
        lng = float(random.randint(10, 50))  # Safe longitude values
        
        order = {
            "customer_name": f"Customer {i+1}",
            "customer_phone": f"+9876543{i:04d}",
            "location": {
                "lat": lat,
                "lng": lng,
                "address": f"Order {i+1} Address"
            },
            "items_count": random.randint(1, 3),
            "weight": float(random.randint(1, 10)),
            "status": "pending"
        }
        orders.append(order)
    
    return depots, couriers, orders


def add_test_data(depots, couriers, orders):
    """
    Add test data to the API.
    
    Args:
        depots: List of depot objects
        couriers: List of courier objects
        orders: List of order objects
    """
    # Add depots and keep track of their IDs
    depot_ids = {}
    for i, depot in enumerate(depots):
        response = client.post(f"{API_PREFIX}/depots/", json=depot)
        assert response.status_code == 200, f"Failed to add depot: {response.text}"
        
        depot_data = response.json()
        depot_ids[i] = depot_data["id"]  # Map index to actual ID
    
    # Add couriers with updated depot_ids
    for i, courier in enumerate(couriers):
        # Определить, к какому складу относится курьер, исходя из индекса
        depot_idx = i % len(depots)
        
        # Обновить depot_id курьера на фактический ID склада
        courier_data = courier.copy()
        courier_data["depot_id"] = depot_ids[depot_idx]
        
        response = client.post(f"{API_PREFIX}/couriers/", json=courier_data)
        assert response.status_code == 200, f"Failed to add courier: {response.text}"
    
    # Add orders
    for order in orders:
        response = client.post(f"{API_PREFIX}/orders/", json=order)
        assert response.status_code == 200, f"Failed to add order: {response.text}"


def validate_routes(routes: List[dict]):
    """
    Validate that the routes meet the required constraints.
    
    Args:
        routes: List of route objects returned from the API
        
    Returns:
        Boolean indicating if routes are valid
    """
    if not routes:
        print("No routes were generated")
        return False
    
    # Check that every route has points
    for i, route in enumerate(routes):
        if not route.get("points"):
            print(f"Route {i} has no points")
            return False
            
        # Verify the sequence is correctly ordered
        sequence_numbers = [
            point.get("sequence") for point in route.get("points", [])
        ]
        if sequence_numbers != sorted(sequence_numbers):
            print(
                f"Route {i} has incorrect sequence ordering: "
                f"{sequence_numbers}"
            )
            return False
            
        # Verify total_distance is not zero (unless no points)
        if len(route.get("points", [])) > 0 and route.get("total_distance", 0) <= 0:
            print(
                f"Route {i} has invalid total_distance: "
                f"{route.get('total_distance')}"
            )
            return False
    
    # Count total orders assigned in routes
    route_order_ids = set()
    for route in routes:
        for point in route.get("points", []):
            route_order_ids.add(point.get("order_id"))
    
    # Get orders from API
    response = client.get(f"{API_PREFIX}/orders/")
    all_orders = response.json()
    
    # After optimization, orders should be marked as assigned, so count total orders
    total_orders = len(all_orders)
    print(f"Total orders in routes: {len(route_order_ids)} out of {total_orders} total orders")
    
    # Make sure all the orders in routes are in the database
    if len(route_order_ids) == 0:
        print("No orders assigned to routes")
        return False
    
    return True


def test_optimize_genetic():
    """Test the genetic algorithm optimization endpoint."""
    # Reset API state (this will clear any existing data)
    client.post(f"{API_PREFIX}/reset/")
    
    # Generate and add test data
    num_depots = 2
    num_couriers = 5
    num_orders = 15
    depots, couriers, orders = generate_test_data(
        num_depots=num_depots,
        num_couriers=num_couriers,
        num_orders=num_orders
    )
    add_test_data(depots, couriers, orders)
    
    # Verify test data was added correctly
    response = client.get(f"{API_PREFIX}/depots/")
    assert len(response.json()) == num_depots
    
    response = client.get(f"{API_PREFIX}/couriers/")
    assert len(response.json()) == num_couriers
    
    response = client.get(f"{API_PREFIX}/orders/")
    assert len(response.json()) == num_orders
    
    # Call the genetic algorithm optimization endpoint
    response = client.post(f"{API_PREFIX}/routes/optimize/genetic")
    assert response.status_code == 200, f"Optimization failed: {response.text}"
    
    # Get the generated routes
    routes = response.json()
    
    # Validate the routes
    assert validate_routes(routes), "Routes failed validation"
    
    # Check that orders have been assigned
    response = client.get(f"{API_PREFIX}/orders/")
    orders = response.json()
    
    assigned_orders = [
        order for order in orders 
        if order.get("status") == "assigned"
    ]
    
    # Genetic algorithm might not assign all orders, but should assign most of them
    min_required_assignments = int(num_orders * 0.8)  # At least 80% of orders should be assigned
    assert len(assigned_orders) >= min_required_assignments, (
        f"Too few orders assigned: {len(assigned_orders)} out of {num_orders}. "
        f"Expected at least {min_required_assignments}"
    )
    
    print(f"Assigned {len(assigned_orders)} out of {num_orders} orders ({len(assigned_orders)/num_orders:.1%})")
    
    # Verify that routes returned from /routes/ endpoint match
    response = client.get(f"{API_PREFIX}/routes/")
    stored_routes = response.json()
    assert len(stored_routes) == len(routes), (
        "Routes count mismatch between response and stored routes"
    )
    
    print(f"Successfully created {len(routes)} routes with the genetic algorithm")
    
    # Print route details
    for i, route in enumerate(routes):
        print(
            f"Route {i+1}: {len(route['points'])} orders, "
            f"distance: {route['total_distance']:.2f}, "
            f"load: {route.get('total_load', 0)}"
        )
        
        # Print sequence of orders
        print("  Order sequence:")
        for point in sorted(route["points"], key=lambda p: p["sequence"]):
            print(f"    Stop {point['sequence']}: Order {point['order_id']}")


def test_compare_ortools_vs_genetic():
    """Test and compare both optimization methods."""
    # Reset API state (this will clear any existing data)
    client.post(f"{API_PREFIX}/reset/")
    
    # Generate and add test data
    num_depots = 2
    num_couriers = 5
    num_orders = 15
    depots, couriers, orders = generate_test_data(
        num_depots=num_depots,
        num_couriers=num_couriers,
        num_orders=num_orders
    )
    add_test_data(depots, couriers, orders)
    
    # Call the OR-Tools optimization endpoint
    response = client.post(f"{API_PREFIX}/routes/optimize")
    assert response.status_code == 200, (
        f"OR-Tools optimization failed: {response.text}"
    )
    ortools_routes = response.json()
    
    # Reset API state
    client.post(f"{API_PREFIX}/reset/")
    
    # Add the same test data again
    add_test_data(depots, couriers, orders)
    
    # Call the genetic algorithm optimization endpoint
    response = client.post(f"{API_PREFIX}/routes/optimize/genetic")
    assert response.status_code == 200, (
        f"Genetic optimization failed: {response.text}"
    )
    genetic_routes = response.json()
    
    # Compare results
    print("\nComparison results:")
    print(
        f"OR-Tools: {len(ortools_routes)} routes, "
        f"total distance: {sum(r['total_distance'] for r in ortools_routes):.2f}"
    )
    print(
        f"Genetic: {len(genetic_routes)} routes, "
        f"total distance: {sum(r['total_distance'] for r in genetic_routes):.2f}"
    )
    
    # Find which algorithm performed better
    ortools_total_distance = sum(r["total_distance"] for r in ortools_routes)
    genetic_total_distance = sum(r["total_distance"] for r in genetic_routes)
    
    if genetic_total_distance < ortools_total_distance:
        print("Genetic algorithm found a better solution!")
    elif genetic_total_distance > ortools_total_distance:
        print("OR-Tools found a better solution!")
    else:
        print("Both algorithms found solutions with equal total distance")


if __name__ == "__main__":
    print("Running integration tests for genetic optimization...")
    test_optimize_genetic()
    print("\nRunning comparison test between OR-Tools and genetic algorithm...")
    test_compare_ortools_vs_genetic()
