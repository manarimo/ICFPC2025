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

The core idea of the solution was to figure out the order of the rooms visited. The ordering must be consistent with a random walk in the library.
Our SA directly optimizes the ordering, followed by the postprocessor that reconstructs the door connection by combining the visit ordering and the executed plan.

Full-SA based double/triple solver extends the original idea; it optimizes whether the room is "original" or "mirror" in addition to the room ordering. Unfortunately, it caused explosion in the number of possible states which made it only feasible to solve very small instances.

The "labeling" approach was the main strategy that solved most double and triple problems. It is based on an essential assumption: these problems are made by copying the same map twice or thrice to make layers. Then edges are "shuffled" so an edge may connect the same node but in the "copied" map, allowing us to navigate through different layers while the entire map indistinguishable from single-layer one by labels. These are not clearly written in the problem specs but almost certain from the storytelling and some manual testing.

Our solution to the double and triple problems consists of two steps; the first step determines the graph of a single layer of the library. It is straightforward because given that those maps are indistinguishable from single-layer one, the goal is identical to that of the lightning round.
Once we get the structure of a layer, we can start distinguishing one layer from another by relabeling each room when entered for the first time. The exploration result will be examined in pair with the executed plan; assuming the graph obtained from the first step is correct, we known which room we are in (ignoreing difference of layers). If the observed label was different from that on the single layer map, it must be the one we've relabeled earlier. In this way, we can distinguish the "original" room and the "mirror" room to reconstruct the full graph.

For the triple problems, the second phase is repeated twice; first run determines one of the layers, then the following run determines other layer.

In practice, SA carried end‑to‑end. Constraint solving (Z3) was explored but did not improve outcomes over tuned SA when integrated into our pipeline.

## What Actually Worked in Production

- Main solvers used for official submissions:
  - Lightning: `kawatea/simulated_annealing.cpp`.
  - Double: `kawatea/double.cpp`.
  - Most triple: `hebrew-double` pipeline (despite the name, it mainly handled triple).
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
  - Heavily used for local testing, since the contest server cannot handle multiple sessions concurrently.

- Frontend UI / proxy: `wizardry/`
  - Next.js app with API routes that proxy to either mock or official backend.
  - Useful for early inspection; later de‑emphasized.

- Solvers / runners:
  - Simulated Annealing (C++): `kawatea/simulated_annealing.cpp` (Lightning), `kawatea/double.cpp` (Full, doubles), `hebrew-double/simulated_annealing.cpp + parallel.py` (mostly triples), `megamix/solver/*`.
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
- `wrapper/` — FIFO↔HTTP adapter for solvers (not used actually).
- `kawatea/`, `hebrew-double/`, `megamix/` — SA solvers and orchestrators.
- `sakazuki/` — Z3 prototype.
- `vertrages/` — Lightning (single) solver.
- `higashi-matsudo/` — Rust client, zero‑shot, visualization.
- `shin-kamagaya/` — Cytoscape visualizer.
- `graph-dump/` — Accepted solutions from the official server.
