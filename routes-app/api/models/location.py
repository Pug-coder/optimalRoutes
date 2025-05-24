from sqlalchemy import Column, Float, String

import math
from core.database import Base


class Location(Base):
    __tablename__ = "locations"
    
    id = Column(String, primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=True)
    
    def distance_to(self, other):
        """Calculate distance to another location using Haversine formula (in km)."""
        if not other or self.latitude is None or self.longitude is None \
           or other.latitude is None or other.longitude is None:
            return 0.0
            
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        lat2_rad = math.radians(other.latitude)
        lon2_rad = math.radians(other.longitude)
        
        # Difference in coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = (math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) 
             * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth's radius in kilometers
        earth_radius_km = 6371.0
        
        # Calculate distance
        distance = earth_radius_km * c
        
        return distance 