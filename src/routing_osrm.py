import json
import urllib.request
import urllib.error
from typing import Tuple, Dict
from .features import haversine

class OSRMClient:
    """Open Source Routing Machine (OSRM) client for fetching real road network distances
    and navigation travel durations with in-memory caching and fallback handling.
    """
    
    _cache: Dict[Tuple[Tuple[float, float], Tuple[float, float]], Tuple[float, float]] = {}
    
    @classmethod
    def _round_coord(cls, coord: Tuple[float, float]) -> Tuple[float, float]:
        return (round(coord[0], 4), round(coord[1], 4))

    @classmethod
    def get_road_distance_and_duration(cls, origin: Tuple[float, float],
                                       destination: Tuple[float, float],
                                       timeout: float = 1.5) -> Tuple[float, float]:
        """Fetch (distance_km, duration_minutes) between origin and destination.
        
        Uses in-memory caching and falls back to Haversine * 1.3 road factor if offline.
        """
        k_orig = cls._round_coord(origin)
        k_dest = cls._round_coord(destination)
        cache_key = (k_orig, k_dest)
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
            
        if k_orig == k_dest:
            return 0.0, 0.0

        # Try OSRM API HTTP Request
        url = f"http://router.project-osrm.org/route/v1/driving/{k_orig[1]},{k_orig[0]};{k_dest[1]},{k_dest[0]}?overview=false"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "DriverAllocationSimulator/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        dist_km = route["distance"] / 1000.0
                        duration_min = route["duration"] / 60.0
                        
                        cls._cache[cache_key] = (dist_km, duration_min)
                        return dist_km, duration_min
        except Exception:
            pass  # Offline or timeout fallback
            
        # Fallback estimation: Haversine * 1.3 road network detour factor
        line_dist = haversine(origin, destination)
        dist_km = line_dist * 1.3
        duration_min = (dist_km / 20.0) * 60.0  # 20 km/h average city speed
        
        result = (round(dist_km, 2), round(duration_min, 1))
        cls._cache[cache_key] = result
        return result
