import argparse
import os
import sys
import yaml

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_default_config():
    root = get_project_root()
    config_path = os.path.join(root, "config", "weights.yaml")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def cmd_simulate(args):
    from .simulation import Simulator, load_config
    config = load_default_config()
    sim = Simulator(config)
    print(f"Running simulation: {args.days} days, {args.drivers} drivers, {args.orders} orders/day")
    sim.run_simulation(args.days, args.drivers, args.orders)
    sim.save_results(os.path.join(get_project_root(), "results"))
    
    stats = sim.get_driver_statistics()
    print(f"\nSimulation complete. Total allocations: {len(sim.results)}")
    print(f"Unique drivers who received orders: {len(stats)}")
    # Print top 10 drivers
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total_orders"], reverse=True)[:10]
    print(f"\nTop 10 Drivers:")
    print(f"{'Driver':<10} {'Orders':<10} {'Probability':<15} {'Avg Score':<10}")
    for did, s in sorted_stats:
        print(f"{did:<10} {s['total_orders']:<10} {s['order_probability']*100:.1f}%{'':8} {s['avg_score']:.1f}")

def cmd_experiment(args):
    # Import experiment modules
    root = get_project_root()
    sys.path.insert(0, root)
    
    experiment_map = {
        "acceptance_rate": "experiments.experiment_ar",
        "completion_rate": "experiments.experiment_cr",
        "history": "experiments.experiment_history",
        "demand": "experiments.experiment_demand",
        "online": "experiments.experiment_online",
        "combined": "experiments.experiment_combined",
        "ml": "experiments.experiment_ml",
    }
    
    if args.name not in experiment_map:
        print(f"Unknown experiment: {args.name}")
        print(f"Available: {', '.join(experiment_map.keys())}")
        return
    
    import importlib
    mod = importlib.import_module(experiment_map[args.name])
    config = load_default_config()
    if args.name == "ml":
        mod.run_ml_experiment(config, output_dir=os.path.join(root, "results"))
    else:
        mod.run_experiment(config, output_dir=os.path.join(root, "results"))

def cmd_monte_carlo(args):
    root = get_project_root()
    sys.path.insert(0, root)
    from experiments.monte_carlo import run_monte_carlo
    config = load_default_config()
    run_monte_carlo(config, iterations=args.iterations, output_dir=os.path.join(root, "results"))

def cmd_sensitivity(args):
    root = get_project_root()
    sys.path.insert(0, root)
    from experiments.sensitivity import run_sensitivity
    config = load_default_config()
    run_sensitivity(config, output_dir=os.path.join(root, "results"))

def cmd_ml_train(args):
    root = get_project_root()
    sys.path.insert(0, root)
    from experiments.experiment_ml import run_ml_experiment
    config = load_default_config()
    run_ml_experiment(config, output_dir=os.path.join(root, "results"))

def cmd_dashboard(args):
    root = get_project_root()
    app_path = os.path.join(root, "app.py")
    print(f"Launching Streamlit Dashboard from {app_path}...")
    os.system(f"python -m streamlit run {app_path}")

def cmd_serve(args):
    import uvicorn
    print(f"Starting FastAPI REST API server on http://localhost:{args.port}...")
    uvicorn.run("src.api:app", host="0.0.0.0", port=args.port, reload=False)

def cmd_animate(args):
    from .animation import DriverTrajectoryAnimator
    root = get_project_root()
    output_gif = os.path.join(root, "results", "charts", "driver_movement.gif")
    print(f"Rendering micro-simulation trajectory animation ({args.ticks} ticks at {args.fps} FPS)...")
    animator = DriverTrajectoryAnimator()
    path = animator.render_gif(output_path=output_gif, ticks=args.ticks, fps=args.fps)
    print(f"Animation successfully rendered and saved to: {path}")

def cmd_init_db(args):
    from .database import MySQLDatabaseManager
    print(f"Connecting to Laragon MySQL (host={args.host}, db={args.db}) and initializing tables...")
    db = MySQLDatabaseManager(host=args.host, port=args.port, user=args.user, password=args.password, database=args.db)
    db.init_db()
    print("[OK] MySQL Database tables (drivers, orders, allocations) successfully created!")


def main():
    parser = argparse.ArgumentParser(description="Driver Order Allocation Simulator")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Run simulation")
    sim_parser.add_argument("--days", type=int, default=14)
    sim_parser.add_argument("--drivers", type=int, default=100)
    sim_parser.add_argument("--orders", type=int, default=50, help="Orders per day")
    
    # experiment
    exp_parser = subparsers.add_parser("experiment", help="Run experiment")
    exp_parser.add_argument("--name", required=True, help="Experiment name")
    
    # monte-carlo
    mc_parser = subparsers.add_parser("monte-carlo", help="Run Monte Carlo simulation")
    mc_parser.add_argument("--iterations", type=int, default=10000)
    
    # sensitivity
    subparsers.add_parser("sensitivity", help="Run sensitivity analysis")
    
    # ml-train
    subparsers.add_parser("ml-train", help="Run Phase 4 & Phase 5 ML training & explainability analysis")
    
    # dashboard
    subparsers.add_parser("dashboard", help="Launch Streamlit Web Dashboard")
    
    # serve
    serve_parser = subparsers.add_parser("serve", help="Launch FastAPI REST API Server")
    serve_parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    # animate
    anim_parser = subparsers.add_parser("animate", help="Render animated GIF of driver movement trajectory")
    anim_parser.add_argument("--ticks", type=int, default=40, help="Number of ticks")
    anim_parser.add_argument("--fps", type=int, default=8, help="Frames per second")
    
    # init-db
    db_parser = subparsers.add_parser("init-db", help="Initialize Laragon MySQL Database Tables")
    db_parser.add_argument("--host", type=str, default="localhost")
    db_parser.add_argument("--port", type=int, default=3306)
    db_parser.add_argument("--user", type=str, default="root")
    db_parser.add_argument("--password", type=str, default="")
    db_parser.add_argument("--db", type=str, default="simulator")
    
    args = parser.parse_args()
    
    if args.command == "simulate":
        cmd_simulate(args)
    elif args.command == "experiment":
        cmd_experiment(args)
    elif args.command == "monte-carlo":
        cmd_monte_carlo(args)
    elif args.command == "sensitivity":
        cmd_sensitivity(args)
    elif args.command == "ml-train":
        cmd_ml_train(args)
    elif args.command == "dashboard":
        cmd_dashboard(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "animate":
        cmd_animate(args)
    elif args.command == "init-db":
        cmd_init_db(args)
    else:
        parser.print_help()






if __name__ == "__main__":
    main()
