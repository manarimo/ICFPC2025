import unittest

from beam_search import BeamSearch


class TestBeamSearch(unittest.TestCase):
    def test_reaches_goal_integer(self):
        target = 37
        bs = BeamSearch[int](beam_size=3, max_steps=50)

        def expand(x: int):
            return (x - 1, x + 1)

        def score(x: int) -> float:
            return abs(x - target)

        def is_goal(x: int) -> bool:
            return x == target

        result = bs.run(
            initial_states=[0], expand=expand, score=score, is_goal=is_goal
        )
        self.assertEqual(result[0], target)

    def test_best_after_fixed_steps(self):
        target = 5
        bs = BeamSearch[int](beam_size=100, max_steps=3)

        def expand(x: int):
            return (x - 1, x + 1)

        def score(x: int) -> float:
            return abs(x - target)

        result = bs.run(initial_states=[0], expand=expand, score=score, max_steps=3)
        # After 3 steps, reachable states are {-3,-1,1,3}; best is 3 (distance 2)
        self.assertEqual(result[0], 3)


if __name__ == "__main__":
    unittest.main()

