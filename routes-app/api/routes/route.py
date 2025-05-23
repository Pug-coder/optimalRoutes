from fastapi import APIRouter, HTTPException
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from ..models import Route
from ..services import route_optimizer, genetic_optimizer
from .order import orders
from .courier import couriers
from .depot import depots

router = APIRouter()

# In-memory storage for generated routes
routes = {}


class GeneticParams(BaseModel):
    population_size: Optional[int] = None
    generations: Optional[int] = None
    mutation_rate: Optional[float] = None
    elite_size: Optional[int] = None


class RoutingMode(BaseModel):
    use_real_roads: bool


@router.post("/optimize", response_model=List[Route])
async def optimize_routes():
    """Generate optimal routes for all pending orders using OR-Tools."""
    if not orders:
        raise HTTPException(
            status_code=400,
            detail="No orders available for optimization"
        )
        
    if not couriers:
        raise HTTPException(
            status_code=400,
            detail="No couriers available for optimization"
        )
    
    # Generate routes using the OR-Tools optimizer
    generated_routes = route_optimizer.optimize_routes()
    
    # Save the generated routes
    for route in generated_routes:
        routes[route.id] = route
        
        # Update order statuses
        for point in route.points:
            if point.order_id in orders:
                orders[point.order_id].status = "assigned"
                orders[point.order_id].courier_id = route.courier_id
                orders[point.order_id].depot_id = route.depot_id
    
    return generated_routes


@router.post("/optimize/genetic", response_model=List[Route])
async def optimize_routes_genetic(params: GeneticParams = None):
    """Generate optimal routes for all pending orders using Genetic Algorithm."""
    if not orders:
        raise HTTPException(
            status_code=400,
            detail="No orders available for optimization"
        )
        
    if not couriers:
        raise HTTPException(
            status_code=400,
            detail="No couriers available for optimization"
        )
    
    print(f"Starting genetic optimization with {len(orders)} orders and {len(couriers)} couriers")
    
    # Apply parameters if provided
    if params:
        if params.population_size is not None:
            genetic_optimizer.population_size = params.population_size
        if params.generations is not None:
            genetic_optimizer.max_generations = params.generations
        if params.mutation_rate is not None:
            genetic_optimizer.mutation_rate = params.mutation_rate
        if params.elite_size is not None:
            genetic_optimizer.elitism_rate = params.elite_size / 100.0  # Convert to percentage
    
    # Ensure the genetic optimizer has all the data
    genetic_optimizer.depots.clear()
    genetic_optimizer.couriers.clear()
    genetic_optimizer.orders.clear()
    
    # Add all depots to the genetic optimizer
    for depot_id, depot in depots.items():
        genetic_optimizer.add_depot(depot)
    
    # Add all couriers to the genetic optimizer
    for courier_id, courier in couriers.items():
        genetic_optimizer.add_courier(courier)
    
    # Add all pending orders to the genetic optimizer
    pending_order_count = 0
    for order_id, order in orders.items():
        if order.status == "pending":
            genetic_optimizer.add_order(order)
            pending_order_count += 1
    
    print(f"Genetic optimizer configured with {len(genetic_optimizer.depots)} depots, "
          f"{len(genetic_optimizer.couriers)} couriers, {pending_order_count} pending orders")
    
    # Generate routes using the Genetic Algorithm optimizer
    generated_routes = genetic_optimizer.optimize_routes()
    
    print(f"Genetic optimizer returned {len(generated_routes)} routes")
    
    # Filter out empty routes
    valid_routes = [route for route in generated_routes if route.points]
    
    if len(valid_routes) < len(generated_routes):
        print(f"Filtered out {len(generated_routes) - len(valid_routes)} empty routes")
    
    # Save the generated routes
    for route in valid_routes:
        routes[route.id] = route
        
        # Update order statuses
        for point in route.points:
            if point.order_id in orders:
                orders[point.order_id].status = "assigned"
                orders[point.order_id].courier_id = route.courier_id
                orders[point.order_id].depot_id = route.depot_id
    
    print(f"Genetic optimization completed with {len(valid_routes)} valid routes")
    return valid_routes


@router.get("/", response_model=List[Route])
async def list_routes():
    """List all generated routes."""
    return list(routes.values())


@router.get("/{route_id}", response_model=Route)
async def get_route(route_id: UUID):
    """Get a specific route by ID."""
    if route_id not in routes:
        raise HTTPException(status_code=404, detail="Route not found")
    return routes[route_id]


@router.get("/courier/{courier_id}", response_model=List[Route])
async def get_routes_by_courier(courier_id: UUID):
    """Get all routes assigned to a specific courier."""
    if courier_id not in couriers:
        raise HTTPException(status_code=404, detail="Courier not found")
        
    courier_routes = [
        route for route in routes.values() 
        if route.courier_id == courier_id
    ]
    
    return courier_routes 


@router.post("/reset")
async def reset_api():
    """Reset all API data (for testing purposes)."""
    # Clear all data
    routes.clear()
    orders.clear()
    couriers.clear()
    depots.clear()
    
    # Reset optimizers
    route_optimizer.reset()
    genetic_optimizer.reset()
    
    return {"status": "success", "message": "All API data has been reset"}


@router.post("/routing-mode", response_model=dict)
async def set_routing_mode(mode: RoutingMode):
    """Set the routing mode (real roads or direct distance)."""
    route_optimizer.use_real_roads = mode.use_real_roads
    genetic_optimizer.use_real_roads = mode.use_real_roads
    
    return {
        "success": True, 
        "message": f"Routing mode set to {'real roads' if mode.use_real_roads else 'direct distance'}"
    }


@router.get("/routing-mode", response_model=RoutingMode)
async def get_routing_mode():
    """Get the current routing mode."""
    return RoutingMode(use_real_roads=route_optimizer.use_real_roads) 