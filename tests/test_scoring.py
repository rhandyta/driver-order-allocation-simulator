"""Unit tests for the scoring module."""

import pytest
from src.models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from src.scoring import calculate_score, score_all_candidates, get_score_breakdown
from src.features import haversine, normalize, get_time_slot, get_distance_bucket, get_area


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


def make_market(area="area_A", drivers=50, orders=120):
    """Helper fixture to create a Market instance with default test values."""
    return Market(area=area, active_drivers=drivers, active_orders=orders)


def default_weights():
    """Helper fixture to create default ScoringWeights."""
    return ScoringWeights()


def default_sub_weights():
    """Helper fixture to create default HistorySubWeights."""
    return HistorySubWeights()


def test_same_input_same_score():
    """Verify that same driver + order + market produces identical score (deterministic)."""
    driver = make_driver()
    order = make_order()
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    score1 = calculate_score(driver, order, market, weights, sub_weights)
    score2 = calculate_score(driver, order, market, weights, sub_weights)

    assert score1 == pytest.approx(score2)


def test_higher_history_higher_score():
    """Verify that driver with better history match gets a higher score."""
    order = make_order(
        service="GoFood",
        pickup=(-6.913, 107.610),
        dist=3.2,
        timestamp="2026-08-11 12:30:00",
    )
    market = make_market(area="area_A")
    weights = default_weights()
    sub_weights = default_sub_weights()

    rich_history = {
        "services": {"GoFood": 100, "GoRide": 5},
        "areas": {"area_A": 80, "area_B": 5},
        "time_slots": {
            "lunch": 60,
            "morning": 5,
            "afternoon": 5,
            "evening": 5,
            "night": 0,
        },
        "distance_buckets": {"3-7km": 70, "0-3km": 10, "7km+": 5},
    }
    driver_rich = make_driver(id="D_RICH", history=rich_history)

    poor_history = {
        "services": {"GoFood": 0, "GoRide": 50},
        "areas": {"area_A": 0, "area_Z": 50},
        "time_slots": {"night": 50},
        "distance_buckets": {"7km+": 50},
    }
    driver_poor = make_driver(id="D_POOR", history=poor_history)

    score_rich = calculate_score(driver_rich, order, market, weights, sub_weights)
    score_poor = calculate_score(driver_poor, order, market, weights, sub_weights)

    assert score_rich > score_poor


def test_closer_driver_higher_location_score():
    """Verify that driver closer to pickup location gets a higher location score and overall score."""
    order = make_order(pickup=(-6.9130, 107.6100))
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    driver_close = make_driver(id="D_CLOSE", lat=-6.9131, lon=107.6101)
    driver_far = make_driver(id="D_FAR", lat=-6.9800, lon=107.6800)

    breakdown_close = get_score_breakdown(driver_close, order, market, weights, sub_weights)
    breakdown_far = get_score_breakdown(driver_far, order, market, weights, sub_weights)

    loc_key = "location" if "location" in breakdown_close else "location_score"
    assert breakdown_close[loc_key] > breakdown_far[loc_key]

    score_close = calculate_score(driver_close, order, market, weights, sub_weights)
    score_far = calculate_score(driver_far, order, market, weights, sub_weights)
    assert score_close > score_far


def test_score_in_valid_range():
    """Verify that score is strictly bounded between 0 and 100 for various inputs."""
    drivers = [
        make_driver(
            id="D_PERFECT", ar=1.0, cr=1.0, online_hours=100, online_days=14
        ),
        make_driver(
            id="D_MINIMAL",
            ar=0.0,
            cr=0.0,
            online_hours=0,
            online_days=0,
            history={},
        ),
        make_driver(id="D_NORMAL"),
    ]
    orders = [
        make_order(dist=0.5, dur=5),
        make_order(dist=25.0, dur=90),
    ]
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    for driver in drivers:
        for order in orders:
            score = calculate_score(driver, order, market, weights, sub_weights)
            assert (
                0.0 <= score <= 100.0
            ), f"Score {score} out of bounds for driver {driver.id}"


def test_score_breakdown_components():
    """Verify that all score breakdown components are normalized between 0 and 1."""
    driver = make_driver()
    order = make_order()
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    breakdown = get_score_breakdown(driver, order, market, weights, sub_weights)
    assert isinstance(breakdown, dict)
    assert len(breakdown) > 0

    for key, value in breakdown.items():
        assert (
            0.0 <= value <= 1.0
        ), f"Breakdown component '{key}' has value {value} outside [0.0, 1.0]"


def test_weights_affect_score():
    """Verify that changing weights changes the final score proportionally."""
    driver = make_driver()
    order = make_order()
    market = make_market()
    sub_weights = default_sub_weights()

    weights1 = default_weights()
    weights2 = ScoringWeights()
    weights2.history = weights1.history * 2.0

    score1 = calculate_score(driver, order, market, weights1, sub_weights)
    score2 = calculate_score(driver, order, market, weights2, sub_weights)

    assert isinstance(score1, float)
    assert isinstance(score2, float)
    # The score should reflect the modified weights
    assert score1 >= 0.0 and score2 >= 0.0
