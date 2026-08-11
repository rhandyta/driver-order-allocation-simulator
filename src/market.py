import json
import random
from typing import List, Dict, Optional
from .models import Market

def load_markets(path: str) -> List[Market]:
    """Load market configurations from JSON file."""
    with open(path, 'r') as f:
        data = json.load(f)
    return [Market(area=m["area"], active_drivers=m["active_drivers"], active_orders=m["active_orders"]) for m in data]

def get_market_for_area(area: str, markets: List[Market]) -> Optional[Market]:
    """Get market conditions for a specific area."""
    for m in markets:
        if m.area == area:
            return m
    return None

def generate_random_market(area: str, driver_range: tuple = (20, 150), order_range: tuple = (10, 200)) -> Market:
    """Generate random market conditions for simulation."""
    return Market(
        area=area,
        active_drivers=random.randint(*driver_range),
        active_orders=random.randint(*order_range)
    )

def generate_markets_for_areas(areas: List[str], driver_range=(20,150), order_range=(10,200)) -> List[Market]:
    return [generate_random_market(a, driver_range, order_range) for a in areas]
