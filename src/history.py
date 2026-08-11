from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .models import Driver, Order
from .features import get_time_slot, get_distance_bucket, get_area
from .spatial_h3 import H3SpatialManager
import copy

class HistoryManager:
    """Manage per-day history entries and rolling window aggregation."""
    
    def __init__(self, window_size: int = 14):
        self.window_size = window_size
        # daily_records[driver_id][day_index] = {services: {}, areas: {}, h3_cells: {}, time_slots: {}, distance_buckets: {}}
        self.daily_records: Dict[str, Dict[int, Dict]] = {}
    
    def _empty_day_record(self) -> Dict:
        return {
            "services": {},
            "areas": {},
            "h3_cells": {},
            "time_slots": {},
            "distance_buckets": {}
        }
    
    def record_trip(self, driver: Driver, order: Order, day: int):
        """Record a completed trip for a driver on a given day."""
        if driver.id not in self.daily_records:
            self.daily_records[driver.id] = {}
        if day not in self.daily_records[driver.id]:
            self.daily_records[driver.id][day] = self._empty_day_record()
        
        rec = self.daily_records[driver.id][day]
        # Service
        svc = order.service_type
        rec["services"][svc] = rec["services"].get(svc, 0) + 1
        # Area
        area = get_area(order.pickup)
        rec["areas"][area] = rec["areas"].get(area, 0) + 1
        # H3 Cell
        h3_cell = H3SpatialManager.coord_to_h3(order.pickup)
        rec["h3_cells"][h3_cell] = rec["h3_cells"].get(h3_cell, 0) + 1
        # Time slot
        slot = get_time_slot(order.timestamp)
        rec["time_slots"][slot] = rec["time_slots"].get(slot, 0) + 1
        # Distance bucket
        bucket = get_distance_bucket(order.estimated_distance)
        rec["distance_buckets"][bucket] = rec["distance_buckets"].get(bucket, 0) + 1

    
    def aggregate_window(self, driver_id: str, current_day: int) -> Dict:
        """Aggregate history over rolling window [current_day - window_size + 1, current_day]."""
        agg = self._empty_day_record()
        start_day = max(0, current_day - self.window_size + 1)
        
        records = self.daily_records.get(driver_id, {})
        for day in range(start_day, current_day + 1):
            if day in records:
                for key in agg:
                    for sub_key, count in records[day][key].items():
                        agg[key][sub_key] = agg[key].get(sub_key, 0) + count
        return agg
    
    def update_driver_history(self, driver: Driver, current_day: int):
        """Update driver's history field with rolling window aggregate."""
        driver.history = self.aggregate_window(driver.id, current_day)

def update_driver_after_order(driver: Driver, order: Order, completed: bool = True):
    """Update driver state after receiving an order."""
    # Update acceptance/completion rates (simple moving update)
    total_trips = sum(driver.history.get("services", {}).values()) or 1
    
    if completed:
        # Update completion rate (weighted average)
        driver.completion_rate = (
            driver.completion_rate * (total_trips - 1) + 1.0
        ) / total_trips
    else:
        # Cancel: reduce completion rate
        driver.completion_rate = (
            driver.completion_rate * (total_trips - 1) + 0.0
        ) / total_trips
    
    # Acceptance rate (for accepted orders)
    driver.acceptance_rate = (
        driver.acceptance_rate * (total_trips - 1) + 1.0
    ) / total_trips
