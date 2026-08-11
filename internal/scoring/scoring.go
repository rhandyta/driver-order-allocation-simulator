package scoring

import (
	"driver-order-allocation-simulator/internal/model"
	"math"
)

func Haversine(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371.0
	dLat := (lat2 - lat1) * math.Pi / 180.0
	dLon := (lon2 - lon1) * math.Pi / 180.0

	l1 := lat1 * math.Pi / 180.0
	l2 := lat2 * math.Pi / 180.0

	a := math.Sin(dLat/2)*math.Sin(dLat/2) + math.Sin(dLon/2)*math.Sin(dLon/2)*math.Cos(l1)*math.Cos(l2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return R * c
}

func Normalize(val, minVal, maxVal float64) float64 {
	if maxVal <= minVal {
		return 0.0
	}
	norm := (val - minVal) / (maxVal - minVal)
	if norm < 0.0 {
		return 0.0
	}
	if norm > 1.0 {
		return 1.0
	}
	return norm
}

func CalculateScore(driver model.Driver, order model.Order, market model.Market, weights model.ScoringWeights) float64 {
	// 1. Demand score
	ratio := float64(market.ActiveOrders) / math.Max(float64(market.ActiveDrivers), 1.0)
	dScore := Normalize(ratio, 0.0, 5.0)

	// 2. Location score
	dist := Haversine(driver.Lat, driver.Lon, order.PickupLat, order.PickupLon)
	locScore := 1.0 - Normalize(dist, 0.0, 15.0)

	// 3. ETA fit
	etaMinutes := (dist / 20.0) * 60.0
	etaScore := 1.0 - Normalize(etaMinutes, 0.0, 45.0)

	// 4. Performance scores
	arScore := driver.AcceptanceRate
	crScore := driver.CompletionRate

	// 5. Online consistency
	hoursNorm := Normalize(driver.OnlineHours, 0.0, 120.0)
	daysNorm := Normalize(float64(driver.OnlineDays), 0.0, 14.0)
	ocScore := (hoursNorm + daysNorm) / 2.0

	total := weights.Demand*dScore +
		weights.Distance*locScore +
		weights.ETA*etaScore +
		weights.AcceptanceRate*arScore +
		weights.CompletionRate*crScore +
		weights.OnlineConsistency*ocScore +
		weights.History*0.5 + // baseline neutral history
		weights.Service*1.0 +
		weights.Time*0.5

	return total
}

func ScoreAllCandidates(drivers []model.Driver, order model.Order, market model.Market, weights model.ScoringWeights) []model.Driver {
	scored := make([]model.Driver, len(drivers))
	for i, d := range drivers {
		s := CalculateScore(d, order, market, weights)
		d.Score = s
		scored[i] = d
	}
	return scored
}
