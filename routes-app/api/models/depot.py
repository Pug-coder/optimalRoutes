from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class Depot(Base):
    __tablename__ = "depots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location_id = Column(String, ForeignKey("locations.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    location = relationship("Location")
    couriers = relationship("Courier", back_populates="depot")
    orders = relationship("Order", back_populates="depot") 