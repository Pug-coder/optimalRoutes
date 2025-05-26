# Schemas for API 
from .location import LocationBase, LocationCreate, LocationResponse
from .depot import DepotBase, DepotCreate, DepotResponse
from .courier import (
    CourierBase, CourierCreate, CourierResponse, CourierUpdate
)
from .order import (
    OrderBase, OrderCreate, OrderResponse, OrderStatusUpdate, BulkOrderCreate
)
from .route import (
    RouteBase, RouteCreate, RouteResponse,
    RoutePointBase, RoutePointResponse,
    RouteWithLocationsResponse, OptimizationResponse
)

__all__ = [
    "LocationBase", "LocationCreate", "LocationResponse",
    "DepotBase", "DepotCreate", "DepotResponse",
    "CourierBase", "CourierCreate", "CourierResponse", "CourierUpdate",
    "OrderBase", "OrderCreate", "OrderResponse", "OrderStatusUpdate", 
    "BulkOrderCreate",
    "RouteBase", "RouteCreate", "RouteResponse",
    "RoutePointBase", "RoutePointResponse",
    "RouteWithLocationsResponse", "OptimizationResponse"
]