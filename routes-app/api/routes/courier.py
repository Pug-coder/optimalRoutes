"""API-маршруты для работы с курьерами."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from uuid import UUID

from ..services import CourierService
from ..schemas import CourierCreate, CourierResponse, CourierUpdate
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Создаем роутер для курьеров
router = APIRouter()


@router.get("/", response_model=List[CourierResponse])
async def get_all_couriers(db: AsyncSession = Depends(get_db)):
    """Получить список всех курьеров."""
    try:
        couriers = await CourierService.get_all_couriers(db)
        return couriers
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении списка курьеров: {str(e)}"
        )


@router.post("/", response_model=CourierResponse)
async def create_courier(
    courier_data: CourierCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать нового курьера."""
    try:
        courier = await CourierService.create_courier(db, courier_data)
        return courier
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании курьера: {str(e)}"
        )


@router.get("/{courier_id}", response_model=CourierResponse)
async def get_courier(
    courier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о курьере по ID."""
    courier = await CourierService.get_courier(db, courier_id)
    if not courier:
        raise HTTPException(
            status_code=404,
            detail=f"Курьер с ID {courier_id} не найден"
        )
    return courier


@router.patch("/{courier_id}", response_model=CourierResponse)
async def update_courier(
    courier_id: UUID,
    courier_update: CourierUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить информацию о курьере."""
    try:
        print(f"PATCH request for courier {courier_id}")
        print(f"Update data: {courier_update}")
        print(f"Update data dict: {courier_update.model_dump()}")
        
        updated_courier = await CourierService.update_courier(
            db=db,
            courier_id=courier_id,
            name=courier_update.name,
            phone=courier_update.phone,
            max_capacity=courier_update.max_capacity,
            max_distance=courier_update.max_distance,
            depot_id=courier_update.depot_id
        )
        if not updated_courier:
            raise HTTPException(
                status_code=404,
                detail=f"Курьер с ID {courier_id} не найден"
            )
        return updated_courier
    except ValueError as e:
        print(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении курьера: {str(e)}"
        )


@router.delete("/{courier_id}", response_model=Dict[str, bool])
async def delete_courier(
    courier_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удалить курьера по ID."""
    try:
        success = await CourierService.delete_courier(db, courier_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Ошибка: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении курьера: {str(e)}"
        ) 