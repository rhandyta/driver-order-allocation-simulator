import pytest
from src.routing_osrm import OSRMClient
from src.models import Driver, Order
from src.features import location_score, eta_fit

def test_osrm_client_fallback_and_caching():
    coord1 = (-6.9147, 107.6098)  # Bandung Center
    coord2 = (-6.9200, 107.6200)
    
    # First call
    dist1, dur1 = OSRMClient.get_road_distance_and_duration(coord1, coord2)
    assert dist1 > 0
    assert dur1 > 0
    
    # Second call (cached)
    dist2, dur2 = OSRMClient.get_road_distance_and_duration(coord1, coord2)
    assert dist1 == dist2
    assert dur1 == dur2

def test_osrm_identical_coordinates():
    coord = (-6.9147, 107.6098)
    dist, dur = OSRMClient.get_road_distance_and_duration(coord, coord)
    assert dist == 0.0
    assert dur == 0.0

def test_features_integration_with_osrm():
    driver = Driver("D1", (-6.9147, 107.6098), ["GoRide"], True, 1.0, 1.0, 50, 10, {}, "active", "healthy")
    order = Order("O1", "GoRide", (-6.9200, 107.6200), (-6.9300, 107.6300), "2026-08-11 12:00:00", 3.0, 10)
    
    score_haversine = location_score(driver, order, use_osrm=False)
    score_osrm = location_score(driver, order, use_osrm=True)
    
    assert 0.0 <= score_haversine <= 1.0
    assert 0.0 <= score_osrm <= 1.0
    
    eta_haversine = eta_fit(driver, order, use_osrm=False)
    eta_osrm = eta_fit(driver, order, use_osrm=True)
    
    assert 0.0 <= eta_haversine <= 1.0
    assert 0.0 <= eta_osrm <= 1.0
