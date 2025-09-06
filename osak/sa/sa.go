package sa

import (
    "context"
    "math"
    "math/rand"
    "time"
)

// Evaluator computes the energy (cost) of a state. Lower is better.
type Evaluator[S any] func(S) float64

// NeighborFunc proposes a nearby candidate state based on the current one.
// It should avoid mutating its input unless S is a pointer type and such
// mutation is intended. Prefer returning a fresh value to keep usage simple.
type NeighborFunc[S any] func(S, *rand.Rand) S

// Schedule provides a temperature for a given iteration of a finite run.
// total is the intended number of iterations for the run.
type Schedule interface {
    Temperature(iter, total int) float64
}

// ExponentialSchedule cools temperature exponentially from Start to End
// across the specified number of iterations in Anneal.
type ExponentialSchedule struct {
    Start float64
    End   float64
}

func (e ExponentialSchedule) Temperature(iter, total int) float64 {
    if total <= 1 {
        return e.End
    }
    if e.Start <= 0 || e.End <= 0 {
        // Fall back to a small positive temperature to avoid div-by-zero
        return 1e-9
    }
    // Geometric decay from Start to End over [0..total-1]
    frac := float64(iter) / float64(total-1)
    return e.Start * math.Pow(e.End/e.Start, frac)
}

// LinearSchedule cools temperature linearly from Start to End.
type LinearSchedule struct {
    Start float64
    End   float64
}

func (l LinearSchedule) Temperature(iter, total int) float64 {
    if total <= 1 {
        return l.End
    }
    frac := float64(iter) / float64(total-1)
    return l.Start + frac*(l.End-l.Start)
}

// Hook is an optional callback invoked each iteration.
// It can be used for logging, plotting, or adaptive control.
type Hook[S any] func(iter int, current S, currentEnergy float64, best S, bestEnergy float64, temperature float64)

// Options bundles configuration for Anneal.
type Options[S any] struct {
    // Iterations to perform. Must be >= 1.
    Iterations int
    // Schedule controls the temperature per iteration. If nil, a default
    // exponential schedule is used.
    Schedule Schedule
    // RNG used for proposals and acceptance. If nil, a time-based RNG is used.
    RNG *rand.Rand
    // Hook receives iteration updates. Optional.
    Hook Hook[S]
}

// Anneal performs simulated annealing for the provided problem.
//
// - init: initial state
// - eval: returns energy (to minimize)
// - neighbor: proposes a candidate near the current state
// - opts: run configuration
//
// Returns the best state and its energy encountered during the run.
func Anneal[S any](ctx context.Context, init S, eval Evaluator[S], neighbor NeighborFunc[S], opts Options[S]) (best S, bestEnergy float64) {
    total := opts.Iterations
    if total <= 0 {
        total = 1
    }

    schedule := opts.Schedule
    if schedule == nil {
        schedule = ExponentialSchedule{Start: 1.0, End: 1e-3}
    }

    rng := opts.RNG
    if rng == nil {
        rng = rand.New(rand.NewSource(time.Now().UnixNano()))
    }

    // Initialize
    current := init
    currentEnergy := eval(current)
    best = current
    bestEnergy = currentEnergy

    hook := opts.Hook

    for iter := 0; iter < total; iter++ {
        select {
        case <-ctx.Done():
            return best, bestEnergy
        default:
        }

        temp := schedule.Temperature(iter, total)
        candidate := neighbor(current, rng)
        candEnergy := eval(candidate)

        // Accept if better, or with Boltzmann probability if worse.
        if accept(currentEnergy, candEnergy, temp, rng) {
            current = candidate
            currentEnergy = candEnergy
        }

        if currentEnergy < bestEnergy {
            best = current
            bestEnergy = currentEnergy
        }

        if hook != nil {
            hook(iter, current, currentEnergy, best, bestEnergy, temp)
        }
    }

    return best, bestEnergy
}

// accept determines whether to accept the candidate state.
func accept(curr, cand, temp float64, rng *rand.Rand) bool {
    if cand < curr {
        return true
    }
    if temp <= 0 {
        return false
    }
    // Probability = exp(-(cand-curr)/temp)
    p := math.Exp(-(cand-curr) / temp)
    return rng.Float64() < p
}

