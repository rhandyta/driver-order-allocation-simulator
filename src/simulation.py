import random
import json
import yaml
import os
import copy
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights, AllocationResult
from .eligibility import filter_eligible
from .scoring import score_all_candidates
from .allocator import allocate_order
from .history import HistoryManager, update_driver_after_order
from .market import generate_random_market, load_markets
from .features import get_area

SERVICE_TYPES = ["GoRide", "GoFood", "GoSend"]
AREAS = ["area_A", "area_B", "area_C"]

def load_config(config_path: str) -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def load_drivers(path: str) -> List[Driver]:
    with open(path, 'r') as f:
        data = json.load(f)
    drivers = []
    for d in data:
        drivers.append(Driver(
            id=d["id"],
            location=tuple(d["location"]),
            service_types=d["service_types"],
            online=d["online"],
            acceptance_rate=d["acceptance_rate"],
            completion_rate=d["completion_rate"],
            online_hours=d["online_hours"],
            online_days=d["online_days"],
            history=d["history"],
            account_status=d["account_status"],
            device_status=d["device_status"],
            trip_settings=d.get("trip_settings", {})
        ))
    return drivers

def load_orders(path: str) -> List[Order]:
    with open(path, 'r') as f:
        data = json.load(f)
    return [Order(
        id=o["id"],
        service_type=o["service_type"],
        pickup=tuple(o["pickup"]),
        destination=tuple(o["destination"]),
        timestamp=o["timestamp"],
        estimated_distance=o["estimated_distance"],
        estimated_duration=o["estimated_duration"]
    ) for o in data]

def generate_random_driver(driver_id: str, base_lat: float = -6.91, base_lon: float = 107.61) -> Driver:
    """Generate a random driver for simulation."""
    lat = base_lat + random.uniform(-0.05, 0.05)
    lon = base_lon + random.uniform(-0.05, 0.05)
    services = random.sample(SERVICE_TYPES, k=random.randint(1, len(SERVICE_TYPES)))
    
    # Random history
    history = {
        "services": {svc: random.randint(0, 50) for svc in services},
        "areas": {area: random.randint(0, 30) for area in random.sample(AREAS, k=random.randint(1, len(AREAS)))},
        "time_slots": {
            slot: random.randint(0, 25)
            for slot in ["morning", "lunch", "afternoon", "evening", "night"]
        },
        "distance_buckets": {
            "0-3km": random.randint(0, 30),
            "3-7km": random.randint(0, 25),
            "7km+": random.randint(0, 10)
        }
    }
    
    return Driver(
        id=driver_id,
        location=(lat, lon),
        service_types=services,
        online=True,
        acceptance_rate=random.uniform(0.7, 1.0),
        completion_rate=random.uniform(0.75, 1.0),
        online_hours=random.uniform(20, 120),
        online_days=random.randint(3, 14),
        history=history,
        account_status="active",
        device_status="healthy",
        trip_settings={}
    )

def generate_random_order(order_id: str, base_lat: float = -6.91, base_lon: float = 107.61, timestamp: Optional[str] = None) -> Order:
    """Generate a random order for simulation."""
    service = random.choice(SERVICE_TYPES)
    pickup_lat = base_lat + random.uniform(-0.04, 0.04)
    pickup_lon = base_lon + random.uniform(-0.04, 0.04)
    dest_lat = pickup_lat + random.uniform(-0.03, 0.03)
    dest_lon = pickup_lon + random.uniform(-0.03, 0.03)
    dist = random.uniform(1.0, 15.0)
    duration = dist * random.uniform(3, 8)  # 3-8 min per km
    
    if timestamp is None:
        hour = random.randint(6, 22)
        minute = random.randint(0, 59)
        timestamp = f"2026-08-11 {hour:02d}:{minute:02d}:00"
    
    return Order(
        id=order_id,
        service_type=service,
        pickup=(pickup_lat, pickup_lon),
        destination=(dest_lat, dest_lon),
        timestamp=timestamp,
        estimated_distance=round(dist, 1),
        estimated_duration=round(duration, 0)
    )

class Simulator:
    def __init__(self, config: Dict):
        self.config = config
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
        
        hist = config.get("history_sub_weights", {})
        self.sub_weights = HistorySubWeights(
            service=hist.get("service", 0.35),
            area=hist.get("area", 0.30),
            time=hist.get("time", 0.20),
            distance=hist.get("distance", 0.15)
        )
        
        alloc = config.get("allocation", {})
        self.temperature = alloc.get("temperature", 5.0)
        self.method = alloc.get("method", "softmax")
        
        self.norm_params = config.get("normalization", {})
        
        elig = config.get("eligibility", {})
        self.eligibility_mode = elig.get("device_status_mode", "hard")
        
        sim_conf = config.get("simulation", {})
        self.rolling_window = sim_conf.get("rolling_window_days", 14)
        
        self.history_manager = HistoryManager(self.rolling_window)
        self.results: List[AllocationResult] = []
    
    def run_day(self, day: int, drivers: List[Driver], orders: List[Order],
                markets: List[Market], weather: str = "clear",
                active_events: Optional[Dict] = None) -> List[AllocationResult]:
        day_results = []
        from .spatial_h3 import H3SpatialManager
        from .market_dynamic import DynamicMarketManager
        
        for order in orders:
            h3_cell = H3SpatialManager.coord_to_h3(order.pickup)
            market = DynamicMarketManager.generate_dynamic_market(
                timestamp=order.timestamp,
                h3_cell=h3_cell,
                base_drivers=len(drivers),
                base_orders=len(orders),
                service_type=order.service_type,
                weather=weather,
                active_events=active_events
            )
            
            result = allocate_order(
                order, drivers, market,
                self.weights, self.sub_weights,
                self.temperature, self.method,
                self.eligibility_mode, self.norm_params
            )

            
            if result:
                day_results.append(result)
                # Update driver history
                for d in drivers:
                    if d.id == result.driver_id:
                        completed = random.random() < d.completion_rate
                        self.history_manager.record_trip(d, order, day)
                        update_driver_after_order(d, order, completed)
                        if not completed:
                            result.result = "cancelled"
                        break
        
        # Update all drivers' rolling window history
        for d in drivers:
            self.history_manager.update_driver_history(d, day)
        
        self.results.extend(day_results)
        return day_results
    
    def run_simulation(self, days: int, num_drivers: int, orders_per_day: int,
                       markets: Optional[List[Market]] = None) -> List[AllocationResult]:
        # Generate drivers
        drivers = [generate_random_driver(f"D{i+1:03d}") for i in range(num_drivers)]
        self.drivers = drivers
        
        for day in range(days):
            # Generate orders for this day
            hour_base = 6
            orders = []
            for j in range(orders_per_day):
                hour = random.randint(6, 22)
                minute = random.randint(0, 59)
                ts = f"2026-08-{min(11+day, 31):02d} {hour:02d}:{minute:02d}:00"
                orders.append(generate_random_order(f"O{day*orders_per_day+j+1:04d}", timestamp=ts))
            
            # Generate or use markets
            if markets is None:
                day_markets = [generate_random_market(a) for a in AREAS]
            else:
                day_markets = markets
            
            self.run_day(day, drivers, orders, day_markets)
            print(f"  Day {day+1}/{days}: {len([r for r in self.results if r.timestamp.startswith(f'2026-08-{min(11+day, 31):02d}')])} orders allocated")
        
        return self.results
    
    def get_driver_statistics(self) -> Dict[str, Dict]:
        stats = {}
        for r in self.results:
            if r.driver_id not in stats:
                stats[r.driver_id] = {
                    "total_orders": 0,
                    "completed": 0,
                    "cancelled": 0,
                    "total_score": 0.0,
                    "avg_score": 0.0,
                    "avg_probability": 0.0
                }
            s = stats[r.driver_id]
            s["total_orders"] += 1
            if r.result == "allocated":
                s["completed"] += 1
            else:
                s["cancelled"] += 1
            s["total_score"] += r.score
        
        total_orders = len(self.results)
        for did, s in stats.items():
            s["avg_score"] = s["total_score"] / max(s["total_orders"], 1)
            s["order_probability"] = s["total_orders"] / max(total_orders, 1)
        
        return stats
    
    def save_results(self, output_dir: str = "results"):
        import pandas as pd
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "charts"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
        
        # Save allocation results to CSV
        if self.results:
            df = pd.DataFrame([
                {"timestamp": r.timestamp, "order_id": r.order_id, "driver_id": r.driver_id,
                 "score": round(r.score, 2), "probability": round(r.probability, 4), "result": r.result}
                for r in self.results
            ])
            df.to_csv(os.path.join(output_dir, "csv", "allocation.csv"), index=False)
            
            # Save to MySQL database if available
            try:
                from .database import MySQLDatabaseManager
                db = MySQLDatabaseManager()
                db.init_db()
                db.save_allocations(self.results)
            except Exception as e:
                pass

        
        # Save driver statistics
        stats = self.get_driver_statistics()
        if stats:
            rows = []
            for did, s in sorted(stats.items()):
                rows.append({
                    "driver_id": did,
                    "total_orders": s["total_orders"],
                    "completed": s["completed"],
                    "cancelled": s["cancelled"],
                    "avg_score": round(s["avg_score"], 2),
                    "order_probability": round(s["order_probability"] * 100, 2)
                })
            df_stats = pd.DataFrame(rows)
            df_stats.to_csv(os.path.join(output_dir, "csv", "driver_statistics.csv"), index=False)
        
        print(f"Results saved to {output_dir}/")
