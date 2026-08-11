import os
import json
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime

from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from .scoring import calculate_score, get_score_breakdown
from .allocator import allocate_order
from .calibration import ScoringCalibrator
from .ml_model import AllocationDatasetGenerator, AllocationMLModel
from .simulation import generate_random_driver

app = FastAPI(
    title="Driver Order Allocation Platform API",
    description="REST API Gateway powering Management Control Center, Driver App, and Customer Booking App.",
    version="2.0.0"
)

# ==================== STATE MEMORY ENGINE ====================
class SystemState:
    def __init__(self):
        self.weather: str = "clear"
        self.surge_multiplier: float = 1.0
        self.weights: ScoringWeights = ScoringWeights()
        self.drivers: Dict[str, Driver] = {
            f"D{i+1:03d}": generate_random_driver(f"D{i+1:03d}") for i in range(15)
        }
        self.orders: Dict[str, Dict] = {}
        self.allocation_history: List[Dict] = []

state = SystemState()

# ==================== SCHEMAS ====================
class DriverSchema(BaseModel):
    id: str
    location: Tuple[float, float] = (-6.9147, 107.6098)
    service_types: List[str] = ["GoRide", "GoFood"]
    online: bool = True
    acceptance_rate: float = 0.95
    completion_rate: float = 0.98
    online_hours: float = 80.0
    online_days: int = 12
    history: Dict[str, Any] = Field(default_factory=dict)
    account_status: str = "active"
    device_status: str = "healthy"
    trip_settings: Dict[str, Any] = Field(default_factory=dict)

class OrderSchema(BaseModel):
    id: str
    service_type: str = "GoRide"
    pickup: Tuple[float, float] = (-6.9150, 107.6100)
    destination: Tuple[float, float] = (-6.9200, 107.6200)
    timestamp: str = "2026-08-11 12:30:00"
    estimated_distance: float = 3.5
    estimated_duration: float = 12.0

class MarketSchema(BaseModel):
    area: str = "area_B"
    active_drivers: int = 30
    active_orders: int = 20

class WeightsSchema(BaseModel):
    demand: float = 30.0
    history: float = 20.0
    service: float = 15.0
    time: float = 10.0
    distance: float = 10.0
    eta: float = 5.0
    completion_rate: float = 5.0
    acceptance_rate: float = 3.0
    online_consistency: float = 2.0

class AllocationRequest(BaseModel):
    order: OrderSchema
    drivers: List[DriverSchema]
    market: Optional[MarketSchema] = None
    weights: Optional[WeightsSchema] = None
    temperature: float = 5.0
    method: str = "softmax"
    eligibility_mode: str = "hard"

class ScoreBreakdownRequest(BaseModel):
    driver: DriverSchema
    order: OrderSchema
    market: Optional[MarketSchema] = None
    weights: Optional[WeightsSchema] = None

class CreateOrderRequest(BaseModel):
    service_type: str = "GoRide"
    pickup_lat: float = -6.9147
    pickup_lon: float = 107.6098
    dest_lat: float = -6.9250
    dest_lon: float = 107.6250
    customer_name: str = "Pengguna Bandung"

class MarketConfigRequest(BaseModel):
    weather: Optional[str] = "clear"
    surge_multiplier: Optional[float] = 1.0
    weights: Optional[WeightsSchema] = None

# Helper converters
def _to_driver(d: DriverSchema) -> Driver:
    return Driver(
        id=d.id, location=d.location, service_types=d.service_types,
        online=d.online, acceptance_rate=d.acceptance_rate,
        completion_rate=d.completion_rate, online_hours=d.online_hours,
        online_days=d.online_days, history=d.history,
        account_status=d.account_status, device_status=d.device_status,
        trip_settings=d.trip_settings
    )

def _to_order(o: OrderSchema) -> Order:
    return Order(
        id=o.id, service_type=o.service_type, pickup=o.pickup,
        destination=o.destination, timestamp=o.timestamp,
        estimated_distance=o.estimated_distance,
        estimated_duration=o.estimated_duration
    )

def _to_market(m: Optional[MarketSchema]) -> Market:
    if not m:
        return Market("area_B", len(state.drivers), len(state.orders))
    return Market(m.area, m.active_drivers, m.active_orders)

def _to_weights(w: Optional[WeightsSchema]) -> ScoringWeights:
    if not w:
        return state.weights
    return ScoringWeights(
        demand=w.demand, history=w.history, service=w.service,
        time=w.time, distance=w.distance, eta=w.eta,
        completion_rate=w.completion_rate, acceptance_rate=w.acceptance_rate,
        online_consistency=w.online_consistency
    )

# ==================== REST ENDPOINTS ====================
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "engine": "Driver Order Allocation Platform REST API"}

@app.get("/api/market-status")
def get_market_status():
    active_drivers = [
        {
            "id": d.id, "lat": d.location[0], "lon": d.location[1],
            "online": d.online, "rating": round(d.completion_rate * 5.0, 1),
            "service_types": d.service_types, "acceptance_rate": round(d.acceptance_rate * 100, 1)
        } for d in state.drivers.values()
    ]
    return {
        "weather": state.weather,
        "surge_multiplier": state.surge_multiplier,
        "active_drivers_count": sum(1 for d in state.drivers.values() if d.online),
        "total_orders_count": len(state.orders),
        "drivers": active_drivers,
        "recent_allocations": state.allocation_history[-10:]
    }

@app.post("/api/market-config")
def update_market_config(cfg: MarketConfigRequest):
    if cfg.weather is not None:
        state.weather = cfg.weather
        if cfg.weather == "rainy":
            state.surge_multiplier = 2.5
        elif cfg.weather == "heavy_rain":
            state.surge_multiplier = 3.5
        else:
            state.surge_multiplier = 1.0
    if cfg.surge_multiplier is not None and cfg.weather == "clear":
        state.surge_multiplier = cfg.surge_multiplier
    if cfg.weights:
        state.weights = _to_weights(cfg.weights)
    return {"status": "updated", "weather": state.weather, "surge_multiplier": state.surge_multiplier}

@app.get("/api/drivers")
def list_drivers():
    return [
        {
            "id": d.id, "lat": d.location[0], "lon": d.location[1],
            "online": d.online, "acceptance_rate": d.acceptance_rate,
            "completion_rate": d.completion_rate, "service_types": d.service_types
        } for d in state.drivers.values()
    ]

@app.post("/api/driver/toggle-online")
def toggle_driver_online(payload: Dict[str, Any]):
    driver_id = payload.get("driver_id", "D001")
    if driver_id not in state.drivers:
        state.drivers[driver_id] = generate_random_driver(driver_id)
    drv = state.drivers[driver_id]
    drv.online = not drv.online
    return {"driver_id": driver_id, "online": drv.online}

@app.post("/api/driver/update-location")
def update_driver_location(payload: Dict[str, Any]):
    driver_id = payload.get("driver_id", "D001")
    lat = float(payload.get("lat", -6.9147))
    lon = float(payload.get("lon", 107.6098))
    
    if driver_id not in state.drivers:
        state.drivers[driver_id] = generate_random_driver(driver_id)
    drv = state.drivers[driver_id]
    drv.location = (lat, lon)
    drv.online = True  # Ensure active online when updating position
    return {"driver_id": driver_id, "location": [lat, lon], "online": drv.online}

@app.post("/api/orders/create")
def create_customer_order(req: CreateOrderRequest):
    import math
    from .features import haversine
    
    order_id = f"ORD_{len(state.orders) + 1:04d}"
    dist = haversine((req.pickup_lat, req.pickup_lon), (req.dest_lat, req.dest_lon))

    dur = (dist / 20.0) * 60.0
    
    # Calculate fare
    base_fare = 8000.0 if req.service_type == "GoRide" else 10000.0
    per_km = 2500.0
    total_fare = (base_fare + dist * per_km) * state.surge_multiplier
    
    order_obj = Order(
        id=order_id, service_type=req.service_type,
        pickup=(req.pickup_lat, req.pickup_lon),
        destination=(req.dest_lat, req.dest_lon),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        estimated_distance=round(dist, 2),
        estimated_duration=round(dur, 1)
    )
    
    active_drivers = [d for d in state.drivers.values() if d.online]
    
    # If no online drivers, fallback to all drivers
    if not active_drivers:
        for d in state.drivers.values():
            d.online = True
        active_drivers = list(state.drivers.values())
        
    market_obj = Market("area_B", len(active_drivers), len(state.orders) + 1)
    
    alloc_res = allocate_order(order_obj, active_drivers, market_obj, state.weights, HistorySubWeights(), temperature=5.0)
    
    order_data = {
        "order_id": order_id,
        "customer_name": req.customer_name,
        "service_type": req.service_type,
        "pickup": [req.pickup_lat, req.pickup_lon],
        "destination": [req.dest_lat, req.dest_lon],
        "distance_km": round(dist, 2),
        "duration_min": round(dur, 1),
        "fare_idr": int(total_fare),
        "surge_multiplier": state.surge_multiplier,
        "status": "matched" if alloc_res else "unassigned",
        "assigned_driver_id": alloc_res.driver_id if alloc_res else None,
        "score": round(alloc_res.score, 2) if alloc_res else 0.0,
        "probability": round(alloc_res.probability, 4) if alloc_res else 0.0,
        "timestamp": order_obj.timestamp
    }
    
    state.orders[order_id] = order_data
    if alloc_res:
        state.allocation_history.append(order_data)
        try:
            from .database import MySQLDatabaseManager
            db = MySQLDatabaseManager()
            db.init_db()
            db.save_allocations([alloc_res])
        except Exception:
            pass

    return order_data


@app.post("/score")
def score_breakdown(req: ScoreBreakdownRequest):
    drv = _to_driver(req.driver)
    ord_ = _to_order(req.order)
    mkt = _to_market(req.market)
    wts = _to_weights(req.weights)
    sub_w = HistorySubWeights()
    
    score = calculate_score(drv, ord_, mkt, wts, sub_w)
    breakdown = get_score_breakdown(drv, ord_, mkt, wts, sub_w)
    
    return {
        "driver_id": drv.id, "order_id": ord_.id,
        "total_score": round(score, 2),
        "component_breakdown": {k: round(v, 4) for k, v in breakdown.items()}
    }

@app.post("/allocate")
def allocate(req: AllocationRequest):
    drivers = [_to_driver(d) for d in req.drivers]
    ord_ = _to_order(req.order)
    mkt = _to_market(req.market)
    wts = _to_weights(req.weights)
    sub_w = HistorySubWeights()
    
    result = allocate_order(
        ord_, drivers, mkt, wts, sub_w,
        temperature=req.temperature, method=req.method, eligibility_mode=req.eligibility_mode
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="No eligible candidate drivers found for this order.")
        
    return {
        "timestamp": result.timestamp, "order_id": result.order_id,
        "driver_id": result.driver_id, "score": round(result.score, 2),
        "probability": round(result.probability, 4), "result": result.result
    }

# Mount Web Directory for 3 Web App Portals
web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(web_dir):
    app.mount("/app", StaticFiles(directory=web_dir, html=True), name="web")
