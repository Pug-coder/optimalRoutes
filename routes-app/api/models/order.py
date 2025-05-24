from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum

from core.database import Base


class OrderStatus(str, enum.Enum):
    """Enumeration of possible order statuses."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=True)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    items_count = Column(Integer, nullable=False, default=1)
    weight = Column(Float, nullable=False, default=1.0)
    status = Column(
        Enum(OrderStatus), 
        nullable=False, 
        default=OrderStatus.PENDING
    )
    created_at = Column(DateTime, server_default=func.now())
    
    # Внешние ключи
    courier_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("couriers.id"), 
        nullable=True
    )
    depot_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("depots.id"), 
        nullable=True
    )
    
    # Relationships
    location = relationship("Location")
    courier = relationship("Courier", back_populates="assigned_orders")
    depot = relationship("Depot", back_populates="orders")
    route_points = relationship("RoutePoint", back_populates="order") 