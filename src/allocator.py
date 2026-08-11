import numpy as np
from typing import List, Tuple, Optional
from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights, AllocationResult
from .eligibility import filter_eligible
from .scoring import score_all_candidates

def rank_drivers(scored_candidates: List[Tuple[Driver, float]]) -> List[Tuple[Driver, float]]:
    """Rank drivers by score descending."""
    return sorted(scored_candidates, key=lambda x: x[1], reverse=True)

def softmax_probabilities(scored_candidates: List[Tuple[Driver, float]], temperature: float = 5.0) -> List[Tuple[Driver, float, float]]:
    """Calculate softmax probabilities for probabilistic allocation.
    
    P(driver_i) = exp(score_i / temperature) / sum(exp(score_j / temperature))
    
    Returns list of (driver, score, probability).
    """
    if not scored_candidates:
        return []
    
    scores = np.array([s for _, s in scored_candidates])
    # Numerical stability: subtract max
    shifted = (scores - np.max(scores)) / temperature
    exp_scores = np.exp(shifted)
    probs = exp_scores / np.sum(exp_scores)
    
    result = []
    for (driver, score), prob in zip(scored_candidates, probs):
        driver.probability = float(prob)
        result.append((driver, score, float(prob)))
    return result

def allocate_order(order: Order, drivers: List[Driver], market: Market,
                   weights: ScoringWeights, sub_weights: HistorySubWeights,
                   temperature: float = 5.0, method: str = "softmax",
                   eligibility_mode: str = "hard",
                   norm_params: Optional[dict] = None,
                   use_osrm: bool = True) -> Optional[AllocationResult]:
    """Full allocation pipeline: filter -> score -> rank -> allocate."""
    # Step 1: Filter eligible
    eligible = filter_eligible(drivers, order, eligibility_mode)
    if not eligible:
        return None
    
    # Step 2: Score all candidates
    scored = score_all_candidates(eligible, order, market, weights, sub_weights, norm_params, use_osrm=use_osrm)

    
    # Step 3: Rank
    ranked = rank_drivers(scored)
    
    # Step 4: Allocate
    if method == "deterministic":
        winner = ranked[0][0]
        result_prob = 1.0
    else:  # softmax
        candidates_with_prob = softmax_probabilities(ranked, temperature)
        probs = [p for _, _, p in candidates_with_prob]
        drivers_list = [d for d, _, _ in candidates_with_prob]
        idx = np.random.choice(len(drivers_list), p=probs)
        winner = drivers_list[idx]
        result_prob = probs[idx]
    
    return AllocationResult(
        timestamp=order.timestamp,
        order_id=order.id,
        driver_id=winner.id,
        score=winner.score,
        probability=result_prob,
        result="allocated"
    )
