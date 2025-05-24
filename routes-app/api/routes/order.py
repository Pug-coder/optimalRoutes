"""API-маршруты для работы с заказами."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Optional
from uuid import UUID

from ..services import OrderService
from ..schemas import OrderCreate, OrderResponse, OrderStatusUpdate, BulkOrderCreate
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Создаем роутер для заказов
router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def get_all_orders(db: AsyncSession = Depends(get_db)):
    """Получить список всех заказов."""
    try:
        orders = await OrderService.get_all_orders(db)
        return orders
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении списка заказов: {str(e)}"
        )


@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новый заказ."""
    try:
        order, _ = await OrderService.create_order(db, order_data)
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании заказа: {str(e)}"
        )


@router.post("/bulk", response_model=List[OrderResponse])
async def create_bulk_orders(
    bulk_data: BulkOrderCreate,
    db: AsyncSession = Depends(get_db)
):
    """Массово создать заказы."""
    try:
        orders = await OrderService.create_bulk_orders(db, bulk_data.orders)
        return orders
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при массовом создании заказов: {str(e)}"
        )


@router.post("/bulk/generate", response_model=List[OrderResponse])
async def generate_random_orders(
    count: int = 10,
    min_lat: float = 55.7,
    max_lat: float = 55.8,
    min_lng: float = 37.5,
    max_lng: float = 37.7,
    db: AsyncSession = Depends(get_db)
):
    """Сгенерировать случайные заказы."""
    try:
        if count <= 0 or count > 100:
            raise ValueError("Количество заказов должно быть от 1 до 100")
            
        orders = await OrderService.generate_random_orders(
            db, count, min_lat, max_lat, min_lng, max_lng
        )
        return orders
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации случайных заказов: {str(e)}"
        )


@router.get("/count", response_model=Dict[str, int])
async def count_orders(
    assigned: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Получить количество заказов с фильтрацией по статусу назначения."""
    try:
        count = await OrderService.count_orders(db, assigned)
        return {"count": count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при подсчете заказов: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о заказе по ID."""
    order = await OrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Заказ с ID {order_id} не найден"
        )
    return order


@router.delete("/{order_id}", response_model=Dict[str, bool])
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Удалить заказ по ID."""
    try:
        success = await OrderService.delete_order(db, order_id)
        return {"success": success}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"Ошибка: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при удалении заказа: {str(e)}"
        )


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    status_update: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить статус заказа."""
    try:
        order = await OrderService.update_order_status(
            db, order_id, status_update
        )
        if not order:
            raise HTTPException(
                status_code=404,
                detail=f"Заказ с ID {order_id} не найден"
            )
        return order
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка валидации: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обновлении статуса заказа: {str(e)}"
        ) 