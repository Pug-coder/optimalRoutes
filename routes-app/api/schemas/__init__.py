# Schemas for API 
from .location import LocationBase, LocationCreate, LocationResponse
from .depot import DepotBase, DepotCreate, DepotCreateWithAddress, DepotResponse
from .courier import (
    CourierBase, CourierCreate, CourierResponse, CourierUpdate
)
from .order import (
    OrderBase, OrderCreate, OrderCreateWithAddress, OrderResponse, 
    OrderStatusUpdate, BulkOrderCreate
)
from .route import (
    RouteBase, RouteCreate, RouteResponse,
    RoutePointBase, RoutePointResponse,
    RouteWithLocationsResponse, OptimizationResponse
)
from .geocoding import (
    GeocodeRequest, GeocodeResponse, 
    ReverseGeocodeRequest, ReverseGeocodeResponse
)


__all__ = [
    "LocationBase", "LocationCreate", "LocationResponse",
    "DepotBase", "DepotCreate", "DepotCreateWithAddress", "DepotResponse",
    "CourierBase", "CourierCreate", "CourierResponse", "CourierUpdate",
    "OrderBase", "OrderCreate", "OrderCreateWithAddress", "OrderResponse", 
    "OrderStatusUpdate", "BulkOrderCreate",
    "RouteBase", "RouteCreate", "RouteResponse",
    "RoutePointBase", "RoutePointResponse",
    "RouteWithLocationsResponse", "OptimizationResponse",
    "GeocodeRequest", "GeocodeResponse", 
    "ReverseGeocodeRequest", "ReverseGeocodeResponse"
]