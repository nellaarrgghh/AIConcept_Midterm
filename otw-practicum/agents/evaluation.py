"""
Precomputed Dijkstra-based heuristic evaluation function
for game tree searches (BE-2).
"""

import networkx as nx

class EvaluationFunction:
    def __init__(self, graph_or_adj):
        if isinstance(graph_or_adj, dict):
            self.graph = nx.Graph(graph_or_adj)
        else:
            self.graph = graph_or_adj
            
        self.distance_dict = dict(nx.all_pairs_dijkstra_path_length(self.graph, weight='meters'))

    def get_distance(self, u, v) -> float:
        try:
            return self.distance_dict[u][v]
        except KeyError:
            return float('inf')

    def evaluate(self, state) -> float:
        """
        Evaluation from the Student's view:
        distance(Proctor, Student) - distance(Student, 'informatics')
        """
        proctor_pos = state.proctor
        student_pos = state.student
        target = state.goal
        
        dist_proctor_student = self.get_distance(proctor_pos, student_pos)
        dist_student_target = self.get_distance(student_pos, target)
        
        return dist_proctor_student - dist_student_target