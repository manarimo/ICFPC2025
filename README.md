# ICFPC2025 Team manarimo

## Members
* Kenkou Nakamura (@kenkoooo)
* mkut
* Osamu Koga (@osa_k)
* Shunsuke Ohashi (@pepsin_amylase)
* Yu Fujikake (@yuusti)
* Yuki Kawata (@kawatea03)

## Strategy Summary

We attacked ICFPC 2025’s Ædificium reconstruction with a pragmatic, solver‑driven approach centered on simulated annealing (SA), complemented by targeted plan design and light tooling around the official API.

- We model each problem as a graph of hex rooms (6 doors/room) with labels in {0..3}. Route plans are strings of door indices (`0..5`) with optional charcoal injections (`[k]`) to overwrite labels in‑flight.
- We stage by duplication mode:
  - Single: straightforward reconstruction from randomized plans.
  - Double: cover the reduced graph, then use charcoal to detect cross‑layer transitions and stitch edges.
  - Triple: identify B‑layer entrances, inject specific charcoal to separate B/C, then finalize connections.
- We run multiple SA workers in parallel and stop early on first valid reconstruction.

In practice, SA carried end‑to‑end. Constraint solving (Z3) was explored but did not improve outcomes over tuned SA when integrated into our pipeline.

## What Actually Worked in Production

- Main solvers used for official submissions:
  - Lightning and most Double: `kawatea/simulated_annealing.cpp`.
  - Triple: `hebrew-double` pipeline (despite the name, it mainly handled triple).
  - Z3 (“sakazuki”) was a good try but performed roughly on par with SA; we stuck with SA.
- SA was used all the way through reconstruction.
- Wizardry UI (Next.js) helped very early to understand the spec, but we quickly moved to automated tooling.
- `graph-dump/*` contains solutions accepted by the official server. We used these to attempt reverse‑engineering the generator; we concluded instances were “random enough” to not exploit special structure.
- Runtime/knobs:
  - Most problems: ~20 minutes total, ~1 minute per iteration.
  - The most effective “knob” was randomness itself (instance randomness, SA randomness, route randomness). Good runs happen when the probabilistic pieces line up.

## Pipeline at a Glance

1) Exploration (plan design)
   - Generate random walks up to 6×rooms moves; inject charcoal when helpful to disambiguate layers.
   - Batch `/explore` with multi‑plan requests.

2) Reconstruction (edge synthesis)
   - Aggregate (room,door) → destination from exploration traces.
   - For Double/Triple, use layer‑aware helpers: `build_dest_maps_double`, `build_layer_b_pos`, `inject_charcoal_to_walk_triple`, `build_dest_maps_triple`.
   - Run SA to produce a consistent door‑destination layout; validate and build undirected connections.

3) Validation and early stop
   - Submit `/guess`; on success, terminate other workers (“first success wins”).

## Key Components

- Mock API server: `lord-crossight/`
  - Endpoints: `/select`, `/explore`, `/guess`, `/compare`, `/spoiler`.
  - Persists per‑id state; deployable to Cloud Run.

- Frontend UI / proxy: `wizardry/`
  - Next.js app with API routes that proxy to either mock or official backend.
  - Useful for early inspection; later de‑emphasized.

- Wrapper (FIFO ↔ HTTP): `wrapper/`
  - Converts a simple text protocol to JSON API calls so binaries can talk to the server reliably.

- Solvers / runners:
  - Simulated Annealing (C++): `kawatea/simulated_annealing.cpp`, `hebrew-double/simulated_annealing.cpp`, `megamix/solver/*`.
  - Parallel driver for Double/Triple: `hebrew-double/parallel.py` (orchestrates plans, SA workers, charcoal strategy).
  - Lightning solver (hash‑based): `vertrages/main.py` (fast single‑map reconstruction).
  - Z3 prototype: `sakazuki/main.py` (kept for reference; not used in final submissions).
  - Rust client/tools: `higashi-matsudo/*` (API client, visualization, graph dump utilities).
  - Visualization: `shin-kamagaya/main.py` (cytoscape), Rust `visualize-graph.rs`.

- Data: `graph-dump/*`
  - Officially accepted solutions, organized by set, used for offline analysis and visualization.

## Notes on Plan Design

- Route length limit per night is ~6×N moves; we respect this in generators and batch multiple plans per `/explore`.
- Charcoal (`[k]`) is injected strategically:
  - Double: overwrite on first unseen visits in the reduced graph to detect layer transitions.
  - Triple: first identify B‑layer entrance indices, then insert charcoal to separate B/C labels deterministically.

## Ops / Running Locally

- Local stack via docker-compose: mock API (`lord-crossight`), UI (`wizardry`), wrapper.
- Wrapper: build `wrapper` and use named pipes (`/tmp/to-wrapper`, `/tmp/from-wrapper`) to drive API calls from native solvers.
- Runners: `megamix/arena.py` provides `build/run/eval` CLIs; `hebrew-double/parallel.py` runs the parallel pipeline with mode inference and early termination.

## Repository Map (selected)

- `lord-crossight/` — Mock API and reference `Aedificium` implementation.
- `wizardry/` — Next.js UI and proxy.
- `wrapper/` — FIFO↔HTTP adapter for solvers.
- `kawatea/`, `hebrew-double/`, `megamix/` — SA solvers and orchestrators.
- `sakazuki/` — Z3 prototype.
- `vertrages/` — Lightning (single) solver.
- `higashi-matsudo/` — Rust client, zero‑shot, visualization.
- `shin-kamagaya/` — Cytoscape visualizer.
- `graph-dump/` — Accepted solutions from the official server.
