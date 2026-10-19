"""
Precomputed hop-based heuristic evaluation function
for game tree searches.
"""

import networkx as nx
from engine.graph_utils import build_graph, all_pairs_hop_distances


class EvaluationFunction:
    def __init__(self, graph_or_adj):
        if isinstance(graph_or_adj, nx.Graph):
            self.graph = graph_or_adj
        else:
            self.graph = build_graph(graph_or_adj)

        # Cache all-pairs shortest hop distance table
        self.distance_dict = all_pairs_hop_distances(self.graph)

    def get_distance(self, u, v) -> float:
        try:
            return self.distance_dict[u][v]
        except KeyError:
            return float('inf')

    def evaluate(self, state) -> float:
        """
        Evaluation from the Student's view:
        distance(Proctor, Student) - distance(Student, goal)
        """
        proctor_pos = state.proctor
        student_pos = state.student
        target = state.goal

        dist_proctor_student = self.get_distance(proctor_pos, student_pos)
        dist_student_target = self.get_distance(student_pos, target)

        return dist_proctor_student - dist_student_target

    # -- shared helpers for Minimax and Alpha-Beta ----------------------------
    # Both agents MUST use these so they score and break ties identically.

    def terminal_score(self, state, depth_remaining):
        """
        Score of a finished game from the Student's view, depth-dependent:
            Student win: +(WIN_SCORE + depth_remaining)
            Proctor win: -(WIN_SCORE + depth_remaining)
        `depth_remaining` is larger when the game ends sooner (closer to the
        root), so a faster catch is more negative (better for the Proctor) and
        a later loss is less bad for the loser. |eval| is always far below
        WIN_SCORE, so any win/loss outranks any heuristic value.
        """
        return state.utility("student") * (WIN_SCORE + depth_remaining)

    def tiebreak_key(self, state, move):
        """
        Secondary key used only among root moves with EQUAL scores (lower is
        better). Proctor: hop distance from the move to the Student. Student:
        hop distance from the move to the goal. Remaining ties keep the fixed
        legal_moves() order (first one wins).
        """
        target = state.student if state.to_move == "proctor" else state.goal
        return self.get_distance(move, target)


# Base magnitude for win/loss scores (see EvaluationFunction.terminal_score).
WIN_SCORE = 10000


def pick_root_move(eval_func, state, scored_moves, maximizing):
    """
    Choose the best (move, score) from `scored_moves` (in legal_moves order).
    Best score first; among equal scores the lowest tiebreak_key; then the
    earliest move. Shared by Minimax and Alpha-Beta.
    """
    best_move, best_score, best_key = None, None, None
    for move, score in scored_moves:
        key = eval_func.tiebreak_key(state, move)
        if best_move is None:
            better = True
        elif score != best_score:
            better = score > best_score if maximizing else score < best_score
        else:
            better = key < best_key
        if better:
            best_move, best_score, best_key = move, score, key
    return best_move, best_score