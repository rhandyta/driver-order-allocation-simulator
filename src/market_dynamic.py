import math
from typing import Dict, Tuple, Optional, List
from .models import Market
from .spatial_h3 import H3SpatialManager

class DynamicMarketManager:
    """Generates spatiotemporal dynamic market conditions including
    time-of-day demand curves, weather surge multipliers, and event hotspots.
    """
    
    @staticmethod
    def get_time_multiplier(hour: int, service_type: str = "GoRide") -> float:
        """Calculate time-of-day demand multiplier for specific service types."""
        if service_type == "GoFood":
            if 11 <= hour <= 13:
                return 2.0  # Lunch peak
            elif 18 <= hour <= 20:
                return 1.8  # Dinner peak
            elif 7 <= hour <= 9:
                return 1.2  # Breakfast
            elif hour >= 22 or hour < 6:
                return 0.4  # Night lull
            else:
                return 1.0
        elif service_type == "GoRide":
            if 7 <= hour <= 9:
                return 1.9  # Morning rush
            elif 17 <= hour <= 19:
                return 1.8  # Evening rush
            elif hour >= 22 or hour < 6:
                return 0.3  # Night lull
            else:
                return 1.0
        else:  # GoSend / General
            if 9 <= hour <= 16:
                return 1.5  # Business hours
            elif hour >= 21 or hour < 6:
                return 0.3
            else:
                return 1.0

    @staticmethod
    def get_weather_multiplier(weather: str = "clear") -> Tuple[float, float]:
        """Return (demand_multiplier, driver_speed_factor) based on weather condition."""
        weather = weather.lower()
        if weather == "rainy":
            return 2.5, 0.7  # +150% demand surge, -30% driver speed
        elif weather == "heavy_rain":
            return 3.5, 0.5  # +250% demand surge, -50% driver speed
        elif weather == "cloudy":
            return 1.2, 0.95
        else:  # "clear" / "sunny"
            return 1.0, 1.0

    @staticmethod
    def get_event_multiplier(h3_cell: str, active_events: Optional[Dict[str, float]] = None) -> float:
        """Return event surge multiplier for specific H3 cell hotspot."""
        if not active_events:
            return 1.0
        return active_events.get(h3_cell, 1.0)

    @classmethod
    def generate_dynamic_market(cls, timestamp: str, h3_cell: str,
                                base_drivers: int = 50, base_orders: int = 40,
                                service_type: str = "GoRide",
                                weather: str = "clear",
                                active_events: Optional[Dict[str, float]] = None) -> Market:
        """Generate a dynamic Market object incorporating time, weather, and event hotspots."""
        try:
            hour = int(timestamp[11:13])
        except (IndexError, ValueError):
            hour = 12
            
        t_mult = cls.get_time_multiplier(hour, service_type)
        w_demand_mult, w_speed_factor = cls.get_weather_multiplier(weather)
        e_mult = cls.get_event_multiplier(h3_cell, active_events)
        
        effective_orders = max(1, int(base_orders * t_mult * w_demand_mult * e_mult))
        effective_drivers = max(1, int(base_drivers * w_speed_factor))
        
        return Market(
            area=h3_cell,
            active_drivers=effective_drivers,
            active_orders=effective_orders
        )
