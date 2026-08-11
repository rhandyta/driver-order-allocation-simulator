from typing import List
from .models import Driver, Order
from .features import haversine, get_area

MAX_OPERATIONAL_PICKUP_DISTANCE = 15.0  # Maximum operational pickup radius in km

def is_eligible(driver: Driver, order: Order, mode: str = "hard") -> bool:
    """Check if driver is eligible for the order.
    
    Hard constraints:
    - Must be online
    - Account must be active
    - Must support the service type
    - Must be within maximum operational pickup distance (default 15.0 km)
    - Trip settings constraints (if configured): max_pickup_distance, destination_area
    """
    if not driver.online:
        return False
    if driver.account_status != "active":
        return False
    if order.service_type not in driver.service_types:
        return False
    if mode == "hard" and driver.device_status != "healthy":
        return False
    
    # Distance boundary check
    dist = haversine(driver.location, order.pickup)
    max_dist = MAX_OPERATIONAL_PICKUP_DISTANCE
    
    if driver.trip_settings:
        custom_max = driver.trip_settings.get("max_pickup_distance")
        if custom_max is not None:
            max_dist = custom_max
            
    if dist > max_dist:
        return False

    # Check destination area preference if configured
    if driver.trip_settings:
        pref_dest_area = driver.trip_settings.get("destination_area")
        if pref_dest_area is not None:
            order_dest_area = get_area(order.destination)
            if order_dest_area != pref_dest_area:
                return False

    return True


def filter_eligible(drivers: List[Driver], order: Order, mode: str = "hard") -> List[Driver]:
    return [d for d in drivers if is_eligible(d, order, mode)]

