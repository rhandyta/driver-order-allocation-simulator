from enum import Enum
import math
from typing import Tuple, List, Dict, Optional
from .models import Driver, Order, Market, AllocationResult, ScoringWeights, HistorySubWeights
from .features import haversine, get_area
from .eligibility import filter_eligible
from .scoring import score_all_candidates
from .allocator import allocate_order
from .history import HistoryManager, update_driver_after_order

class DriverState(str, Enum):
    IDLE = "IDLE"
    EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP"
    TRIP_IN_PROGRESS = "TRIP_IN_PROGRESS"
    OFFLINE = "OFFLINE"

class MicroDriver:
    """Wraps a Driver with continuous position interpolation and state machine logic."""
    
    def __init__(self, driver: Driver):
        self.driver = driver
        self.state = DriverState.IDLE if driver.online else DriverState.OFFLINE
        self.current_location = driver.location
        self.route_start: Optional[Tuple[float, float]] = None
        self.route_end: Optional[Tuple[float, float]] = None
        self.travel_start_time: float = 0.0
        self.travel_duration: float = 0.0
        self.assigned_order: Optional[Order] = None


    def start_travel(self, destination: Tuple[float, float], duration_seconds: float, current_time: float, next_state: DriverState):
        self.route_start = self.current_location
        self.route_end = destination
        self.travel_start_time = current_time
        self.travel_duration = max(1.0, duration_seconds)
        self.state = next_state

    def update_position(self, current_time: float) -> Tuple[float, float]:
        """Interpolate current coordinates based on elapsed travel time."""
        if self.state in (DriverState.IDLE, DriverState.OFFLINE) or not self.route_start or not self.route_end:
            return self.current_location

        elapsed = current_time - self.travel_start_time
        fraction = min(1.0, max(0.0, elapsed / self.travel_duration))

        lat = self.route_start[0] + fraction * (self.route_end[0] - self.route_start[0])
        lon = self.route_start[1] + fraction * (self.route_end[1] - self.route_start[1])

        self.current_location = (lat, lon)
        self.driver.location = self.current_location
        return self.current_location

class MicroSimulationEngine:
    """Event-driven micro-simulation engine managing discrete time ticks
    and real-time driver movement vectors.
    """
    
    def __init__(self, drivers: List[Driver], config: Dict):
        self.config = config
        self.micro_drivers = [MicroDriver(d) for d in drivers]
        self.clock_seconds: float = 0.0
        self.history_manager = HistoryManager()
        self.allocation_log: List[AllocationResult] = []
        
        scoring = config.get("scoring_weights", {})
        self.weights = ScoringWeights(
            demand=scoring.get("demand", 30),
            history=scoring.get("history", 20),
            service=scoring.get("service", 15),
            time=scoring.get("time", 10),
            distance=scoring.get("distance", 10),
            eta=scoring.get("eta", 5),
            completion_rate=scoring.get("completion_rate", 5),
            acceptance_rate=scoring.get("acceptance_rate", 3),
            online_consistency=scoring.get("online_consistency", 2)
        )
        self.sub_weights = HistorySubWeights()

    def get_idle_drivers(self) -> List[Driver]:
        return [md.driver for md in self.micro_drivers if md.state == DriverState.IDLE and md.driver.online]

    def tick(self, delta_seconds: float = 5.0, new_orders: Optional[List[Order]] = None):
        """Advance simulation clock by delta_seconds and process driver state transitions."""
        self.clock_seconds += delta_seconds
        
        # 1. Update driver positions and state transitions
        for md in self.micro_drivers:
            md.update_position(self.clock_seconds)
            
            if md.state == DriverState.EN_ROUTE_PICKUP:
                if self.clock_seconds >= md.travel_start_time + md.travel_duration:
                    # Arrived at pickup -> start trip to destination
                    if md.assigned_order:
                        trip_dist = md.assigned_order.estimated_distance
                        trip_duration_sec = (trip_dist / 20.0) * 3600.0  # 20 km/h
                        md.start_travel(md.assigned_order.destination, trip_duration_sec, self.clock_seconds, DriverState.TRIP_IN_PROGRESS)
                    else:
                        md.state = DriverState.IDLE
                        
            elif md.state == DriverState.TRIP_IN_PROGRESS:
                if self.clock_seconds >= md.travel_start_time + md.travel_duration:
                    # Arrived at destination -> complete trip and become IDLE
                    if md.assigned_order:
                        self.history_manager.record_trip(md.driver, md.assigned_order, day=1)
                        update_driver_after_order(md.driver, md.assigned_order, completed=True)
                    md.assigned_order = None
                    md.state = DriverState.IDLE

        # 2. Process new incoming orders
        if new_orders:
            for order in new_orders:
                idle_drivers = self.get_idle_drivers()
                if not idle_drivers:
                    continue
                
                market = Market("area_B", len(idle_drivers), len(new_orders))
                result = allocate_order(
                    order, idle_drivers, market,
                    self.weights, self.sub_weights,
                    temperature=self.config.get("allocation", {}).get("temperature", 5.0),
                    method=self.config.get("allocation", {}).get("method", "softmax")
                )
                
                if result:
                    self.allocation_log.append(result)
                    # Assign order to winning micro driver
                    for md in self.micro_drivers:
                        if md.driver.id == result.driver_id:
                            md.assigned_order = order
                            # Calculate pickup travel duration (assuming 20 km/h)
                            dist = haversine(md.current_location, order.pickup)
                            pickup_duration_sec = (dist / 20.0) * 3600.0
                            md.start_travel(order.pickup, pickup_duration_sec, self.clock_seconds, DriverState.EN_ROUTE_PICKUP)
                            break
