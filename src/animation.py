import os
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from typing import List, Dict, Tuple, Optional
from .models import Driver, Order
from .simulation import generate_random_driver, generate_random_order
from .microsimulation import MicroSimulationEngine, DriverState

class DriverTrajectoryAnimator:
    """Renders micro-simulation real-time driver movement trajectories to animated GIF files."""
    
    def __init__(self, drivers: Optional[List[Driver]] = None, config: Optional[Dict] = None):
        self.config = config or {"scoring_weights": {"distance": 50, "demand": 50}}
        self.drivers = drivers or [generate_random_driver(f"D{i+1:03d}") for i in range(12)]
        self.engine = MicroSimulationEngine(self.drivers, self.config)

    def render_gif(self, output_path: str = "results/charts/driver_movement.gif", ticks: int = 40, fps: int = 8) -> str:
        """Render micro-simulation driver movement animation and save to GIF."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Capture frame snapshots
        frames_data = []
        for t in range(ticks):
            orders = [generate_random_order(f"O_{t}_{i}") for i in range(1)] if t % 8 == 0 else None
            self.engine.tick(delta_seconds=5.0, new_orders=orders)
            
            snapshot = {
                "clock": int(self.engine.clock_seconds),
                "drivers": [(md.driver.id, md.current_location, md.state) for md in self.engine.micro_drivers],
                "active_orders": [(r.order_id, r.driver_id) for r in self.engine.allocation_log[-5:]]
            }
            frames_data.append(snapshot)
            
        # Matplotlib animation rendering
        fig, ax = plt.subplots(figsize=(9, 6))
        
        def update_frame(frame_idx):
            ax.clear()
            snap = frames_data[frame_idx]
            
            idle_lats, idle_lons = [], []
            pickup_lats, pickup_lons = [], []
            trip_lats, trip_lons = [], []
            
            for did, loc, state in snap["drivers"]:
                if state == DriverState.IDLE:
                    idle_lats.append(loc[0])
                    idle_lons.append(loc[1])
                elif state == DriverState.EN_ROUTE_PICKUP:
                    pickup_lats.append(loc[0])
                    pickup_lons.append(loc[1])
                elif state == DriverState.TRIP_IN_PROGRESS:
                    trip_lats.append(loc[0])
                    trip_lons.append(loc[1])

            if idle_lons:
                ax.scatter(idle_lons, idle_lats, c="#2b5c8f", label="IDLE", s=60, alpha=0.8, marker="o")
            if pickup_lons:
                ax.scatter(pickup_lons, pickup_lats, c="#e67e22", label="EN_ROUTE_PICKUP", s=80, alpha=0.9, marker="^")
            if trip_lons:
                ax.scatter(trip_lons, trip_lats, c="#27ae60", label="TRIP_IN_PROGRESS", s=80, alpha=0.9, marker="s")

            ax.set_title(f"Driver Movement Trajectory Simulation — Time: {snap['clock']}s (Frame {frame_idx+1}/{ticks})")
            ax.set_xlabel("Longitude")
            ax.set_ylabel("Latitude")
            ax.legend(loc="upper right")
            ax.grid(True, linestyle="--", alpha=0.5)

        anim = animation.FuncAnimation(fig, update_frame, frames=len(frames_data), interval=1000//fps)
        writer = animation.PillowWriter(fps=fps)
        anim.save(output_path, writer=writer)
        plt.close(fig)
        
        return output_path
