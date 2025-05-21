from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID

from ..models import Depot, DepotCreate
from ..services import route_optimizer

router = APIRouter()

# In-memory storage for demo purposes
depots = {}


@router.post("/", response_model=Depot)
async def create_depot(depot: DepotCreate):
    """Create a new depot."""
    new_depot = Depot(**depot.model_dump())
    depots[new_depot.id] = new_depot
    route_optimizer.add_depot(new_depot)
    return new_depot


@router.get("/", response_model=List[Depot])
async def list_depots():
    """List all depots."""
    return list(depots.values())


@router.get("/{depot_id}", response_model=Depot)
async def get_depot(depot_id: UUID):
    """Get a specific depot by ID."""
    if depot_id not in depots:
        raise HTTPException(status_code=404, detail="Depot not found")
    return depots[depot_id]


@router.delete("/{depot_id}")
async def delete_depot(depot_id: UUID):
    """Delete a depot."""
    if depot_id not in depots:
        raise HTTPException(status_code=404, detail="Depot not found")
    del depots[depot_id]
    return {"status": "success", "message": "Depot deleted"} 