package scoring

import (
	"driver-order-allocation-simulator/internal/model"
	"testing"
)

func TestHaversine(t *testing.T) {
	dist := Haversine(-6.9147, 107.6098, -6.9200, 107.6200)
	if dist <= 0.0 {
		t.Errorf("Expected distance > 0, got %f", dist)
	}
}

func TestCalculateScore(t *testing.T) {
	d := model.Driver{
		ID:             "D1",
		Lat:            -6.91,
		Lon:            107.61,
		ServiceTypes:   []string{"GoRide"},
		Online:         true,
		AcceptanceRate: 1.0,
		CompletionRate: 1.0,
		OnlineHours:    100,
		OnlineDays:     14,
		AccountStatus:  "active",
		DeviceStatus:   "healthy",
	}

	o := model.Order{
		ID:          "O1",
		ServiceType: "GoRide",
		PickupLat:   -6.91,
		PickupLon:   107.61,
	}

	m := model.Market{Area: "area_B", ActiveDrivers: 10, ActiveOrders: 20}
	w := model.DefaultScoringWeights()

	score := CalculateScore(d, o, m, w)
	if score <= 0.0 || score > 100.0 {
		t.Errorf("Expected score in (0, 100], got %f", score)
	}
}
