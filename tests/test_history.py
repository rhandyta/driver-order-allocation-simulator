"""Unit tests for the history management module."""

import pytest
from src.models import Driver, Order
from src.history import HistoryManager, update_driver_after_order


def make_driver(
    id="D001",
    lat=-6.9147,
    lon=107.6098,
    ar=0.95,
    cr=0.97,
    online_hours=70,
    online_days=12,
    services=None,
    history=None,
):
    """Helper fixture to create a Driver instance with default test values."""
    if services is None:
        services = ["GoRide", "GoFood"]
    if history is None:
        history = {
            "services": {"GoFood": 30, "GoRide": 15},
            "areas": {"area_A": 25, "area_B": 10},
            "time_slots": {
                "morning": 8,
                "lunch": 20,
                "afternoon": 10,
                "evening": 7,
                "night": 0,
            },
            "distance_buckets": {"0-3km": 20, "3-7km": 15, "7km+": 5},
        }
    return Driver(
        id=id,
        location=(lat, lon),
        service_types=services,
        online=True,
        acceptance_rate=ar,
        completion_rate=cr,
        online_hours=online_hours,
        online_days=online_days,
        history=history,
        account_status="active",
        device_status="healthy",
        trip_settings={},
    )


def make_order(
    id="O001",
    service="GoFood",
    pickup=(-6.913, 107.610),
    dest=(-6.920, 107.620),
    timestamp="2026-08-11 12:30:00",
    dist=3.2,
    dur=18,
):
    """Helper fixture to create an Order instance with default test values."""
    return Order(
        id=id,
        service_type=service,
        pickup=pickup,
        destination=dest,
        timestamp=timestamp,
        estimated_distance=dist,
        estimated_duration=dur,
    )


def test_record_trip():
    """Verify that recording a trip updates daily records correctly in HistoryManager."""
    mgr = HistoryManager()
    driver = make_driver(id="D001")
    order = make_order(service="GoFood", dist=3.2)

    # record_trip(driver, order, day) where day is an integer index
    mgr.record_trip(driver, order, day=0)

    # Check that daily_records has the driver's entry
    assert driver.id in mgr.daily_records
    assert 0 in mgr.daily_records[driver.id]
    rec = mgr.daily_records[driver.id][0]
    assert rec["services"]["GoFood"] == 1


def test_rolling_window_aggregate():
    """Verify that rolling window aggregation includes all days within the window."""
    mgr = HistoryManager(window_size=14)
    driver = make_driver(id="D001")
    order1 = make_order(id="O1", service="GoFood")
    order2 = make_order(id="O2", service="GoRide")

    # Record trips on different days within 14-day window
    for day in [0, 5, 10]:
        mgr.record_trip(driver, order1, day=day)
        mgr.record_trip(driver, order2, day=day)

    # Aggregate from day 0 to day 13 (14-day window ending at day 13)
    agg = mgr.aggregate_window(driver.id, current_day=13)

    assert isinstance(agg, dict)
    assert agg["services"]["GoFood"] == 3
    assert agg["services"]["GoRide"] == 3


def test_rolling_window_excludes_old():
    """Verify that days prior to the rolling window are excluded from aggregation."""
    mgr = HistoryManager(window_size=14)
    driver = make_driver(id="D001")
    order = make_order(id="O_OLD", service="GoFood")

    # Record a trip on day 0 (will be old) and day 20 (recent)
    mgr.record_trip(driver, order, day=0)
    mgr.record_trip(driver, order, day=20)

    # Aggregate at day 20 with window=14 => only days 7..20 included
    agg = mgr.aggregate_window(driver.id, current_day=20)

    # Only day 20 trip should be included, day 0 is outside window
    count = agg.get("services", {}).get("GoFood", 0)
    assert count == 1


def test_update_driver_history():
    """Verify that driver's history attribute is properly updated."""
    mgr = HistoryManager(window_size=14)
    driver = make_driver(id="D001", history={})
    order = make_order(service="GoFood")

    # Record a trip on day 5
    mgr.record_trip(driver, order, day=5)

    # Update driver's history at day 10
    mgr.update_driver_history(driver, current_day=10)

    assert isinstance(driver.history, dict)
    assert driver.history.get("services", {}).get("GoFood", 0) == 1


def test_update_driver_after_completed_order():
    """Verify that completion rate stays stable or high after a completed order."""
    driver = make_driver(cr=0.95, ar=0.95)
    order = make_order()

    initial_cr = driver.completion_rate
    # completed=True (default)
    update_driver_after_order(driver, order, completed=True)

    # CR should remain high and not decrease significantly
    assert driver.completion_rate >= initial_cr - 0.05
    assert 0.0 <= driver.completion_rate <= 1.0


def test_update_driver_after_cancelled_order():
    """Verify that completion rate decreases after a cancelled order."""
    driver = make_driver(cr=0.95, ar=0.95)
    order = make_order()

    initial_cr = driver.completion_rate
    # completed=False means cancelled
    update_driver_after_order(driver, order, completed=False)

    assert driver.completion_rate < initial_cr
    assert 0.0 <= driver.completion_rate <= 1.0
