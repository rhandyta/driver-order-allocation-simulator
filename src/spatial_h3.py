import h3
from typing import Tuple, List, Dict, Optional

class H3SpatialManager:
    """Manages Uber H3 Hexagonal Spatial Indexing for precise location matching,
    grid distance calculations, and neighborhood-aware spatial scoring.
    """
    
    DEFAULT_RESOLUTION = 8  # ~0.73 km² cell area
    
    @staticmethod
    def coord_to_h3(location: Tuple[float, float], res: int = DEFAULT_RESOLUTION) -> str:
        """Convert (lat, lon) coordinates to H3 Cell ID."""
        lat, lon = location
        return h3.latlng_to_cell(lat, lon, res)

    @staticmethod
    def get_h3_distance(cell1: str, cell2: str) -> int:
        """Calculate hexagonal grid step distance between two H3 cells."""
        try:
            return h3.grid_distance(cell1, cell2)
        except Exception:
            return 999

    @staticmethod
    def get_h3_neighbors(cell: str, k: int = 1) -> List[str]:
        """Get k-ring neighbor cells around a central H3 cell."""
        try:
            return list(h3.grid_disk(cell, k))
        except Exception:
            return [cell]

    @classmethod
    def calculate_h3_area_fit(cls, driver_history: Dict, order_pickup_loc: Tuple[float, float], res: int = DEFAULT_RESOLUTION) -> float:
        """Calculate spatial historical fit using H3 cells and neighborhood weighting.
        
        Exact H3 cell match: 1.0 weight
        1st-ring neighbor match: 0.5 weight
        2nd-ring neighbor match: 0.25 weight
        """
        pickup_cell = cls.coord_to_h3(order_pickup_loc, res)
        h3_history = driver_history.get("h3_cells", {})
        
        # Fallback to legacy area mapping if no H3 history exists yet
        if not h3_history:
            return 0.5
            
        total_trips = sum(h3_history.values())
        if total_trips == 0:
            return 0.5
            
        score = 0.0
        # Exact cell
        exact_trips = h3_history.get(pickup_cell, 0)
        score += (exact_trips / total_trips) * 1.0
        
        # 1st-ring neighbors
        ring_1 = set(cls.get_h3_neighbors(pickup_cell, 1)) - {pickup_cell}
        r1_trips = sum(h3_history.get(c, 0) for c in ring_1)
        score += (r1_trips / total_trips) * 0.5
        
        # 2nd-ring neighbors
        ring_2 = set(cls.get_h3_neighbors(pickup_cell, 2)) - ring_1 - {pickup_cell}
        r2_trips = sum(h3_history.get(c, 0) for c in ring_2)
        score += (r2_trips / total_trips) * 0.25
        
        return min(1.0, score)
