import pytest
from src.market_dynamic import DynamicMarketManager
from src.models import Market

def test_time_multipliers():
    # GoFood lunch surge
    assert DynamicMarketManager.get_time_multiplier(12, "GoFood") == 2.0
    # GoFood dinner surge
    assert DynamicMarketManager.get_time_multiplier(19, "GoFood") == 1.8
    # GoRide morning rush
    assert DynamicMarketManager.get_time_multiplier(8, "GoRide") == 1.9
    # Night lull
    assert DynamicMarketManager.get_time_multiplier(23, "GoRide") == 0.3

def test_weather_multipliers():
    demand_clear, speed_clear = DynamicMarketManager.get_weather_multiplier("clear")
    assert demand_clear == 1.0
    assert speed_clear == 1.0
    
    demand_rain, speed_rain = DynamicMarketManager.get_weather_multiplier("rainy")
    assert demand_rain == 2.5
    assert speed_rain == 0.7

def test_event_multipliers():
    cell = "888c1479e1fffff"
    active_events = {cell: 4.0}
    
    assert DynamicMarketManager.get_event_multiplier(cell, active_events) == 4.0
    assert DynamicMarketManager.get_event_multiplier("other_cell", active_events) == 1.0

def test_generate_dynamic_market():
    h3_cell = "888c1479e1fffff"
    timestamp = "2026-08-11 12:30:00"  # Lunch hour
    
    market = DynamicMarketManager.generate_dynamic_market(
        timestamp=timestamp,
        h3_cell=h3_cell,
        base_drivers=50,
        base_orders=20,
        service_type="GoFood",
        weather="rainy"
    )
    
    assert isinstance(market, Market)
    assert market.area == h3_cell
    # Lunch GoFood (2.0) * Rainy (2.5) * 20 orders = 100 active orders
    assert market.active_orders == 100
    # 50 drivers * 0.7 speed factor = 35 active drivers
    assert market.active_drivers == 35
