"""
Minimax decision-making agent utilizing fixed-depth search
for Campus Pursuit (BE-2).

Scoring and root tie-breaking are shared with AlphaBetaAgent (see
agents/evaluation.py) so both agents choose identical moves at equal depth:
  * terminal states: depth-dependent win/loss score (faster catch is better
    for the Proctor, later loss is better for the loser);
  * depth cut-off: EvaluationFunction.evaluate (hop distances);
  * equal root scores: prefer the move closest (in hops) to the Student
    (Proctor) or the goal (Student), then the fixed legal_moves() order.
"""

from agents.evaluation import EvaluationFunction, pick_root_move

class MinimaxAgent:
    def __init__(self, eval_func=None, depth=3):
        self.eval_func = eval_func
        self.depth = depth
        self.nodes_expanded = 0

    def choose_move(self, state):
        self.nodes_expanded = 0

        if self.eval_func is None:
            self.eval_func = EvaluationFunction(state.adj)

        is_maximizing = (state.to_move == 'student')
        scored = []
        for move in state.legal_moves():
            next_state = state.apply(move)
            scored.append((move, self.minimax(next_state, self.depth - 1, not is_maximizing)))

        best_move, _ = pick_root_move(self.eval_func, state, scored, is_maximizing)
        return best_move

    def minimax(self, state, depth, maximizing_player):
        self.nodes_expanded += 1

        if state.is_terminal():
            return self.eval_func.terminal_score(state, depth)
        if depth <= 0:
            return self.eval_func.evaluate(state)

        if maximizing_player:
            max_eval = float('-inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                eval_val = self.minimax(next_state, depth - 1, False)
                max_eval = max(max_eval, eval_val)
            return max_eval
        else:
            min_eval = float('inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                eval_val = self.minimax(next_state, depth - 1, True)
                min_eval = min(min_eval, eval_val)
            return min_eval