from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Hashable, Iterable, List, Optional, Sequence, Tuple, TypeVar


StateT = TypeVar("StateT")


@dataclass
class _Entry(Generic[StateT]):
    state: StateT
    score: float
    step: int


class BeamSearch(Generic[StateT]):
    """Generic beam search.

    Maintains up to ``beam_size`` states per step. At each step it expands all
    states in the current beam using ``expand`` and scores them with ``score``,
    then keeps the best ``beam_size`` for the next step.

    This implementation is deterministic (stable tie-breaking) and supports
    both minimization and maximization.

    Parameters
    - beam_size: maximum number of states kept each step.
    - max_steps: hard limit on the number of expansion steps. If ``None``,
      must be provided at ``run`` call time.
    - deduplicate: whether to drop duplicate states (as defined by ``key``)
      within each step to improve diversity.
    - key: function mapping a state to a hashable key for deduplication.
      Defaults to identity when the state is hashable, otherwise falls back to
      Python object identity.
    - maximize: if True, higher scores are better; otherwise lower scores are
      better (default).
    """

    def __init__(
        self,
        *,
        beam_size: int,
        max_steps: Optional[int] = None,
        deduplicate: bool = True,
        key: Optional[Callable[[StateT], Hashable]] = None,
        maximize: bool = False,
    ) -> None:
        if beam_size <= 0:
            raise ValueError("beam_size must be positive")
        self.beam_size = int(beam_size)
        self.default_max_steps = max_steps
        self.deduplicate = deduplicate
        self.key_fn = key
        self.maximize = maximize

    def _key(self, state: StateT) -> Hashable:
        if self.key_fn is not None:
            return self.key_fn(state)
        # Try to use the state itself as key if hashable; otherwise fallback
        # to object identity (which disables actual dedup across equal content).
        try:
            hash(state)  # type: ignore[arg-type]
            return state  # type: ignore[return-value]
        except Exception:
            return id(state)

    def run(
        self,
        *,
        initial_states: Iterable[StateT],
        expand: Callable[[StateT], Iterable[StateT]],
        score: Callable[[StateT], float],
        is_goal: Optional[Callable[[StateT], bool]] = None,
        max_steps: Optional[int] = None,
        return_n_best: int = 1,
    ) -> List[StateT]:
        """Execute beam search and return up to ``return_n_best`` final states.

        The search proceeds for at most ``max_steps`` steps. If ``is_goal`` is
        provided, any goal states encountered at a step are collected; if at
        least one goal is found in a step, the search stops after that step and
        the best goals from that step are returned.

        Returns a list of best states (length <= return_n_best). If the beam
        becomes empty, returns an empty list.
        """
        if return_n_best <= 0:
            raise ValueError("return_n_best must be positive")

        step_limit = max_steps if max_steps is not None else self.default_max_steps
        if step_limit is None:
            raise ValueError("max_steps must be provided either in constructor or run()")

        # Initialize beam with scored initial states.
        init_list = list(initial_states)
        if not init_list:
            return []
        beam: List[_Entry[StateT]] = [
            _Entry(state=s, score=score(s), step=0) for s in init_list
        ]

        # Keep only the top-k initial states if needed.
        beam = self._top_k(beam, self.beam_size)

        for step in range(1, step_limit + 1):
            # Expand all states in the beam.
            candidates: List[_Entry[StateT]] = []
            seen: set[Hashable] = set()

            print(f"Step {step}: min_score={beam[0].score}, max_score={beam[-1].score}")
            for entry in beam:
                for child in expand(entry.state):
                    if self.deduplicate:
                        k = self._key(child)
                        if k in seen:
                            continue
                        seen.add(k)
                    candidates.append(_Entry(state=child, score=score(child), step=step))

            if not candidates:
                # No more expansions possible.
                return []

            # If goal function is provided, filter and early stop if any found.
            goals: List[_Entry[StateT]] = []
            if is_goal is not None:
                goals = [c for c in candidates if is_goal(c.state)]
                if goals:
                    goals = self._top_k(goals, min(return_n_best, self.beam_size))
                    return [g.state for g in goals[:return_n_best]]

            # Otherwise, continue with the best candidates as the new beam.
            beam = self._top_k(candidates, self.beam_size)

        # Reached step limit; return the top results from the final beam.
        beam = self._top_k(beam, min(return_n_best, self.beam_size))
        return [e.state for e in beam[:return_n_best]]

    def _top_k(self, entries: List[_Entry[StateT]], k: int) -> List[_Entry[StateT]]:
        if not entries:
            return []
        # Stable sort by score with correct direction.
        reverse = self.maximize
        # Python sort is stable; for equal scores, earlier entries are preferred.
        return sorted(entries, key=lambda e: e.score, reverse=reverse)[:k]


if __name__ == "__main__":
    # Tiny demo: find integer closest to target using +/- 1 moves.
    target = 37
    bs = BeamSearch[int](beam_size=3, max_steps=15, maximize=False)

    def expand_int(x: int) -> Iterable[int]:
        return (x - 1, x + 1)

    def score_int(x: int) -> float:
        return abs(x - target)

    def is_goal_int(x: int) -> bool:
        return x == target

    result = bs.run(
        initial_states=[0], expand=expand_int, score=score_int, is_goal=is_goal_int
    )
    print({"best": result})

