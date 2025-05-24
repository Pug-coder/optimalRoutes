from .location import Location
from .depot import Depot
from .courier import Courier
from .order import Order, OrderStatus
from .route import Route, RoutePoint

# Импортируем все модели для миграций Alembic
__all__ = [
    "Location",
    "Depot",
    "Courier",
    "Order",
    "OrderStatus",
    "Route",
    "RoutePoint"
] 