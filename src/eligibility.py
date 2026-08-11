from typing import List
from .models import Driver, Order
from .features import haversine, get_area

def is_eligible(driver: Driver, order: Order, mode: str = "hard") -> bool:
    """Check if driver is eligible for the order.
    
    Hard constraints:
    - Must be online
    - Account must be active
    - Must support the service type
    - Trip settings constraints (if configured)
      * max_pickup_distance (km)
      * destination_area preference
    
    In 'hard' mode, device_status must be healthy.
    In 'soft' mode, device_status is not a filter (handled in scoring).
    """
    if not driver.online:
        return False
    if driver.account_status != "active":
        return False
    if order.service_type not in driver.service_types:
        return False
    if mode == "hard" and driver.device_status != "healthy":
        return False
    
    # Check trip settings constraints if present
    if driver.trip_settings:
        max_dist = driver.trip_settings.get("max_pickup_distance")
        if max_dist is not None:
            dist = haversine(driver.location, order.pickup)
            if dist > max_dist:
                return False
        
        pref_dest_area = driver.trip_settings.get("destination_area")
        if pref_dest_area is not None:
            order_dest_area = get_area(order.destination)
            if order_dest_area != pref_dest_area:
                return False

    return True

def filter_eligible(drivers: List[Driver], order: Order, mode: str = "hard") -> List[Driver]:
    return [d for d in drivers if is_eligible(d, order, mode)]

