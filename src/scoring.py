from .models import Driver, Order, Market, ScoringWeights, HistorySubWeights
from . import features
from typing import List, Tuple, Dict, Optional

def calculate_score(driver: Driver, order: Order, market: Market,
                    weights: ScoringWeights, sub_weights: HistorySubWeights,
                    norm_params: Optional[Dict] = None,
                    use_osrm: bool = True) -> float:
    """Calculate the total score for a driver-order pair.
    
    score = w_demand * demand_score + w_history * historical_fit + ...
    All component scores are [0,1], weights sum to 100.
    Final score is in [0, 100].
    """
    params = norm_params or {}
    max_distance = params.get("max_distance_km", 15.0)
    max_eta = params.get("max_eta_minutes", 45.0)
    max_hours = params.get("max_online_hours", 120.0)
    max_days = params.get("max_online_days", 14)
    max_ratio = params.get("max_demand_ratio", 5.0)
    
    d_score = features.demand_score(market, max_ratio)
    h_score = features.historical_fit(driver, order, sub_weights)
    s_score = features.service_fit(driver, order)
    t_score = features.time_fit(driver, order)
    dist_score = features.location_score(driver, order, max_distance, use_osrm=use_osrm)
    e_score = features.eta_fit(driver, order, max_eta, use_osrm=use_osrm)
    ar_score = features.acceptance_score(driver)
    cr_score = features.completion_score(driver)
    oc_score = features.online_consistency(driver, max_hours, max_days)
    
    total = (
        weights.demand * d_score
        + weights.history * h_score
        + weights.service * s_score
        + weights.time * t_score
        + weights.distance * dist_score
        + weights.eta * e_score
        + weights.acceptance_rate * ar_score
        + weights.completion_rate * cr_score
        + weights.online_consistency * oc_score
    )
    return total

def score_all_candidates(drivers: List[Driver], order: Order, market: Market,
                          weights: ScoringWeights, sub_weights: HistorySubWeights,
                          norm_params: Optional[Dict] = None,
                          use_osrm: bool = True) -> List[Tuple[Driver, float]]:
    """Score all candidate drivers for a given order."""
    results = []
    for driver in drivers:
        score = calculate_score(driver, order, market, weights, sub_weights, norm_params, use_osrm=use_osrm)
        driver.score = score
        results.append((driver, score))
    return results


def get_score_breakdown(driver: Driver, order: Order, market: Market,
                        weights: ScoringWeights, sub_weights: HistorySubWeights,
                        norm_params: Optional[Dict] = None) -> Dict[str, float]:
    """Get detailed breakdown of score components for analysis."""
    params = norm_params or {}
    return {
        "demand": features.demand_score(market, params.get("max_demand_ratio", 5.0)),
        "historical_fit": features.historical_fit(driver, order, sub_weights),
        "service_fit": features.service_fit(driver, order),
        "time_fit": features.time_fit(driver, order),
        "location": features.location_score(driver, order, params.get("max_distance_km", 15.0)),
        "eta": features.eta_fit(driver, order, params.get("max_eta_minutes", 45.0)),
        "acceptance_rate": features.acceptance_score(driver),
        "completion_rate": features.completion_score(driver),
        "online_consistency": features.online_consistency(driver, params.get("max_online_hours", 120.0), params.get("max_online_days", 14)),
    }
