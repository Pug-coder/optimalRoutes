import requests
import json
from pprint import pprint

# Base URL for the API
BASE_URL = "http://0.0.0.0:8000/api"

def test_api():
    """Test the route optimization API with sample data."""
    print("Testing the Route Optimization API\n")
    
    # Create two depots
    print("Creating depots...")
    depot1 = {
        "name": "Центральный склад",
        "location": {
            "lat": 55.7558,
            "lng": 37.6173,
            "address": "Москва, Красная площадь"
        }
    }
    
    depot2 = {
        "name": "Южный склад",
        "location": {
            "lat": 55.6500,
            "lng": 37.6200,
            "address": "Москва, Нахимовский проспект"
        }
    }
    
    depot1_response = requests.post(f"{BASE_URL}/depots/", json=depot1)
    depot1_data = depot1_response.json()
    print(f"Depot 1 created: {depot1_data['name']} (ID: {depot1_data['id']})")
    
    depot2_response = requests.post(f"{BASE_URL}/depots/", json=depot2)
    depot2_data = depot2_response.json()
    print(f"Depot 2 created: {depot2_data['name']} (ID: {depot2_data['id']})")
    
    # Create couriers for each depot
    print("\nCreating couriers...")
    courier1 = {
        "name": "Иван Петров",
        "phone": "+7-900-123-4567",
        "depot_id": depot1_data['id'],
        "max_capacity": 15,
        "max_distance": 50.0
    }
    
    courier2 = {
        "name": "Алексей Смирнов",
        "phone": "+7-900-765-4321",
        "depot_id": depot1_data['id'],
        "max_capacity": 10,
        "max_distance": 30.0
    }
    
    courier3 = {
        "name": "Мария Иванова",
        "phone": "+7-900-111-2222",
        "depot_id": depot2_data['id'],
        "max_capacity": 12,
        "max_distance": 40.0
    }
    
    courier1_response = requests.post(f"{BASE_URL}/couriers/", json=courier1)
    courier1_data = courier1_response.json()
    print(f"Courier 1 created: {courier1_data['name']} (ID: {courier1_data['id']})")
    
    courier2_response = requests.post(f"{BASE_URL}/couriers/", json=courier2)
    courier2_data = courier2_response.json()
    print(f"Courier 2 created: {courier2_data['name']} (ID: {courier2_data['id']})")
    
    courier3_response = requests.post(f"{BASE_URL}/couriers/", json=courier3)
    courier3_data = courier3_response.json()
    print(f"Courier 3 created: {courier3_data['name']} (ID: {courier3_data['id']})")
    
    # Create orders
    print("\nCreating orders...")
    orders = [
        {
            "customer_name": "Петр Сидоров",
            "customer_phone": "+7-900-333-4444",
            "location": {
                "lat": 55.7450,
                "lng": 37.6300,
                "address": "Москва, ул. Тверская, 10"
            },
            "items_count": 2,
            "weight": 3.5
        },
        {
            "customer_name": "Елена Козлова",
            "customer_phone": "+7-900-555-6666",
            "location": {
                "lat": 55.7600,
                "lng": 37.6000,
                "address": "Москва, ул. Арбат, 20"
            },
            "items_count": 1,
            "weight": 1.2
        },
        {
            "customer_name": "Сергей Николаев",
            "customer_phone": "+7-900-777-8888",
            "location": {
                "lat": 55.7300,
                "lng": 37.6500,
                "address": "Москва, Покровский бульвар, 5"
            },
            "items_count": 3,
            "weight": 5.0
        },
        {
            "customer_name": "Ольга Михайлова",
            "customer_phone": "+7-900-999-0000",
            "location": {
                "lat": 55.6600,
                "lng": 37.6100,
                "address": "Москва, ул. Ленинский проспект, 30"
            },
            "items_count": 2,
            "weight": 2.8
        },
        {
            "customer_name": "Андрей Кузнецов",
            "customer_phone": "+7-900-222-3333",
            "location": {
                "lat": 55.6800,
                "lng": 37.6400,
                "address": "Москва, Варшавское шоссе, 15"
            },
            "items_count": 4,
            "weight": 6.5
        }
    ]
    
    for i, order in enumerate(orders):
        response = requests.post(f"{BASE_URL}/orders/", json=order)
        order_data = response.json()
        print(f"Order {i+1} created: {order_data['customer_name']} (ID: {order_data['id']})")
    
    # Get all orders
    print("\nRetrieving all orders...")
    orders_response = requests.get(f"{BASE_URL}/orders/")
    all_orders = orders_response.json()
    print(f"Total orders: {len(all_orders)}")
    
    # Optimize routes
    print("\nOptimizing routes...")
    optimize_response = requests.post(f"{BASE_URL}/routes/optimize")
    
    if optimize_response.status_code == 200:
        routes = optimize_response.json()
        print(f"Routes generated: {len(routes)}")
        
        for i, route in enumerate(routes):
            print(f"\nRoute {i+1} (ID: {route['id']}):")
            print(f"  Courier: {route['courier_id']}")
            print(f"  Depot: {route['depot_id']}")
            print(f"  Total Distance: {route['total_distance']:.2f} km")
            print(f"  Total Load: {route['total_load']} items")
            print(f"  Delivery Points: {len(route['points'])}")
            
            print("  Delivery Sequence:")
            for j, point in enumerate(route['points']):
                # Get order details
                order_response = requests.get(f"{BASE_URL}/orders/{point['order_id']}")
                order = order_response.json()
                print(f"    {j+1}. {order['customer_name']} - {order['location']['address']}")
    else:
        print(f"Error optimizing routes: {optimize_response.status_code}")
        print(optimize_response.text)
    
    # Get updated order statuses
    print("\nChecking updated order statuses...")
    orders_response = requests.get(f"{BASE_URL}/orders/")
    updated_orders = orders_response.json()
    
    for order in updated_orders:
        print(f"Order {order['id']}: {order['status']}")
        if order['courier_id']:
            print(f"  Assigned to courier: {order['courier_id']}")
        if order['depot_id']:
            print(f"  Assigned to depot: {order['depot_id']}")
    
    print("\nTest completed successfully!")


if __name__ == "__main__":
    test_api() 