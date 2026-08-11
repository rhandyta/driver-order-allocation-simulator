import os
import pytest
from src.animation import DriverTrajectoryAnimator

def test_driver_trajectory_animator_render(tmp_path):
    output_gif = os.path.join(tmp_path, "test_movement.gif")
    animator = DriverTrajectoryAnimator()
    
    saved_path = animator.render_gif(output_path=output_gif, ticks=5, fps=2)
    assert os.path.exists(saved_path)
    assert os.path.getsize(saved_path) > 0
