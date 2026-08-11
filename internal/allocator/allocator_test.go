package allocator

import (
	"driver-order-allocation-simulator/internal/model"
	"testing"
)

func TestSoftmaxProbabilities(t *testing.T) {
	drivers := []model.Driver{
		{ID: "D1", Score: 90.0},
		{ID: "D2", Score: 70.0},
	}

	probs := SoftmaxProbabilities(drivers, 5.0)
	if len(probs) != 2 {
		t.Fatalf("Expected 2 drivers, got %d", len(probs))
	}

	if probs[0].Probability <= probs[1].Probability {
		t.Errorf("Expected driver with higher score to have higher probability")
	}

	totalProb := probs[0].Probability + probs[1].Probability
	if totalProb < 0.99 || totalProb > 1.01 {
		t.Errorf("Expected total probability ~1.0, got %f", totalProb)
	}
}
