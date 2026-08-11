import pytest
from src.spatial_h3 import H3SpatialManager
from src.models import Driver, Order

def test_h3_coord_to_cell():
    loc = (-6.9147, 107.6098)  # Bandung center
    cell = H3SpatialManager.coord_to_h3(loc, res=8)
    assert isinstance(cell, str)
    assert len(cell) == 15

def test_h3_grid_distance():
    loc1 = (-6.9147, 107.6098)
    loc2 = (-6.9150, 107.6100)
    cell1 = H3SpatialManager.coord_to_h3(loc1, res=8)
    cell2 = H3SpatialManager.coord_to_h3(loc2, res=8)
    
    dist = H3SpatialManager.get_h3_distance(cell1, cell2)
    assert dist >= 0
    assert H3SpatialManager.get_h3_distance(cell1, cell1) == 0

def test_h3_k_ring_neighbors():
    loc = (-6.9147, 107.6098)
    cell = H3SpatialManager.coord_to_h3(loc, res=8)
    neighbors = H3SpatialManager.get_h3_neighbors(cell, k=1)
    
    assert len(neighbors) == 7  # Center + 6 surrounding hexagons
    assert cell in neighbors

def test_h3_area_fit_scoring():
    loc_center = (-6.9147, 107.6098)
    cell_center = H3SpatialManager.coord_to_h3(loc_center, res=8)
    
    # Driver history with 10 trips in exact center cell
    history_exact = {
        "h3_cells": {
            cell_center: 10
        }
    }
    
    score_exact = H3SpatialManager.calculate_h3_area_fit(history_exact, loc_center, res=8)
    assert score_exact == 1.0
    
    # Driver history with trips in neighbor cell
    neighbors = H3SpatialManager.get_h3_neighbors(cell_center, k=1)
    neighbor_cell = [c for c in neighbors if c != cell_center][0]
    history_neighbor = {
        "h3_cells": {
            neighbor_cell: 10
        }
    }
    
    score_neighbor = H3SpatialManager.calculate_h3_area_fit(history_neighbor, loc_center, res=8)
    assert score_neighbor == 0.5  # 1st-ring neighbor weight decay
