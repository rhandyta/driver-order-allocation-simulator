"""Unit tests for the order allocation module."""

import pytest
from src.models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from src.allocator import allocate_order, rank_drivers, softmax_probabilities
from src.eligibility import is_eligible, filter_eligible


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
    online=True,
    account_status="active",
    device_status="healthy",
):
    """Helper fixture to create a Driver instance with custom parameters."""
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
        online=online,
        acceptance_rate=ar,
        completion_rate=cr,
        online_hours=online_hours,
        online_days=online_days,
        history=history,
        account_status=account_status,
        device_status=device_status,
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


def test_eligibility_filters_offline():
    """Verify that an offline driver is marked as ineligible and filtered out."""
    driver_offline = make_driver(id="D_OFFLINE", online=False)
    driver_online = make_driver(id="D_ONLINE", online=True)
    order = make_order()

    assert is_eligible(driver_offline, order) is False
    assert is_eligible(driver_online, order) is True

    eligible = filter_eligible([driver_offline, driver_online], order)
    assert driver_offline not in eligible
    assert driver_online in eligible


def test_eligibility_filters_suspended():
    """Verify that a driver with account_status 'suspended' is filtered out."""
    driver_suspended = make_driver(id="D_SUSP", account_status="suspended")
    driver_active = make_driver(id="D_ACT", account_status="active")
    order = make_order()

    assert is_eligible(driver_suspended, order) is False
    assert is_eligible(driver_active, order) is True

    eligible = filter_eligible([driver_suspended, driver_active], order)
    assert driver_suspended not in eligible
    assert driver_active in eligible


def test_eligibility_filters_wrong_service():
    """Verify that a driver without matching service type is filtered out."""
    driver_goride_only = make_driver(id="D_RIDE", services=["GoRide"])
    driver_gofood_only = make_driver(id="D_FOOD", services=["GoFood"])
    order_gofood = make_order(service="GoFood")

    assert is_eligible(driver_goride_only, order_gofood) is False
    assert is_eligible(driver_gofood_only, order_gofood) is True

    eligible = filter_eligible(
        [driver_goride_only, driver_gofood_only], order_gofood
    )
    assert driver_goride_only not in eligible
    assert driver_gofood_only in eligible


def test_softmax_probabilities_sum_to_one():
    """Verify that softmax allocation probabilities sum to approximately 1.0."""
    d1 = make_driver(id="D1")
    d2 = make_driver(id="D2")
    d3 = make_driver(id="D3")
    candidates = [(d1, 85.0), (d2, 70.0), (d3, 50.0)]

    # softmax_probabilities returns List[Tuple[Driver, float, float]]
    result = softmax_probabilities(candidates, temperature=1.0)

    # Sum the probabilities (3rd element of each tuple)
    total_prob = sum(prob for _, _, prob in result)
    assert total_prob == pytest.approx(1.0, abs=1e-4)


def test_rank_drivers_descending():
    """Verify that rank_drivers returns candidates sorted by score descending."""
    d1 = make_driver(id="D1")
    d2 = make_driver(id="D2")
    d3 = make_driver(id="D3")

    scored_candidates = [(d1, 45.0), (d2, 92.5), (d3, 78.0)]
    ranked = rank_drivers(scored_candidates)

    scores = [score for driver, score in ranked]
    assert scores == sorted(scores, reverse=True)
    assert ranked[0][0].id == "D2"
    assert ranked[1][0].id == "D3"
    assert ranked[2][0].id == "D1"


def test_allocate_order_returns_result():
    """Verify that allocate_order produces an AllocationResult when eligible drivers exist."""
    drivers = [make_driver(id="D1"), make_driver(id="D2")]
    order = make_order()
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    result = allocate_order(order, drivers, market, weights, sub_weights)

    assert result is not None
    assert hasattr(result, "order_id")
    assert hasattr(result, "driver_id")
    assert result.order_id == order.id


def test_allocate_order_no_eligible():
    """Verify that allocate_order returns None when no driver is eligible."""
    ineligible_drivers = [
        make_driver(id="D_OFFLINE", online=False),
        make_driver(id="D_SUSPENDED", account_status="suspended"),
        make_driver(id="D_WRONG_SVC", services=["GoSend"]),
    ]
    order = make_order(service="GoFood")
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    result = allocate_order(order, ineligible_drivers, market, weights, sub_weights)
    assert result is None


def test_deterministic_picks_top():
    """Verify that deterministic allocation mode always selects the highest scored driver."""
    d_top = make_driver(id="D_TOP", lat=-6.913, lon=107.610, ar=1.0, cr=1.0)
    d_low = make_driver(id="D_LOW", lat=-6.980, lon=107.680, ar=0.5, cr=0.5)
    order = make_order()
    market = make_market()
    weights = default_weights()
    sub_weights = default_sub_weights()

    # Use method="deterministic" to always pick highest score
    for _ in range(5):
        result = allocate_order(
            order, [d_top, d_low], market, weights, sub_weights,
            method="deterministic"
        )
        assert result is not None
        assert result.driver_id == "D_TOP"
