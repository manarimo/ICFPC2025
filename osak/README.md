Simulated Annealing Scaffold (Go)

Overview

- Package `sa`: Generic simulated annealing utilities using Go generics.
- Example CLI: `cmd/sa_example` shows minimizing a simple integer function.

Quick Start

1) Example run

  - Build and run the example:

    go run ./cmd/sa_example

2) Library usage

  - Define an evaluator (lower is better):

    // energy of state S
    type Evaluator[S any] func(S) float64

  - Define a neighbor function:

    // propose a nearby candidate
    type NeighborFunc[S any] func(S, *rand.Rand) S

  - Choose a schedule (exponential or linear), set iterations and RNG in `sa.Options[S]`, and call:

    best, bestEnergy := sa.Anneal(ctx, initState, eval, neighbor, opts)

Design Notes

- Minimization only: pass energy you want to minimize.
- Temperature schedules: `ExponentialSchedule` and `LinearSchedule` provided.
- Hooks: optional per-iteration callback for logging/plotting.
- Context: cancelable via `context.Context`.

Files

- `sa/sa.go`: Core algorithm and schedules.
- `sa/sa_test.go`: Minimal smoke test.
- `cmd/sa_example/main.go`: Demo program.

