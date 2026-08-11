import pytest
from src.models import Driver, Order
from src.eligibility import is_eligible

def test_trip_settings_max_pickup_distance():
    driver = Driver(
        id="D001",
        location=(-6.91, 107.61),
        service_types=["GoRide"],
        online=True,
        acceptance_rate=1.0,
        completion_rate=1.0,
        online_hours=50,
        online_days=10,
        history={},
        account_status="active",
        device_status="healthy",
        trip_settings={"max_pickup_distance": 2.0}
    )
    
    # Close order (~1 km)
    close_order = Order(
        id="O001",
        service_type="GoRide",
        pickup=(-6.915, 107.61),
        destination=(-6.92, 107.62),
        timestamp="2026-08-11 12:00:00",
        estimated_distance=3.0,
        estimated_duration=10
    )
    
    # Far order (~10 km)
    far_order = Order(
        id="O002",
        service_type="GoRide",
        pickup=(-6.99, 107.61),
        destination=(-7.00, 107.62),
        timestamp="2026-08-11 12:00:00",
        estimated_distance=12.0,
        estimated_duration=30
    )
    
    assert is_eligible(driver, close_order) == True
    assert is_eligible(driver, far_order) == False

def test_trip_settings_destination_area():
    driver = Driver(
        id="D002",
        location=(-6.91, 107.61),
        service_types=["GoFood"],
        online=True,
        acceptance_rate=0.9,
        completion_rate=0.9,
        online_hours=40,
        online_days=7,
        history={},
        account_status="active",
        device_status="healthy",
        trip_settings={"destination_area": "area_C"}
    )
    
    order_area_c = Order(
        id="O003",
        service_type="GoFood",
        pickup=(-6.91, 107.61),
        destination=(-6.95, 107.59), # area_C
        timestamp="2026-08-11 12:00:00",
        estimated_distance=4.0,
        estimated_duration=15
    )
    
    assert is_eligible(driver, order_area_c) == True
