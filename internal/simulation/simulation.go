package simulation

import (
	"driver-order-allocation-simulator/internal/allocator"
	"driver-order-allocation-simulator/internal/model"
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type Simulator struct {
	Weights     model.ScoringWeights
	Temperature float64
}

func NewSimulator() *Simulator {
	return &Simulator{
		Weights:     model.DefaultScoringWeights(),
		Temperature: 5.0,
	}
}

func GenerateRandomDriver(id string) model.Driver {
	return model.Driver{
		ID:             id,
		Lat:            -6.91 + (rand.Float64()*0.1 - 0.05),
		Lon:            107.61 + (rand.Float64()*0.1 - 0.05),
		ServiceTypes:   []string{"GoRide", "GoFood"},
		Online:         true,
		AcceptanceRate: 0.7 + rand.Float64()*0.3,
		CompletionRate: 0.8 + rand.Float64()*0.2,
		OnlineHours:    20.0 + rand.Float64()*100.0,
		OnlineDays:     5 + rand.Intn(10),
		AccountStatus:  "active",
		DeviceStatus:   "healthy",
	}
}

func GenerateRandomOrder(id string) model.Order {
	return model.Order{
		ID:                id,
		ServiceType:       "GoRide",
		PickupLat:         -6.91 + (rand.Float64()*0.08 - 0.04),
		PickupLon:         107.61 + (rand.Float64()*0.08 - 0.04),
		DestLat:           -6.92 + (rand.Float64()*0.08 - 0.04),
		DestLon:           107.62 + (rand.Float64()*0.08 - 0.04),
		Timestamp:         time.Now(),
		EstimatedDistance: 1.0 + rand.Float64()*10.0,
		EstimatedDuration: 5.0 + rand.Float64()*25.0,
	}
}

func (s *Simulator) RunMonteCarloConcurrent(iterations int, numWorkers int) time.Duration {
	startTime := time.Now()
	var wg sync.WaitGroup
	tasksPerWorker := iterations / numWorkers

	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			r := rand.New(rand.NewSource(time.Now().UnixNano() + int64(workerID)))

			drivers := make([]model.Driver, 30)
			for i := 0; i < 30; i++ {
				drivers[i] = GenerateRandomDriver(fmt.Sprintf("D%03d", i+1))
			}

			market := model.Market{Area: "area_B", ActiveDrivers: 30, ActiveOrders: 15}

			for i := 0; i < tasksPerWorker; i++ {
				order := GenerateRandomOrder(fmt.Sprintf("O%04d", i+1))
				_ = r
				allocator.AllocateOrder(order, drivers, market, s.Weights, s.Temperature)
			}
		}(w)
	}

	wg.Wait()
	return time.Since(startTime)
}
