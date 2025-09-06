package main

import (
    "context"
    "fmt"
    "math"
    "math/rand"
    "time"

    "osak/sa"
)

// Example problem: Find integer x close to target T by minimizing (x-T)^2.
// State is simply an int.

func main() {
    ctx := context.Background()

    const target = 42
    evaluator := func(x int) float64 {
        d := float64(x - target)
        return d * d
    }

    neighbor := func(x int, rng *rand.Rand) int {
        step := rng.Intn(11) - 5 // [-5, +5]
        nx := x + step
        // clamp to a reasonable range to avoid runaway
        if nx < -1000 {
            nx = -1000
        } else if nx > 1000 {
            nx = 1000
        }
        return nx
    }

    opts := sa.Options[int]{
        Iterations: 5000,
        Schedule:   sa.ExponentialSchedule{Start: 10, End: 1e-3},
        RNG:        rand.New(rand.NewSource(time.Now().UnixNano())),
        Hook: func(iter int, current int, currentEnergy float64, best int, bestEnergy float64, temp float64) {
            // Print occasionally; keep output light.
            if iter%1000 == 0 {
                fmt.Printf("iter=%4d temp=%.4f curr=%d E=%.4f best=%d Eb=%.4f\n", iter, temp, current, currentEnergy, best, bestEnergy)
            }
        },
    }

    init := 250 // an intentionally bad start
    best, e := sa.Anneal[int](ctx, init, evaluator, neighbor, opts)
    fmt.Printf("\nBest: x=%d energy=%.6f (distance=%.6f)\n", best, e, math.Sqrt(e))
}

