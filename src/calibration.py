import numpy as np
from scipy.optimize import minimize
from typing import List, Dict, Tuple, Optional
from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from .scoring import calculate_score
from .allocator import softmax_probabilities

class ScoringCalibrator:
    """Calibrates scoring weights using optimization (scipy.optimize)
    to match target driver allocation probabilities or observed outcomes.
    """
    
    def __init__(self, target_weights: Optional[ScoringWeights] = None):
        self.sub_weights = HistorySubWeights()
    
    @staticmethod
    def _weights_to_array(weights: ScoringWeights) -> np.ndarray:
        return np.array([
            weights.demand,
            weights.history,
            weights.service,
            weights.time,
            weights.distance,
            weights.eta,
            weights.completion_rate,
            weights.acceptance_rate,
            weights.online_consistency
        ], dtype=float)

    @staticmethod
    def _array_to_weights(arr: np.ndarray) -> ScoringWeights:
        # Scale array to sum to 100
        arr = np.maximum(0, arr)
        total = np.sum(arr)
        if total > 0:
            arr = (arr / total) * 100.0
        else:
            arr = np.ones(9) * (100.0 / 9)
        return ScoringWeights(
            demand=arr[0],
            history=arr[1],
            service=arr[2],
            time=arr[3],
            distance=arr[4],
            eta=arr[5],
            completion_rate=arr[6],
            acceptance_rate=arr[7],
            online_consistency=arr[8]
        )

    def calibrate(self, dataset: List[Tuple[Order, List[Driver], Market, List[float]]],
                  temperature: float = 5.0,
                  initial_weights: Optional[ScoringWeights] = None) -> ScoringWeights:
        """Calibrate weights given dataset of (order, drivers, market, target_probs).
        
        Minimizes cross-entropy / MSE loss between predicted softmax probabilities and target probabilities.
        """
        init_w = initial_weights or ScoringWeights()
        x0 = self._weights_to_array(init_w)
        
        def loss_function(w_arr: np.ndarray) -> float:
            weights = self._array_to_weights(w_arr)
            total_loss = 0.0
            
            for order, drivers, market, target_probs in dataset:
                scores = [calculate_score(d, order, market, weights, self.sub_weights) for d in drivers]
                scored_candidates = [(d, s) for d, s in zip(drivers, scores)]
                candidates_with_prob = softmax_probabilities(scored_candidates, temperature)
                pred_probs = np.array([p for _, _, p in candidates_with_prob])
                
                # Cross-entropy loss + MSE loss
                eps = 1e-9
                pred_probs = np.clip(pred_probs, eps, 1.0 - eps)
                ce = -np.sum(np.array(target_probs) * np.log(pred_probs))
                total_loss += ce

            
            return total_loss / max(len(dataset), 1)
        
        bounds = [(0.0, 100.0) for _ in range(9)]
        res = minimize(loss_function, x0, bounds=bounds, method="L-BFGS-B")
        
        return self._array_to_weights(res.x)
