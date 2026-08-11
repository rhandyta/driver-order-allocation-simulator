from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

@dataclass
class Driver:
    id: str
    location: Tuple[float, float]  # (lat, lon)
    service_types: List[str]
    online: bool
    acceptance_rate: float  # 0.0 - 1.0
    completion_rate: float  # 0.0 - 1.0
    online_hours: float  # in last 14 days
    online_days: int  # in last 14 days
    history: Dict  # {services: {}, areas: {}, time_slots: {}, distance_buckets: {}}
    account_status: str  # "active" or "suspended"
    device_status: str  # "healthy" or "unhealthy"
    trip_settings: Dict = field(default_factory=dict)
    score: float = 0.0
    probability: float = 0.0

@dataclass
class Order:
    id: str
    service_type: str
    pickup: Tuple[float, float]
    destination: Tuple[float, float]
    timestamp: str  # "YYYY-MM-DD HH:MM:SS"
    estimated_distance: float  # km
    estimated_duration: float  # minutes

@dataclass
class Market:
    area: str
    active_drivers: int
    active_orders: int

@dataclass
class AllocationResult:
    timestamp: str
    order_id: str
    driver_id: str
    score: float
    probability: float
    result: str  # "allocated", "rejected", "cancelled"

@dataclass
class ScoringWeights:
    demand: float = 30.0
    history: float = 20.0
    service: float = 15.0
    time: float = 10.0
    distance: float = 10.0
    eta: float = 5.0
    completion_rate: float = 5.0
    acceptance_rate: float = 3.0
    online_consistency: float = 2.0

@dataclass
class HistorySubWeights:
    service: float = 0.35
    area: float = 0.30
    time: float = 0.20
    distance: float = 0.15

def load_weights_from_config(config: dict) -> Tuple[ScoringWeights, HistorySubWeights]:
    scoring = config.get("scoring_weights", {})
    weights = ScoringWeights(
        demand=scoring.get("demand", 30.0),
        history=scoring.get("history", 20.0),
        service=scoring.get("service", 15.0),
        time=scoring.get("time", 10.0),
        distance=scoring.get("distance", 10.0),
        eta=scoring.get("eta", 5.0),
        completion_rate=scoring.get("completion_rate", 5.0),
        acceptance_rate=scoring.get("acceptance_rate", 3.0),
        online_consistency=scoring.get("online_consistency", 2.0)
    )
    
    hist = config.get("history_sub_weights", {})
    sub_weights = HistorySubWeights(
        service=hist.get("service", 0.35),
        area=hist.get("area", 0.30),
        time=hist.get("time", 0.20),
        distance=hist.get("distance", 0.15)
    )
    return weights, sub_weights
