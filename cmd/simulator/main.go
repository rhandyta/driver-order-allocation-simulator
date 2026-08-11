package main

import (
	"flag"
	"fmt"
	"runtime"
	"driver-order-allocation-simulator/internal/simulation"
)

func main() {
	iterations := flag.Int("iterations", 100000, "Number of Monte Carlo iterations")
	workers := flag.Int("workers", runtime.NumCPU(), "Number of parallel worker goroutines")
	flag.Parse()

	fmt.Printf("=== High-Performance Go Driver Order Allocation Simulator ===\n")
	fmt.Printf("CPU Cores: %d | Worker Goroutines: %d | Iterations: %d\n", runtime.NumCPU(), *workers, *iterations)

	sim := simulation.NewSimulator()
	duration := sim.RunMonteCarloConcurrent(*iterations, *workers)

	rate := float64(*iterations) / duration.Seconds()
	fmt.Printf("\nCompleted %d allocations in %v\n", *iterations, duration)
	fmt.Printf("⚡ Throughput Speed: %.2f allocations/sec\n", rate)
}
