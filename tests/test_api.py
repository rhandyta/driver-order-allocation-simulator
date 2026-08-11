import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_score_endpoint():
    payload = {
        "driver": {
            "id": "D001",
            "location": [-6.9147, 107.6098],
            "service_types": ["GoRide"],
            "online": True,
            "acceptance_rate": 0.9,
            "completion_rate": 0.9,
            "online_hours": 50,
            "online_days": 10
        },
        "order": {
            "id": "O001",
            "service_type": "GoRide",
            "pickup": [-6.9150, 107.6100],
            "destination": [-6.9200, 107.6200]
        }
    }
    response = client.post("/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["driver_id"] == "D001"
    assert "total_score" in data
    assert "component_breakdown" in data

def test_allocate_endpoint():
    payload = {
        "drivers": [
            {"id": "D001", "location": [-6.9147, 107.6098], "service_types": ["GoRide"], "online": True},
            {"id": "D002", "location": [-6.9500, 107.6100], "service_types": ["GoRide"], "online": True}
        ],
        "order": {
            "id": "O001",
            "service_type": "GoRide",
            "pickup": [-6.9150, 107.6100],
            "destination": [-6.9200, 107.6200]
        }
    }
    response = client.post("/allocate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "O001"
    assert data["driver_id"] in ["D001", "D002"]
    assert data["result"] == "allocated"

def test_predict_ml_endpoint():
    payload = {
        "driver": {"id": "D001", "location": [-6.9147, 107.6098], "service_types": ["GoRide"], "online": True},
        "order": {"id": "O001", "service_type": "GoRide", "pickup": [-6.9150, 107.6100], "destination": [-6.9200, 107.6200]}
    }
    response = client.post("/predict-ml", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predicted_allocation_probability" in data
