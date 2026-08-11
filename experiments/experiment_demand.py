import os
import csv
import matplotlib.pyplot as plt
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

def run_experiment_demand(config, output_dir):
    weights, sub_weights, temperature, norm_params = _load_from_config(config)
    os.makedirs(os.path.join(output_dir, 'csv'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)
    
    demand_ratios = [10, 20, 50, 100, 200]
    iterations = 100
    
    drivers = [_make_driver(id="Driver_A", ar=0.95), _make_driver(id="Driver_B", ar=0.85)]
    
    results = {dr: {d.id: 0 for d in drivers} for dr in demand_ratios}
    
    for dr in demand_ratios:
        market = Market(area="area_A", active_drivers=100, active_orders=dr)
        for i in range(iterations):
            order = generate_random_order(order_id=f"O_{i}")
            result = allocate_order(order, drivers, market, weights, sub_weights, temperature, "softmax", "hard", norm_params)
            if result and result.driver_id:
                results[dr][result.driver_id] += 1
                
    print("Experiment Demand Results:")
    with open(os.path.join(output_dir, 'csv', 'experiment_demand.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Demand_Ratio', 'Driver_A_Wins', 'Driver_B_Wins'])
        for dr in demand_ratios:
            a_wins = results[dr]["Driver_A"]
            b_wins = results[dr]["Driver_B"]
            print(f"Demand Ratio {dr}: Driver A {a_wins}, Driver B {b_wins}")
            writer.writerow([dr, a_wins, b_wins])
            
    plt.figure(figsize=(10, 6))
    dr_str = [str(dr) for dr in demand_ratios]
    a_rates = [results[dr]["Driver_A"]/iterations for dr in demand_ratios]
    b_rates = [results[dr]["Driver_B"]/iterations for dr in demand_ratios]
    x = range(len(demand_ratios))
    plt.bar([i - 0.2 for i in x], a_rates, width=0.4, label='Driver A (AR 0.95)')
    plt.bar([i + 0.2 for i in x], b_rates, width=0.4, label='Driver B (AR 0.85)')
    plt.xticks(x, dr_str)
    plt.title('Win Rate by Demand Ratio')
    plt.xlabel('Demand Ratio (Orders per 100 Drivers)')
    plt.ylabel('Win Rate')
    plt.legend()
    plt.savefig(os.path.join(output_dir, 'charts', 'experiment_demand.png'))
    plt.close()


def run_experiment(config, output_dir="results"):
    return run_experiment_demand(config, output_dir)
