import os
import csv
import matplotlib.pyplot as plt
from collections import defaultdict
from src.models import Driver, Order, Market, ScoringWeights, HistorySubWeights, AllocationResult
from src.allocator import allocate_order
from src.simulation import generate_random_order

plt.switch_backend('Agg')

def _make_driver(id, ar=0.95, cr=0.97, online_hours=70, online_days=12,
                 services=None, history=None, location=(-6.91, 107.61)):
    if services is None:
        services = ["GoRide", "GoFood", "GoSend"]
    if history is None:
        history = {
            "services": {"GoFood": 30, "GoRide": 15, "GoSend": 5},
            "areas": {"area_A": 25, "area_B": 10, "area_C": 5},
            "time_slots": {"morning": 8, "lunch": 20, "afternoon": 10, "evening": 7, "night": 0},
            "distance_buckets": {"0-3km": 20, "3-7km": 15, "7km+": 5}
        }
    return Driver(
        id=id, location=location, service_types=services, online=True,
        acceptance_rate=ar, completion_rate=cr, online_hours=online_hours,
        online_days=online_days, history=history, account_status="active",
        device_status="healthy", trip_settings={}
    )

def _load_from_config(config):
    sw = config.get('scoring_weights', {})
    weights = ScoringWeights(
        demand=sw.get('demand', 30), history=sw.get('history', 20),
        service=sw.get('service', 15), time=sw.get('time', 10),
        distance=sw.get('distance', 10), eta=sw.get('eta', 5),
        completion_rate=sw.get('completion_rate', 5),
        acceptance_rate=sw.get('acceptance_rate', 3),
        online_consistency=sw.get('online_consistency', 2)
    )
    hsw = config.get('history_sub_weights', {})
    sub_weights = HistorySubWeights(
        service=hsw.get('service', 0.35), area=hsw.get('area', 0.30),
        time=hsw.get('time', 0.20), distance=hsw.get('distance', 0.15)
    )
    alloc = config.get('allocation', {})
    temperature = alloc.get('temperature', 5.0)
    norm_params = config.get('normalization', {})
    return weights, sub_weights, temperature, norm_params

def run_experiment_ar(config, output_dir):
    weights, sub_weights, temperature, norm_params = _load_from_config(config)
    os.makedirs(os.path.join(output_dir, 'csv'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)
    
    ar_values = [0.70, 0.80, 0.90, 0.95, 0.99, 1.00]
    iterations = 1000
    market = Market(area="area_A", active_drivers=len(ar_values), active_orders=100)
    
    drivers = [_make_driver(id=f"Driver_{ar:.2f}", ar=ar) for ar in ar_values]
    
    win_counts = {d.id: 0 for d in drivers}
    
    for i in range(iterations):
        order = generate_random_order(order_id=f"O_{i}")
        result = allocate_order(order, drivers, market, weights, sub_weights, temperature, "softmax", "hard", norm_params)
        if result and result.driver_id:
            win_counts[result.driver_id] += 1
            
    print("Experiment AR Results:")
    with open(os.path.join(output_dir, 'csv', 'experiment_ar.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Driver', 'AR', 'Wins', 'Win_Rate'])
        for d in drivers:
            rate = win_counts[d.id] / iterations
            print(f"{d.id}: {win_counts[d.id]} wins ({rate*100:.1f}%)")
            writer.writerow([d.id, d.acceptance_rate, win_counts[d.id], rate])
            
    plt.figure(figsize=(10, 6))
    plt.bar([str(ar) for ar in ar_values], [win_counts[f"Driver_{ar:.2f}"]/iterations for ar in ar_values])
    plt.title('Win Rate by Acceptance Rate')
    plt.xlabel('Acceptance Rate')
    plt.ylabel('Win Rate')
    plt.savefig(os.path.join(output_dir, 'charts', 'experiment_ar.png'))
    plt.close()


def run_experiment(config, output_dir="results"):
    return run_experiment_ar(config, output_dir)
