package model

import "time"

type Driver struct {
	ID             string             `json:"id"`
	Lat            float64            `json:"lat"`
	Lon            float64            `json:"lon"`
	ServiceTypes   []string           `json:"service_types"`
	Online         bool               `json:"online"`
	AcceptanceRate float64            `json:"acceptance_rate"`
	CompletionRate float64            `json:"completion_rate"`
	OnlineHours    float64            `json:"online_hours"`
	OnlineDays     int                `json:"online_days"`
	History        map[string]map[string]int `json:"history"`
	AccountStatus  string             `json:"account_status"`
	DeviceStatus   string             `json:"device_status"`
	Score          float64            `json:"score"`
	Probability    float64            `json:"probability"`
}

type Order struct {
	ID                string    `json:"id"`
	ServiceType       string    `json:"service_type"`
	PickupLat         float64   `json:"pickup_lat"`
	PickupLon         float64   `json:"pickup_lon"`
	DestLat           float64   `json:"dest_lat"`
	DestLon           float64   `json:"dest_lon"`
	Timestamp         time.Time `json:"timestamp"`
	EstimatedDistance float64   `json:"estimated_distance"`
	EstimatedDuration float64   `json:"estimated_duration"`
}

type Market struct {
	Area          string `json:"area"`
	ActiveDrivers int    `json:"active_drivers"`
	ActiveOrders  int    `json:"active_orders"`
}

type ScoringWeights struct {
	Demand            float64
	History           float64
	Service           float64
	Time              float64
	Distance          float64
	ETA               float64
	CompletionRate    float64
	AcceptanceRate    float64
	OnlineConsistency float64
}

type AllocationResult struct {
	Timestamp   string  `json:"timestamp"`
	OrderID     string  `json:"order_id"`
	DriverID    string  `json:"driver_id"`
	Score       float64 `json:"score"`
	Probability float64 `json:"probability"`
	Result      string  `json:"result"`
}

func DefaultScoringWeights() ScoringWeights {
	return ScoringWeights{
		Demand:            30.0,
		History:           20.0,
		Service:           15.0,
		Time:              10.0,
		Distance:          10.0,
		ETA:               5.0,
		CompletionRate:    5.0,
		AcceptanceRate:    3.0,
		OnlineConsistency: 2.0,
	}
}
