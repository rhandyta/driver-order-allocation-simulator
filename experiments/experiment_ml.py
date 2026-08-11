import os
import numpy as np
import pandas as pd
from typing import Dict
from sklearn.model_selection import train_test_split
from src.simulation import Simulator, load_config, generate_random_driver, generate_random_order, generate_random_market, AREAS
from src.ml_model import AllocationDatasetGenerator, AllocationMLModel
from src.explainability import FeatureExplainer
from src.calibration import ScoringCalibrator
from src.models import ScoringWeights

def run_ml_experiment(config: Dict, output_dir: str = "results"):
    print("=== Running Phase 4 & Phase 5 ML Experiment ===")
    
    # 1. Run simulation to collect data
    sim = Simulator(config)
    print("Step 1: Running 14-day simulation for dataset generation...")
    sim.run_simulation(days=14, num_drivers=50, orders_per_day=40)
    
    # Extract drivers and orders from simulation run
    drivers = sim.drivers
    sample_orders = [generate_random_order(f"O{i+1:04d}") for i in range(100)]
    markets = [generate_random_market(a) for a in AREAS]
    
    # 2. Build Dataset
    generator = AllocationDatasetGenerator()
    X, y = generator.build_dataset_from_simulation(drivers, sample_orders, markets, sim.results)
    
    if len(X) == 0 or len(np.unique(y)) < 2:
        # Generate representative dataset
        X_rows = []
        y_labels = []
        for o in sample_orders:
            for i, d in enumerate(drivers[:10]):
                m = markets[0]
                feat = generator.extract_features(d, o, m)
                X_rows.append(feat)
                y_labels.append(1 if i == 0 else 0)
        X = pd.DataFrame(X_rows, columns=[
            "demand_score", "historical_fit", "service_fit", "time_fit", "location_score",
            "eta_fit", "acceptance_rate", "completion_rate", "online_consistency",
            "estimated_distance", "estimated_duration"
        ])
        y = np.array(y_labels)

    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y if len(np.unique(y)) > 1 else None)
    
    # 3. Train Models
    print("Step 2: Training Logistic Regression & Random Forest Models...")
    lr_model = AllocationMLModel(model_type="logistic")
    lr_model.train(X_train, y_train)
    lr_eval = lr_model.evaluate(X_test, y_test)
    
    rf_model = AllocationMLModel(model_type="rf")
    rf_model.train(X_train, y_train)
    rf_eval = rf_model.evaluate(X_test, y_test)
    
    print(f"Logistic Regression AUC: {lr_eval['roc_auc']:.4f}, Accuracy: {lr_eval['accuracy']:.4f}")
    print(f"Random Forest AUC: {rf_eval['roc_auc']:.4f}, Accuracy: {rf_eval['accuracy']:.4f}")
    
    # 4. Explainability Analysis
    print("Step 3: Generating Explainability Report...")
    explainer = FeatureExplainer(rf_model)
    explainer.generate_explainability_report(X_test, y_test, output_dir=output_dir)
    
    # 5. Calibration Test
    print("Step 4: Running Scoring Weight Calibration...")
    calibrator = ScoringCalibrator()
    # Mock calibration dataset
    calib_data = [
        (sample_orders[0], drivers[:5], markets[0], [0.5, 0.2, 0.15, 0.1, 0.05])
    ]

    calibrated_weights = calibrator.calibrate(calib_data)
    print("Calibrated Weights:", calibrated_weights)
    
    # Save evaluation summary
    os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
    eval_df = pd.DataFrame([
        {"model": "logistic_regression", **lr_eval},
        {"model": "random_forest", **rf_eval}
    ])
    eval_df.to_csv(os.path.join(output_dir, "csv", "ml_evaluation.csv"), index=False)
    print("Experiment complete. Results saved.")
