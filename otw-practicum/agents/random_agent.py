"""
Random agent (owned by BE-1).

Picks a uniformly random legal move (including waiting). Works for either
side, since it just uses whatever side is to move in the state. Used as a
baseline and for engine sanity checks.
"""

import random


class RandomAgent:
    def __init__(self, seed=None):
        # Own generator so results are reproducible and global random is untouched.
        self.rng = random.Random(seed)

    def choose_move(self, state):
        """Return a random node id from state.legal_moves()."""
        moves = state.legal_moves()
        if not moves:
            raise ValueError("No legal moves: the game is already over")
        return self.rng.choice(moves)
