# Walkthrough — Driver Order Allocation Simulator

## Summary

Berhasil membangun **Driver Order Allocation Simulator** lengkap sesuai spesifikasi [README.md](file:///d:/Project/python/driver-order-allocation-simulator/README.md). Simulator mengimplementasi Phase 1–3 dari roadmap (Rule-Based Scoring, Historical Profile, Monte Carlo).

---

## Project Structure

```
driver-order-allocation-simulator/
├── README.md
├── requirements.txt
├── config/
│   └── weights.yaml          # Scoring weights & parameters
├── data/
│   ├── drivers.json           # 10 sample drivers (Bandung)
│   ├── orders.json            # 5 sample orders
│   └── market.json            # 3 area market conditions
├── src/
│   ├── __init__.py
│   ├── models.py              # Driver, Order, Market, ScoringWeights, etc.
│   ├── eligibility.py         # Eligibility filter (hard/soft)
│   ├── features.py            # Feature extraction (haversine, time_fit, etc.)
│   ├── scoring.py             # Weighted scoring engine
│   ├── allocator.py           # Softmax allocation + ranking
│   ├── history.py             # Rolling window history manager
│   ├── market.py              # Market data loading/generation
│   ├── simulation.py          # Full simulation engine
│   └── main.py                # CLI (argparse)
├── experiments/
│   ├── experiment_ar.py       # Exp A: Acceptance Rate
│   ├── experiment_cr.py       # Exp B: Completion Rate
│   ├── experiment_history.py  # Exp C+D: History Fit + Area
│   ├── experiment_demand.py   # Exp E: Demand/Supply
│   ├── experiment_online.py   # Exp F: Online Consistency
│   ├── experiment_combined.py # Exp G: Combined Profile
│   ├── monte_carlo.py         # Monte Carlo simulation
│   └── sensitivity.py         # Sensitivity analysis
├── tests/
│   ├── test_scoring.py        # 6 scoring tests
│   ├── test_history.py        # 6 history tests
│   └── test_allocator.py      # 8 allocator tests
└── results/
    ├── csv/                   # Generated CSV outputs
    └── charts/                # Generated chart PNGs
```

---

## Key Components

### Scoring Model
Formula: `score(driver, order) = Σ(weight_i × feature_i)`

| Feature | Weight | Description |
|---------|--------|-------------|
| Demand/Supply | 30 | Market ratio normalized |
| Historical Fit | 20 | Composite: service + area + time + distance |
| Service Fit | 15 | Historical service type ratio |
| Time Fit | 10 | Time slot match |
| Distance (Location) | 10 | Haversine proximity |
| ETA Fit | 5 | Estimated pickup ETA |
| Completion Rate | 5 | Driver CR |
| Acceptance Rate | 3 | Driver AR |
| Online Consistency | 2 | Hours + days normalized |

### Allocation
- **Softmax probabilistic**: `P(d_i) = exp(score_i/T) / Σ exp(score_j/T)`
- **Deterministic**: always pick rank #1
- Configurable temperature parameter

### Historical Profile
- 14-day rolling window
- Tracks: services, areas, time_slots, distance_buckets per day
- Automatic aggregation and driver state updates

---

## CLI Commands

```bash
# Basic simulation
python -m src.main simulate --days 14 --drivers 100 --orders 50

# Run experiments
python -m src.main experiment --name acceptance_rate
python -m src.main experiment --name completion_rate
python -m src.main experiment --name history
python -m src.main experiment --name demand
python -m src.main experiment --name online
python -m src.main experiment --name combined

# Monte Carlo
python -m src.main monte-carlo --iterations 10000

# Sensitivity Analysis
python -m src.main sensitivity
```

---

## Verification Results

### Tests: 20/20 PASSED ✅

```
tests/test_allocator.py  - 8 passed
tests/test_history.py    - 6 passed
tests/test_scoring.py    - 6 passed
```

### Simulation: ✅
- 14 days, 50 drivers, 200 orders/day → 2,800 allocations
- All 50 drivers received orders (probabilistic distribution)

### Experiments: ✅
- AR experiment: shows AR influence on win probability
- Combined profile: demonstrates Historical Fit driver outperforming Perfect AR/CR driver
- Monte Carlo: 1000 iterations producing distribution statistics
- Sensitivity: temperature analysis showing scoring discrimination

### Output Files: ✅
- `results/csv/allocation.csv` — full allocation log
- `results/csv/driver_statistics.csv` — per-driver statistics
- `results/csv/experiment_*.csv` — experiment results
- `results/charts/*.png` — visualization charts
