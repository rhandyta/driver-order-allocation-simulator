import pytest
from src.models import Driver, Order
from src.microsimulation import MicroDriver, MicroSimulationEngine, DriverState

def test_micro_driver_position_interpolation():
    driver = Driver("D1", (-6.91, 107.61), ["GoRide"], True, 1.0, 1.0, 50, 10, {}, "active", "healthy")
    micro = MicroDriver(driver)
    
    assert micro.state == DriverState.IDLE
    assert micro.current_location == (-6.91, 107.61)
    
    # Start travel to (-6.92, 107.62) in 100 seconds
    micro.start_travel((-6.92, 107.62), 100.0, current_time=0.0, next_state=DriverState.EN_ROUTE_PICKUP)
    assert micro.state == DriverState.EN_ROUTE_PICKUP
    
    # At 50 seconds (halfway)
    pos_halfway = micro.update_position(50.0)
    assert abs(pos_halfway[0] - (-6.915)) < 1e-4
    assert abs(pos_halfway[1] - 107.615) < 1e-4
    
    # At 100 seconds (arrived)
    pos_end = micro.update_position(100.0)
    assert abs(pos_end[0] - (-6.92)) < 1e-4
    assert abs(pos_end[1] - 107.62) < 1e-4

def test_micro_simulation_engine_ticks():
    driver1 = Driver("D1", (-6.91, 107.61), ["GoRide"], True, 1.0, 1.0, 50, 10, {}, "active", "healthy")
    driver2 = Driver("D2", (-6.95, 107.65), ["GoRide"], True, 1.0, 1.0, 50, 10, {}, "active", "healthy")
    config = {"scoring_weights": {"distance": 50, "demand": 50}}
    
    engine = MicroSimulationEngine([driver1, driver2], config)
    assert len(engine.get_idle_drivers()) == 2
    
    order = Order("O1", "GoRide", (-6.91, 107.61), (-6.92, 107.62), "2026-08-11 12:00:00", 3.0, 10)
    
    # Process tick with order
    engine.tick(delta_seconds=5.0, new_orders=[order])
    assert len(engine.allocation_log) == 1
    
    # At least one driver should now be EN_ROUTE_PICKUP
    states = [md.state for md in engine.micro_drivers]
    assert DriverState.EN_ROUTE_PICKUP in states
