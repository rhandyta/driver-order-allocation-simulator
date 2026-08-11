import math
from typing import Tuple, Dict, Optional
from .models import Driver, Order, Market

def haversine(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate haversine distance in km between two (lat, lon) points."""
    R = 6371.0
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def normalize(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Normalize value to [0, 1] range."""
    if max_val <= min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

def get_time_slot(timestamp: str) -> str:
    """Extract time slot from timestamp string.
    morning: 06:00-10:59
    lunch: 11:00-13:59
    afternoon: 14:00-16:59
    evening: 17:00-20:59
    night: 21:00-05:59
    """
    # Parse hour from timestamp e.g. "2026-08-11 12:04:00"
    try:
        hour = int(timestamp[11:13])
        if 6 <= hour < 11:
            return "morning"
        elif 11 <= hour < 14:
            return "lunch"
        elif 14 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    except (ValueError, IndexError):
        return "morning"

def get_distance_bucket(distance_km: float) -> str:
    """Categorize distance into buckets."""
    if distance_km < 3:
        return "0-3km"
    elif distance_km < 7:
        return "3-7km"
    else:
        return "7km+"

def get_area(location: Tuple[float, float]) -> str:
    """Simple area mapping based on grid.
    Use a simple grid system to map coordinates to areas.
    For Bandung area (-6.85 to -6.95 lat, 107.55 to 107.65 lon).
    """
    lat, lon = location
    # Divide into grid areas
    if lat > -6.90:
        area_lat = "north"
    elif lat > -6.93:
        area_lat = "central"
    else:
        area_lat = "south"
    
    if lon < 107.60:
        area_lon = "west"
    elif lon < 107.63:
        area_lon = "central"
    else:
        area_lon = "east"
    
    # Map to named areas
    area_map = {
        ("north", "west"): "area_A",
        ("north", "central"): "area_A",
        ("north", "east"): "area_B",
        ("central", "west"): "area_A",
        ("central", "central"): "area_B",
        ("central", "east"): "area_B",
        ("south", "west"): "area_C",
        ("south", "central"): "area_C",
        ("south", "east"): "area_C",
    }
    return area_map.get((area_lat, area_lon), "area_B")

def demand_score(market: Market, max_ratio: float = 5.0) -> float:
    """Calculate demand/supply score.
    Higher ratio = more orders per driver = higher opportunity."""
    ratio = market.active_orders / max(market.active_drivers, 1)
    return normalize(ratio, 0.0, max_ratio)

def location_score(driver: Driver, order: Order, max_distance: float = 15.0) -> float:
    """Calculate location fitness. Closer = higher score."""
    dist = haversine(driver.location, order.pickup)
    return 1.0 - normalize(dist, 0.0, max_distance)

def service_fit(driver: Driver, order: Order) -> float:
    """Service type fitness including historical ratio."""
    if order.service_type not in driver.service_types:
        return 0.0
    # Use history if available
    services = driver.history.get("services", {})
    total = sum(services.values())
    if total == 0:
        return 1.0  # eligible but no history
    return services.get(order.service_type, 0) / total

def time_fit(driver: Driver, order: Order) -> float:
    """Time slot fitness based on driver's historical time slots."""
    slot = get_time_slot(order.timestamp)
    time_slots = driver.history.get("time_slots", {})
    total = sum(time_slots.values())
    if total == 0:
        return 0.5  # neutral if no history
    return time_slots.get(slot, 0) / total

def distance_fit(driver: Driver, order: Order) -> float:
    """Distance fitness based on driver's historical distance buckets."""
    bucket = get_distance_bucket(order.estimated_distance)
    buckets = driver.history.get("distance_buckets", {})
    total = sum(buckets.values())
    if total == 0:
        return 0.5
    return buckets.get(bucket, 0) / total

def eta_fit(driver: Driver, order: Order, max_eta: float = 45.0) -> float:
    """ETA fitness. Estimated based on haversine distance.
    Assume average speed of 20 km/h in city."""
    dist = haversine(driver.location, order.pickup)
    eta_minutes = (dist / 20.0) * 60.0  # 20 km/h average
    return 1.0 - normalize(eta_minutes, 0.0, max_eta)

def area_fit(driver: Driver, order: Order) -> float:
    """Area historical fitness."""
    area = get_area(order.pickup)
    areas = driver.history.get("areas", {})
    total = sum(areas.values())
    if total == 0:
        return 0.5
    return areas.get(area, 0) / total

def historical_fit(driver: Driver, order: Order, sub_weights) -> float:
    """Composite historical fitness.
    historical_fit = service * 0.35 + area * 0.30 + time * 0.20 + distance * 0.15
    """
    sf = service_fit(driver, order)
    af = area_fit(driver, order)
    tf = time_fit(driver, order)
    df = distance_fit(driver, order)
    return (
        sf * sub_weights.service
        + af * sub_weights.area
        + tf * sub_weights.time
        + df * sub_weights.distance
    )

def acceptance_score(driver: Driver) -> float:
    return driver.acceptance_rate

def completion_score(driver: Driver) -> float:
    return driver.completion_rate

def online_consistency(driver: Driver, max_hours: float = 120.0, max_days: int = 14) -> float:
    """Online consistency score."""
    hours_norm = normalize(driver.online_hours, 0, max_hours)
    days_norm = normalize(driver.online_days, 0, max_days)
    return (hours_norm + days_norm) / 2.0
