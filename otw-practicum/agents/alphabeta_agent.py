"""
Alpha-Beta pruning decision agent with optional
iterative deepening for Campus Pursuit (BE-2).
"""

import time
from agents.evaluation import EvaluationFunction

class AlphaBetaAgent:
    def __init__(self, eval_func=None, depth=3, iterative_deepening=False, time_limit=1.0):
        self.eval_func = eval_func
        self.depth = depth
        self.iterative_deepening = iterative_deepening
        self.time_limit = time_limit
        self.nodes_expanded = 0

    def choose_move(self, state):
        self.nodes_expanded = 0
        
        if self.eval_func is None:
            self.eval_func = EvaluationFunction(state.adj)
        
        if self.iterative_deepening:
            return self._iterative_deepening_search(state)
        else:
            return self._alpha_beta_root(state, self.depth)

    def _alpha_beta_root(self, state, depth):
        best_move = None
        is_maximizing = (state.to_move == 'student')
        alpha = float('-inf')
        beta = float('inf')
        
        if is_maximizing:
            best_score = float('-inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                score = self.alphabeta(next_state, depth - 1, alpha, beta, False)
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, best_score)
        else:
            best_score = float('inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                score = self.alphabeta(next_state, depth - 1, alpha, beta, True)
                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, best_score)
                
        return best_move

    def _iterative_deepening_search(self, state):
        start_time = time.time()
        best_move = None
        current_depth = 1
        
        while True:
            if time.time() - start_time >= self.time_limit:
                break
            try:
                move = self._alpha_beta_root(state, current_depth)
                if move is not None:
                    best_move = move
                current_depth += 1
            except Exception:
                break
        return best_move

    def alphabeta(self, state, depth, alpha, beta, maximizing_player):
        self.nodes_expanded += 1
        
        if state.is_terminal() or depth == 0:
            if state.winner() is not None:
                if hasattr(state, 'utility'):
                    return state.utility('student')
                return 10000 if state.winner() == 'student' else -10000
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