package allocator

import (
	"driver-order-allocation-simulator/internal/eligibility"
	"driver-order-allocation-simulator/internal/model"
	"driver-order-allocation-simulator/internal/scoring"
	"math"
	"math/rand"
	"sort"
)

func SoftmaxProbabilities(drivers []model.Driver, temperature float64) []model.Driver {
	if len(drivers) == 0 {
		return drivers
	}

	maxScore := -1000.0
	for _, d := range drivers {
		if d.Score > maxScore {
			maxScore = d.Score
		}
	}

	expSum := 0.0
	expScores := make([]float64, len(drivers))
	for i, d := range drivers {
		shifted := (d.Score - maxScore) / temperature
		expVal := math.Exp(shifted)
		expScores[i] = expVal
		expSum += expVal
	}

	result := make([]model.Driver, len(drivers))
	for i, d := range drivers {
		prob := expScores[i] / expSum
		d.Probability = prob
		result[i] = d
	}
	return result
}

func AllocateOrder(order model.Order, drivers []model.Driver, market model.Market, weights model.ScoringWeights, temperature float64) (model.AllocationResult, bool) {
	eligible := eligibility.FilterEligible(drivers, order, "hard")
	if len(eligible) == 0 {
		return model.AllocationResult{}, false
	}

	scored := scoring.ScoreAllCandidates(eligible, order, market, weights)

	sort.Slice(scored, func(i, j int) bool {
		return scored[i].Score > scored[j].Score
	})

	withProbs := SoftmaxProbabilities(scored, temperature)

	r := rand.Float64()
	cumulative := 0.0
	winnerIdx := 0
	for i, d := range withProbs {
		cumulative += d.Probability
		if r <= cumulative {
			winnerIdx = i
			break
		}
	}

	winner := withProbs[winnerIdx]
	return model.AllocationResult{
		Timestamp:   order.Timestamp.Format("2006-01-02 15:04:05"),
		OrderID:     order.ID,
		DriverID:    winner.ID,
		Score:       winner.Score,
		Probability: winner.Probability,
		Result:      "allocated",
	}, true
}
