"""
Minimax decision-making agent utilizing fixed-depth search
for Campus Pursuit (BE-2).
"""

from agents.evaluation import EvaluationFunction

class MinimaxAgent:
    def __init__(self, eval_func=None, depth=3):
        self.eval_func = eval_func
        self.depth = depth
        self.nodes_expanded = 0

    def choose_move(self, state):
        self.nodes_expanded = 0
        
        if self.eval_func is None:
            self.eval_func = EvaluationFunction(state.adj)
        
        best_move = None
        is_maximizing = (state.to_move == 'student')
        
        if is_maximizing:
            best_score = float('-inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                score = self.minimax(next_state, self.depth - 1, False)
                if score > best_score:
                    best_score = score
                    best_move = move
        else:
            best_score = float('inf')
            for move in state.legal_moves():
                next_state = state.apply(move)
                score = self.minimax(next_state, self.depth - 1, True)
                if score < best_score:
                    best_score = score
                    best_move = move
                    
        return best_move

    def minimax(self, state, depth, maximizing_player):
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