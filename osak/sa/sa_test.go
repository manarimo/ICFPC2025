package sa

import (
    "context"
    "math/rand"
    "testing"
)

// Simple smoke test: best energy should be <= initial energy.
func TestAnnealMonotonicBest(t *testing.T) {
    // Problem: minimize (x-10)^2 over integers via +/-1 neighbor
    eval := func(x int) float64 {
        d := float64(x - 10)
        return d * d
    }
    neighbor := func(x int, rng *rand.Rand) int {
        if rng.Intn(2) == 0 {
            return x - 1
        }
        return x + 1
    }

    init := 100
    initE := eval(init)

    best, bestE := Anneal[int](context.Background(), init, eval, neighbor, Options[int]{
        Iterations: 200,
        Schedule:   ExponentialSchedule{Start: 5, End: 1e-3},
        RNG:        rand.New(rand.NewSource(1)),
    })

    if bestE > initE+1e-12 {
        t.Fatalf("best energy should not exceed initial: best=%f init=%f bestState=%d", bestE, initE, best)
    }
}

