"""API-маршруты для работы с депо."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from uuid import UUID

from ..services import DepotService
from ..schemas import (
    DepotCreate, DepotCreateWithAddress, DepotResponse
)
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Создаем роутер для депо
router = APIRouter()


@router.get("/", response_model=List[DepotResponse])
async def get_all_depots(db: AsyncSession = Depends(get_db)):
    """Получить список всех депо."""
    try:
        depots = await DepotService.get_all_depots(db)
        return depots
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении списка депо: {str(e)}"
        )


@router.post("/", response_model=DepotResponse)
async def create_depot(
    depot_data: DepotCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новое депо."""
    try:
        depot, _ = await DepotService.create_depot(db, depot_data)
        return depot
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании депо: {str(e)}"
        )


@router.post("/with-address", response_model=DepotResponse)
async def create_depot_with_address(
    depot_data: DepotCreateWithAddress,
    db: AsyncSession = Depends(get_db)
):
    """Создать новое депо с автоматическим геокодированием адреса."""
    try:
        depot, _ = await DepotService.create_depot_with_address(db, depot_data)
        return depot
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании депо: {str(e)}"
        )


@router.get("/{depot_id}", response_model=DepotResponse)
async def get_depot(
    depot_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о депо по ID."""
    depot = await DepotService.get_depot(db, depot_id)
    if not depot:
        raise HTTPException(
            status_code=404,
            detail=f"Депо с ID {depot_id} не найдено"
        )
    return depot


@router.delete("/{depot_id}", response_model=Dict[str, bool])
async def delete_depot(
    depot_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удалить депо по ID."""
    try:
        print(f"Attempting to delete depot with ID: {depot_id} "
              f"(type: {type(depot_id)})")
        
        # First check if depot exists by getting it
        depot = await DepotService.get_depot(db, depot_id)
        if depot:
            print(f"Found depot: {depot.name} with ID {depot.id}")
        else:
            print(f"Depot with ID {depot_id} not found in get_depot")
            
        success = await DepotService.delete_depot(db, depot_id)
        print(f"Depot deletion result: {success}")
        return {"success": success}
    except ValueError as e:
        print(f"ValueError during depot deletion: {str(e)}")
        error_message = str(e)
        if "not found" in error_message:
            # Depot doesn't exist
            raise HTTPException(
                status_code=404,
                detail=f"Ошибка: {error_message}"
            )
        else:
            # Business logic error (depot has related entities)
            raise HTTPException(
                status_code=409,
                detail=f"Ошибка: {error_message}"
            )
    except Exception as e:
        print(f"Unexpected error during depot deletion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении депо: {str(e)}"
        ) 