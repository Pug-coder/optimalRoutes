from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class RoutePoint(Base):
    __tablename__ = "route_points"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    estimated_arrival = Column(DateTime, nullable=True)
    
    # Relationships
    route = relationship("Route", back_populates="points")
    order = relationship("Order", back_populates="route_points")


class Route(Base):
    __tablename__ = "routes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    courier_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("couriers.id"), 
        nullable=False
    )
    depot_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("depots.id"), 
        nullable=False
    )
    created_at = Column(DateTime, server_default=func.now())
    total_distance = Column(Float, default=0.0)
    total_load = Column(Integer, default=0)
    total_weight = Column(Float, default=0.0)
    
    # Relationships
    courier = relationship("Courier", back_populates="routes")
    depot = relationship("Depot")
    points = relationship(
        "RoutePoint", 
        back_populates="route", 
        order_by="RoutePoint.sequence"
    ) 