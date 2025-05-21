from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from uuid import UUID

from ..models import Order, OrderCreate, OrderStatus
from .depot import route_optimizer

router = APIRouter()

# In-memory storage for demo purposes
orders = {}


@router.post("/", response_model=Order)
async def create_order(order: OrderCreate):
    """Create a new order."""
    new_order = Order(**order.model_dump())
    orders[new_order.id] = new_order
    route_optimizer.add_order(new_order)
    return new_order


@router.get("/", response_model=List[Order])
async def list_orders(
    skip: int = 0, 
    limit: int = 100, 
    assigned: Optional[bool] = None
):
    """List all orders with optional filtering and pagination."""
    result = list(orders.values())
    
    # Filter by assignment status if requested
    if assigned is not None:
        if assigned:
            result = [order for order in result if order.status == "assigned"]
        else:
            result = [order for order in result if order.status != "assigned"]
    
    # Apply pagination
    return result[skip:skip+limit]


@router.get("/count")
async def count_orders(assigned: Optional[bool] = None):
    """Count orders with optional filtering."""
    if assigned is None:
        return {"count": len(orders)}
    
    # Count by assignment status
    if assigned:
        count = sum(1 for order in orders.values() if order.status == "assigned")
    else:
        count = sum(1 for order in orders.values() if order.status != "assigned")
    
    return {"count": count}


@router.post("/bulk", response_model=List[Order])
async def create_bulk_orders(orders_data: dict):
    """Create multiple orders at once."""
    new_orders = []
    
    for order_data in orders_data.get("orders", []):
        new_order = Order(**order_data)
        orders[new_order.id] = new_order
        route_optimizer.add_order(new_order)
        new_orders.append(new_order)
    
    return new_orders


@router.delete("/")
async def delete_all_orders():
    """Delete all orders."""
    orders.clear()
    return {"status": "success", "message": "All orders deleted"}


@router.get("/{order_id}", response_model=Order)
async def get_order(order_id: UUID):
    """Get a specific order by ID."""
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders[order_id]


@router.put("/{order_id}/status", response_model=Order)
async def update_order_status(order_id: UUID, status: OrderStatus):
    """Update the status of an order."""
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = orders[order_id]
    order.status = status
    return order


@router.delete("/{order_id}")
async def delete_order(order_id: UUID):
    """Delete an order."""
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    del orders[order_id]
    return {"status": "success", "message": "Order deleted"} 