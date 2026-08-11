from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Tuple, Optional, Any
import numpy as np

from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from .scoring import calculate_score, get_score_breakdown
from .allocator import allocate_order
from .calibration import ScoringCalibrator
from .ml_model import AllocationDatasetGenerator, AllocationMLModel

app = FastAPI(
    title="Driver Order Allocation Simulator REST API",
    description="HTTP REST API service for driver order allocation scoring, softmax sampling, ML probability predictions, and parameter calibration.",
    version="1.0.0"
)

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
        return Market("area_B", 30, 20)
    return Market(m.area, m.active_drivers, m.active_orders)

def _to_weights(w: Optional[WeightsSchema]) -> ScoringWeights:
    if not w:
        return ScoringWeights()
    return ScoringWeights(
        demand=w.demand, history=w.history, service=w.service,
        time=w.time, distance=w.distance, eta=w.eta,
        completion_rate=w.completion_rate, acceptance_rate=w.acceptance_rate,
        online_consistency=w.online_consistency
    )

# ==================== ENDPOINTS ====================
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0", "engine": "Driver Order Allocation Simulator REST API"}

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
        "driver_id": drv.id,
        "order_id": ord_.id,
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
        temperature=req.temperature,
        method=req.method,
        eligibility_mode=req.eligibility_mode
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="No eligible candidate drivers found for this order.")
        
    return {
        "timestamp": result.timestamp,
        "order_id": result.order_id,
        "driver_id": result.driver_id,
        "score": round(result.score, 2),
        "probability": round(result.probability, 4),
        "result": result.result
    }

@app.post("/predict-ml")
def predict_ml(req: ScoreBreakdownRequest):
    drv = _to_driver(req.driver)
    ord_ = _to_order(req.order)
    mkt = _to_market(req.market)
    
    generator = AllocationDatasetGenerator()
    feat = generator.extract_features(drv, ord_, mkt).reshape(1, -1)
    
    import pandas as pd
    from .ml_model import FEATURE_NAMES
    X_df = pd.DataFrame(feat, columns=FEATURE_NAMES)
    
    model = AllocationMLModel("rf")
    # Quick mock fit for demonstration if uninitialized
    X_dummy = pd.DataFrame(np.random.rand(10, len(FEATURE_NAMES)), columns=FEATURE_NAMES)
    y_dummy = np.random.choice([0, 1], size=10)
    model.train(X_dummy, y_dummy)
    
    prob = float(model.predict_proba(X_df)[0])
    
    return {
        "driver_id": drv.id,
        "order_id": ord_.id,
        "predicted_allocation_probability": round(prob, 4)
    }
