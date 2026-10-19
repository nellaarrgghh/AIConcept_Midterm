"""
Alpha-Beta pruning decision agent with optional
iterative deepening.

Scoring and root tie-breaking are shared with MinimaxAgent (see
agents/evaluation.py), so at the same fixed depth both agents choose the same
move; Alpha-Beta only expands fewer nodes.

Iterative deepening (used by the Hard level):
  * depth 1 is always searched to completion, whatever the time limit;
  * deeper iterations run while time is left (time_limit seconds per move);
    an iteration that runs out of time is discarded;
  * the depth is capped at the number of plies left until the turn limit,
    and deepening stops early once a search reaches the end of the game on
    every branch (deeper searches could not change anything);
  * depth_reached is the deepest fully completed iteration.
"""

import time
from agents.evaluation import EvaluationFunction, pick_root_move


class _SearchTimeout(Exception):
    """Raised inside the search when an iterative-deepening iteration runs out of time."""


def remaining_plies(state):
    """Plies (single moves) left before the turn limit ends the game."""
    plies = 2 * (state.turn_limit - state.turn)
    if state.to_move == 'proctor':
        plies -= 1  # the Student has already moved this round
    return max(0, plies)


class AlphaBetaAgent:
    def __init__(self, eval_func=None, depth=3, iterative_deepening=False, time_limit=1.0):
        self.eval_func = eval_func
        self.depth = depth
        self.iterative_deepening = iterative_deepening
        self.time_limit = time_limit
        self.nodes_expanded = 0
        self.depth_reached = depth
        self._deadline = None
        self._cutoff_hit = False

    def choose_move(self, state):
        self.nodes_expanded = 0
        self._deadline = None

        if self.eval_func is None:
            self.eval_func = EvaluationFunction(state.adj)

        if self.iterative_deepening:
            return self._iterative_deepening_search(state)
        else:
            self.depth_reached = self.depth
            return self._alpha_beta_root(state, self.depth)

    def _alpha_beta_root(self, state, depth):
        """
        Score every root move, then pick with the shared tie-break.
        After the first move, each child is searched with a window that sits
        just below (max) / above (min) the best score so far. Scores are
        integers, so a child that ties the best score still gets its exact
        value, while clearly worse children can be pruned. This keeps the
        chosen move identical to Minimax.
        """
        is_maximizing = (state.to_move == 'student')
        scored = []
        best = None
        for move in state.legal_moves():
            next_state = state.apply(move)
            if best is None:
                alpha, beta = float('-inf'), float('inf')
            elif is_maximizing:
                alpha, beta = best - 0.5, float('inf')
            else:
                alpha, beta = float('-inf'), best + 0.5
            score = self.alphabeta(next_state, depth - 1, alpha, beta, not is_maximizing)
            scored.append((move, score))
            if best is None or (score > best if is_maximizing else score < best):
                best = score

        best_move, _ = pick_root_move(self.eval_func, state, scored, is_maximizing)
        return best_move

    def _iterative_deepening_search(self, state):
        start_time = time.perf_counter()
        max_depth = max(1, remaining_plies(state))

        # Depth 1 always completes (no deadline).
        self._cutoff_hit = False
        best_move = self._alpha_beta_root(state, 1)
        self.depth_reached = 1

        current_depth = 2
        while self._cutoff_hit and current_depth <= max_depth:
            if time.perf_counter() - start_time >= self.time_limit:
                break
            self._deadline = start_time + self.time_limit
            self._cutoff_hit = False
            try:
                move = self._alpha_beta_root(state, current_depth)
            except _SearchTimeout:
                break  # discard the unfinished iteration
            if move is not None:
                best_move = move
                self.depth_reached = current_depth
            current_depth += 1

        self._deadline = None
        return best_move

    def alphabeta(self, state, depth, alpha, beta, maximizing_player):
        self.nodes_expanded += 1
        if (self._deadline is not None and (self.nodes_expanded & 255) == 0
                and time.perf_counter() > self._deadline):
            raise _SearchTimeout()

        if state.is_terminal():
            return self.eval_func.terminal_score(state, depth)
        if depth <= 0:
            self._cutoff_hit = True  # a deeper search could still see more
            return self.eval_func.evaluate(state)

        if maximizing_player:
            max_eval = float('-inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                eval_val = self.alphabeta(next_state, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval_val)
                alpha = max(alpha, max_eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float('inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                eval_val = self.alphabeta(next_state, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval_val)
                beta = min(beta, min_eval)
                if beta <= alpha:
                    break
            return min_eval