from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID

from ..models import Courier, CourierCreate
from .depot import depots, route_optimizer

router = APIRouter()

# In-memory storage for demo purposes
couriers = {}


@router.post("/", response_model=Courier)
async def create_courier(courier: CourierCreate):
    """Create a new courier."""
    if courier.depot_id not in depots:
        raise HTTPException(
            status_code=404, 
            detail=f"Depot with id {courier.depot_id} not found"
        )
    
    new_courier = Courier(**courier.model_dump())
    couriers[new_courier.id] = new_courier
    route_optimizer.add_courier(new_courier)
    return new_courier


@router.get("/", response_model=List[Courier])
async def list_couriers():
    """List all couriers."""
    return list(couriers.values())


@router.get("/{courier_id}", response_model=Courier)
async def get_courier(courier_id: UUID):
    """Get a specific courier by ID."""
    if courier_id not in couriers:
        raise HTTPException(status_code=404, detail="Courier not found")
    return couriers[courier_id]


@router.delete("/{courier_id}")
async def delete_courier(courier_id: UUID):
    """Delete a courier."""
    if courier_id not in couriers:
        raise HTTPException(status_code=404, detail="Courier not found")
    del couriers[courier_id]
    return {"status": "success", "message": "Courier deleted"} 