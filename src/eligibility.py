from typing import List
from .models import Driver, Order

def is_eligible(driver: Driver, order: Order, mode: str = "hard") -> bool:
    """Check if driver is eligible for the order.
    
    Hard constraints:
    - Must be online
    - Account must be active
    - Must support the service type
    
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
    return True

def filter_eligible(drivers: List[Driver], order: Order, mode: str = "hard") -> List[Driver]:
    return [d for d in drivers if is_eligible(d, order, mode)]
