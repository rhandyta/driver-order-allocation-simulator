import pytest
import numpy as np
import pandas as pd
from src.models import Driver, Order, Market, AllocationResult
from src.ml_model import AllocationDatasetGenerator, AllocationMLModel, FEATURE_NAMES

def test_dataset_generator():
    driver = Driver("D1", (-6.91, 107.61), ["GoRide"], True, 1.0, 1.0, 100, 14, {}, "active", "healthy")
    order = Order("O1", "GoRide", (-6.91, 107.61), (-6.92, 107.62), "2026-08-11 12:00:00", 3.0, 10)
    market = Market("area_B", 10, 20)
    
    gen = AllocationDatasetGenerator()
    feat = gen.extract_features(driver, order, market)
    assert len(feat) == len(FEATURE_NAMES)

def test_ml_model_train_and_evaluate():
    X = pd.DataFrame(np.random.rand(50, len(FEATURE_NAMES)), columns=FEATURE_NAMES)
    y = np.random.choice([0, 1], size=50)
    
    model = AllocationMLModel(model_type="rf")
    model.train(X, y)
    
    probs = model.predict_proba(X)
    assert len(probs) == 50
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
    
    metrics = model.evaluate(X, y)
    assert "accuracy" in metrics
    assert "roc_auc" in metrics
    
    importances = model.get_feature_importances()
    assert len(importances) == len(FEATURE_NAMES)
