"""
Uniform Cost Search (UCS) baseline agent using
shortest-path navigation for Campus Pursuit (BE-2).
"""

import networkx as nx

class UCSAgent:
    def __init__(self, graph: nx.Graph = None):
        self.graph = graph
        self.nodes_expanded = 0

    def choose_move(self, state):
        self.nodes_expanded = 0
        graph = self.graph if self.graph is not None else state.adj
        
        start_node = state.proctor if state.to_move == 'proctor' else state.student
        target_node = state.student if state.to_move == 'proctor' else 'informatics'
        
        try:
            path = nx.shortest_path(self.graph, source=start_node, target=target_node, weight='meters')
            if len(path) > 1:
                next_node = path[1]
                for move in state.legal_moves():
                    if move == next_node or getattr(move, 'target', None) == next_node:
                        return move
                return path[1]
        except (nx.NetworkXNoPath, IndexError):
            pass
        
        legal = state.legal_moves()
        return legal[0] if legal else None