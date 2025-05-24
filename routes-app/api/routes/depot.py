"""API-маршруты для работы с депо."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from uuid import UUID

from ..services import DepotService, route_optimizer
from ..schemas import DepotCreate, DepotResponse
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
        success = await DepotService.delete_depot(db, depot_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Ошибка: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении депо: {str(e)}"
        ) 