from fastapi import APIRouter

from .routes import depot, order, courier, route
 
router = APIRouter()
router.include_router(depot.router, prefix="/depots", tags=["depots"])
router.include_router(order.router, prefix="/orders", tags=["orders"])
router.include_router(courier.router, prefix="/couriers", tags=["couriers"])
router.include_router(route.router, prefix="/routes", tags=["routes"]) 