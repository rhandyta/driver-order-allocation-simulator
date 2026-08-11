import pytest
import numpy as np
from src.models import Driver, Order, Market, ScoringWeights
from src.calibration import ScoringCalibrator

def test_calibration_weights_array_conversion():
    w = ScoringWeights(demand=30, history=20, service=15, time=10, distance=10, eta=5, completion_rate=5, acceptance_rate=3, online_consistency=2)
    arr = ScoringCalibrator._weights_to_array(w)
    assert len(arr) == 9
    assert arr[0] == 30.0
    
    w_reconstructed = ScoringCalibrator._array_to_weights(arr)
    assert abs(w_reconstructed.demand - 30.0) < 1e-5

def test_calibrator_optimization():
    driver1 = Driver("D1", (-6.91, 107.61), ["GoRide"], True, 1.0, 1.0, 100, 14, {}, "active", "healthy")
    driver2 = Driver("D2", (-6.95, 107.61), ["GoRide"], True, 0.7, 0.7, 20, 3, {}, "active", "healthy")
    order = Order("O1", "GoRide", (-6.91, 107.61), (-6.92, 107.62), "2026-08-11 12:00:00", 3.0, 10)
    market = Market("area_B", 10, 20)
    
    dataset = [(order, [driver1, driver2], market, [0.8, 0.2])]
    calibrator = ScoringCalibrator()
    calibrated_weights = calibrator.calibrate(dataset)
    
    assert isinstance(calibrated_weights, ScoringWeights)
    total = sum([
        calibrated_weights.demand, calibrated_weights.history, calibrated_weights.service,
        calibrated_weights.time, calibrated_weights.distance, calibrated_weights.eta,
        calibrated_weights.completion_rate, calibrated_weights.acceptance_rate,
        calibrated_weights.online_consistency
    ])
    assert abs(total - 100.0) < 1e-3
