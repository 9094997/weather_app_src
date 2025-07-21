"""
Spatial Indexing System for Weather App
Optimizes location lookups and distance calculations using spatial partitioning.
"""
import math
from typing import Dict, List, Tuple, Optional
from functools import lru_cache

class SpatialIndex:
    """
    Spatial index for fast location lookups using grid-based partitioning.
    Replaces O(n) linear searches with O(1) average-case lookups.
    """
    
    def __init__(self, grid_size_degrees: float = 0.5):
        """
        Initialize spatial index with grid-based partitioning.
        
        Args:
            grid_size_degrees: Size of each grid cell in degrees (default: 0.5° ≈ 35 miles)
        """
        self.grid_size = grid_size_degrees
        self.spatial_grid = {}  # Grid cells containing location indices
        self.locations = []     # List of all locations
        self.coordinates = []   # List of all coordinates (lat, lon)
        self.location_data = []  # List of all location data
        
    def build_index(self, weather_data: Dict) -> None:
        """Build spatial index from weather data."""
        print("Building spatial index...")
        
        # Clear existing data
        self.spatial_grid.clear()
        self.locations.clear()
        self.coordinates.clear()
        self.location_data.clear()
        
        # Process all locations
        for idx, location_data in enumerate(weather_data.get('weather_data', [])):
            location = location_data['location']
            lat, lon = location['latitude'], location['longitude']
            
            # Store location data
            self.locations.append(location)
            self.coordinates.append((lat, lon))
            self.location_data.append(location_data)
            
            # Calculate grid cell
            grid_x = int(lat / self.grid_size)
            grid_y = int(lon / self.grid_size)
            grid_key = (grid_x, grid_y)
            
            # Add to spatial grid
            if grid_key not in self.spatial_grid:
                self.spatial_grid[grid_key] = []
            self.spatial_grid[grid_key].append(idx)
        
        print(f"Indexed {len(self.locations)} locations into {len(self.spatial_grid)} grid cells")
    
    @lru_cache(maxsize=10000)
    def find_closest_location(self, target_lat: float, target_lon: float, 
                            max_search_radius: int = 2) -> Tuple[Optional[Dict], float]:
        """
        Find closest weather location using spatial index.
        
        Args:
            target_lat: Target latitude
            target_lon: Target longitude
            max_search_radius: Maximum grid cells to search in each direction
            
        Returns:
            Tuple of (closest_location_data, distance_miles) or (None, float('inf'))
        """
        if not self.locations:
            return None, float('inf')
        
        # Calculate target grid cell
        target_grid_x = int(target_lat / self.grid_size)
        target_grid_y = int(target_lon / self.grid_size)
        
        closest_location = None
        min_distance = float('inf')
        
        # Search in expanding grid pattern (much faster than checking all locations)
        for radius in range(max_search_radius + 1):
            locations_found = []
            
            # Check grid cells in current radius
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    # Only check the perimeter for radius > 0
                    if radius > 0 and abs(dx) != radius and abs(dy) != radius:
                        continue
                    
                    grid_key = (target_grid_x + dx, target_grid_y + dy)
                    if grid_key in self.spatial_grid:
                        locations_found.extend(self.spatial_grid[grid_key])
            
            # Check distances for locations in current radius
            for location_idx in locations_found:
                location_lat, location_lon = self.coordinates[location_idx]
                distance = self._haversine_distance_miles(
                    target_lat, target_lon, location_lat, location_lon
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_location = self.location_data[location_idx]
            
            # If we found a close location, we can stop searching
            if closest_location and min_distance < self.grid_size * 111:  # Convert degrees to miles
                break
        
        return closest_location, min_distance
    
    @lru_cache(maxsize=5000)
    def _haversine_distance_miles(self, lat1: float, lon1: float, 
                                lat2: float, lon2: float) -> float:
        """Fast haversine distance calculation with caching."""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in miles
        return c * 3956
    
    def get_locations_within_radius(self, center_lat: float, center_lon: float, 
                                  radius_miles: float) -> List[Tuple[Dict, float]]:
        """
        Get all locations within a specified radius.
        
        Args:
            center_lat: Center latitude
            center_lon: Center longitude  
            radius_miles: Search radius in miles
            
        Returns:
            List of (location_data, distance) tuples within radius
        """
        # Convert radius to grid cells (approximate)
        radius_degrees = radius_miles / 69.0  # Rough conversion: 1 degree ≈ 69 miles
        grid_radius = int(math.ceil(radius_degrees / self.grid_size))
        
        center_grid_x = int(center_lat / self.grid_size)
        center_grid_y = int(center_lon / self.grid_size)
        
        locations_in_radius = []
        
        # Check all grid cells within the radius
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                grid_key = (center_grid_x + dx, center_grid_y + dy)
                
                if grid_key in self.spatial_grid:
                    for location_idx in self.spatial_grid[grid_key]:
                        location_lat, location_lon = self.coordinates[location_idx]
                        distance = self._haversine_distance_miles(
                            center_lat, center_lon, location_lat, location_lon
                        )
                        
                        if distance <= radius_miles:
                            locations_in_radius.append(
                                (self.location_data[location_idx], distance)
                            )
        
        # Sort by distance
        locations_in_radius.sort(key=lambda x: x[1])
        return locations_in_radius
    
    def get_statistics(self) -> Dict:
        """Get spatial index statistics for debugging."""
        if not self.spatial_grid:
            return {"error": "Index not built"}
        
        cell_sizes = [len(locations) for locations in self.spatial_grid.values()]
        
        return {
            "total_locations": len(self.locations),
            "total_grid_cells": len(self.spatial_grid),
            "average_locations_per_cell": sum(cell_sizes) / len(cell_sizes),
            "max_locations_per_cell": max(cell_sizes),
            "min_locations_per_cell": min(cell_sizes),
            "grid_size_degrees": self.grid_size,
            "cache_info": {
                "find_closest_location": self.find_closest_location.cache_info(),
                "haversine_distance": self._haversine_distance_miles.cache_info()
            }
        }

class DistanceCache:
    """Optimized distance caching system."""
    
    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.max_size = max_size
        self.spatial_index = SpatialIndex()
    
    def get_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Get distance with caching and optimization."""
        # Create cache key (rounded to avoid excessive cache entries)
        key = (round(lat1, 4), round(lon1, 4), round(lat2, 4), round(lon2, 4))
        
        if key in self.cache:
            return self.cache[key]
        
        # Calculate distance
        distance = self.spatial_index._haversine_distance_miles(lat1, lon1, lat2, lon2)
        
        # Cache with size limit
        if len(self.cache) < self.max_size:
            self.cache[key] = distance
        
        return distance
    
    def clear_cache(self):
        """Clear the distance cache."""
        self.cache.clear()
        self.spatial_index.find_closest_location.cache_clear()
        self.spatial_index._haversine_distance_miles.cache_clear()

# Global instances
spatial_index = SpatialIndex()
distance_cache = DistanceCache() 