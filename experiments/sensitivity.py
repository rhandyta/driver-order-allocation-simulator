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

def run_sensitivity(config, output_dir):
    weights, sub_weights, temperature, norm_params = _load_from_config(config)
    os.makedirs(os.path.join(output_dir, 'csv'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'charts'), exist_ok=True)
    
    temp_values = [0.1, 1.0, 5.0, 10.0, 50.0]
    iterations = 500
    market = Market(area="area_A", active_drivers=2, active_orders=100)
    
    d1 = _make_driver("Elite_Driver", ar=0.99, cr=0.99)
    d2 = _make_driver("Avg_Driver", ar=0.85, cr=0.90)
    drivers = [d1, d2]
    
    results = {tv: {d.id: 0 for d in drivers} for tv in temp_values}
    
    for tv in temp_values:
        for i in range(iterations):
            order = generate_random_order(order_id=f"O_{i}")
            result = allocate_order(order, drivers, market, weights, sub_weights, tv, "softmax", "hard", norm_params)
            if result and result.driver_id:
                results[tv][result.driver_id] += 1
                
    print("Sensitivity Results:")
    with open(os.path.join(output_dir, 'csv', 'sensitivity.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Temperature', 'Elite_Wins', 'Avg_Wins'])
        for tv in temp_values:
            ew = results[tv][d1.id]
            aw = results[tv][d2.id]
            print(f"Temp {tv}: Elite {ew}, Avg {aw}")
            writer.writerow([tv, ew, aw])
            
    plt.figure(figsize=(10, 6))
    tv_str = [str(tv) for tv in temp_values]
    elite_rates = [results[tv][d1.id]/iterations for tv in temp_values]
    avg_rates = [results[tv][d2.id]/iterations for tv in temp_values]
    
    plt.plot(tv_str, elite_rates, marker='o', label='Elite Driver')
    plt.plot(tv_str, avg_rates, marker='s', label='Avg Driver')
    plt.title('Win Rate vs Softmax Temperature')
    plt.xlabel('Temperature')
    plt.ylabel('Win Rate')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, 'charts', 'sensitivity.png'))
    plt.close()
