from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class Courier(Base):
    __tablename__ = "couriers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    depot_id = Column(UUID(as_uuid=True), ForeignKey("depots.id"), nullable=False)
    max_capacity = Column(Integer, nullable=False, default=10)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    depot = relationship("Depot", back_populates="couriers")
    routes = relationship("Route", back_populates="courier")
    assigned_orders = relationship("Order", back_populates="courier") 