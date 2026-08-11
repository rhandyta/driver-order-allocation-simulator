import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Any, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights, AllocationResult
from .scoring import get_score_breakdown, calculate_score
from .eligibility import filter_eligible

FEATURE_NAMES = [
    "demand_score",
    "historical_fit",
    "service_fit",
    "time_fit",
    "location_score",
    "eta_fit",
    "acceptance_rate",
    "completion_rate",
    "online_consistency",
    "estimated_distance",
    "estimated_duration"
]

class AllocationDatasetGenerator:
    """Generates ML dataset (X, y) from simulation runs."""
    
    def __init__(self):
        self.sub_weights = HistorySubWeights()
        self.weights = ScoringWeights()

    def extract_features(self, driver: Driver, order: Order, market: Market) -> np.ndarray:
        breakdown = get_score_breakdown(driver, order, market, self.weights, self.sub_weights)
        features = [
            breakdown["demand"],
            breakdown["historical_fit"],
            breakdown["service_fit"],
            breakdown["time_fit"],
            breakdown["location"],
            breakdown["eta"],
            breakdown["acceptance_rate"],
            breakdown["completion_rate"],
            breakdown["online_consistency"],
            order.estimated_distance,
            order.estimated_duration
        ]
        return np.array(features, dtype=float)

    def build_dataset_from_simulation(self, drivers: List[Driver], orders: List[Order], markets: List[Market],
                                     allocations: List[AllocationResult]) -> Tuple[pd.DataFrame, np.ndarray]:
        X_rows = []
        y_labels = []
        
        alloc_map = {r.order_id: r.driver_id for r in allocations if r.result in ("allocated", "completed")}
        market_map = {m.area: m for m in markets}
        
        for order in orders:
            winner_id = alloc_map.get(order.id)
            if not winner_id:
                continue
            
            # Eligible candidates
            eligible_drivers = filter_eligible(drivers, order)
            for d in eligible_drivers:
                m = market_map.get(d.history.get("main_area", "area_B"), markets[0] if markets else Market("area_B", 50, 50))
                feat = self.extract_features(d, order, m)
                X_rows.append(feat)
                y_labels.append(1 if d.id == winner_id else 0)
        
        df_X = pd.DataFrame(X_rows, columns=FEATURE_NAMES)
        arr_y = np.array(y_labels, dtype=int)
        return df_X, arr_y

class AllocationMLModel:
    """Machine Learning Model (Logistic Regression & Random Forest) for predicting driver order allocation probability."""
    
    def __init__(self, model_type: str = "rf"):
        self.model_type = model_type
        if model_type == "logistic":
            self.model = LogisticRegression(max_iter=1000, random_state=42)
        else:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            
    def train(self, X: pd.DataFrame, y: np.ndarray):
        self.model.fit(X, y)
        
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(X)[:, 1]
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)
    
    def evaluate(self, X_test: pd.DataFrame, y_test: np.ndarray) -> Dict[str, float]:
        preds = self.predict(X_test)
        probs = self.predict_proba(X_test)
        
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        try:
            auc = roc_auc_score(y_test, probs)
        except ValueError:
            auc = 0.5
            
        return {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "roc_auc": float(auc)
        }
    
    def get_feature_importances(self) -> Dict[str, float]:
        if hasattr(self.model, "feature_importances_"):
            importances = self.model.feature_importances_
        elif hasattr(self.model, "coef_"):
            importances = np.abs(self.model.coef_[0])
        else:
            importances = np.zeros(len(FEATURE_NAMES))
            
        total = np.sum(importances)
        if total > 0:
            importances = importances / total
            
        return dict(zip(FEATURE_NAMES, importances))
