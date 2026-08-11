import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any
from sklearn.inspection import permutation_importance
from .ml_model import AllocationMLModel, FEATURE_NAMES

class FeatureExplainer:
    """Provides explainability analysis (Feature Importance, Permutation Importance)
    and exports visual charts and summaries.
    """
    
    def __init__(self, ml_model: AllocationMLModel):
        self.ml_model = ml_model
        
    def compute_permutation_importance(self, X_val: pd.DataFrame, y_val: np.ndarray) -> Dict[str, float]:
        res = permutation_importance(self.ml_model.model, X_val, y_val, n_repeats=10, random_state=42)
        importances = res.importances_mean
        total = np.sum(np.maximum(0, importances))
        if total > 0:
            norm_imp = importances / total
        else:
            norm_imp = importances
            
        return dict(zip(FEATURE_NAMES, norm_imp))

    def generate_explainability_report(self, X_val: pd.DataFrame, y_val: np.ndarray, output_dir: str = "results"):
        os.makedirs(os.path.join(output_dir, "charts"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "csv"), exist_ok=True)
        
        # Get importances
        model_imp = self.ml_model.get_feature_importances()
        perm_imp = self.compute_permutation_importance(X_val, y_val)
        
        df_imp = pd.DataFrame({
            "feature": FEATURE_NAMES,
            "model_importance": [model_imp.get(f, 0.0) for f in FEATURE_NAMES],
            "permutation_importance": [perm_imp.get(f, 0.0) for f in FEATURE_NAMES]
        }).sort_values("permutation_importance", ascending=False)
        
        # Save CSV
        csv_path = os.path.join(output_dir, "csv", "feature_importance.csv")
        df_imp.to_csv(csv_path, index=False)
        
        # Generate chart
        plt.figure(figsize=(10, 6))
        features = df_imp["feature"]
        y_pos = np.arange(len(features))
        
        plt.barh(y_pos, df_imp["permutation_importance"], align="center", alpha=0.8, color="#2b5c8f")
        plt.yticks(y_pos, features)
        plt.xlabel("Normalized Permutation Importance Score")
        plt.title("Phase 6: Allocation Feature Importance Analysis")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        
        chart_path = os.path.join(output_dir, "charts", "feature_importance.png")
        plt.savefig(chart_path, dpi=150)
        plt.close()
        
        return df_imp
