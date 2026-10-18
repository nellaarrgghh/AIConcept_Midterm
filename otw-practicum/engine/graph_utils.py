"""
Graph utilities for Campus Pursuit (engine/graph_utils.py).

Provides:
  - build_graph(map_or_state): returns a NetworkX Graph with explicit 'cost', 'weight', and 'meters' attributes.
  - hop_distance(graph, a, b): BFS hop distance between node a and node b.
  - meter_distance(graph, a, b): shortest path distance in meters (using Dijkstra).
  - all_pairs_hop_distances(graph): cached dictionary of all-pairs hop distances {u: {v: hops}}.
  - all_pairs_meter_distances(graph): cached dictionary of all-pairs walking distances in meters {u: {v: meters}}.
"""

import math
import networkx as nx


def build_graph(map_or_state):
    """
    Build a networkx.Graph from a map dict, a GameState, or an adjacency dict.
    Ensures every edge has explicit 'weight', 'cost', and 'meters' set to edge cost.
    """
    g = nx.Graph()

    if hasattr(map_or_state, "adj"):  # GameState instance
        adj = map_or_state.adj
        for u, neighbors in adj.items():
            g.add_node(u)
            for v, cost in neighbors.items():
                g.add_edge(u, v, weight=cost, cost=cost, meters=cost)
        return g

    if isinstance(map_or_state, dict) and "edges" in map_or_state and "nodes" in map_or_state:
        for node in map_or_state["nodes"]:
            g.add_node(node["id"])
        for edge in map_or_state["edges"]:
            c = edge["cost"]
            g.add_edge(edge["from"], edge["to"], weight=c, cost=c, meters=c)
        return g

    if isinstance(map_or_state, dict):  # adjacency dict: {u: {v: cost}}
        for u, neighbors in map_or_state.items():
            g.add_node(u)
            for v, cost in neighbors.items():
                g.add_edge(u, v, weight=cost, cost=cost, meters=cost)
        return g

    raise TypeError("Expected map dict, GameState, or adjacency dict, got %r" % type(map_or_state))


def hop_distance(graph, a, b):
    """Shortest distance in number of edges (hops) between node a and node b."""
    try:
        return nx.shortest_path_length(graph, source=a, target=b, weight=None)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


def meter_distance(graph, a, b):
    """Shortest walking distance in meters between node a and node b."""
    try:
        return nx.shortest_path_length(graph, source=a, target=b, weight="weight")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


def all_pairs_hop_distances(graph):
    """Compute and return all-pairs shortest hop distance dict: {u: {v: hops}}."""
    return dict(nx.all_pairs_shortest_path_length(graph))


def all_pairs_meter_distances(graph):
    """Compute and return all-pairs shortest meter distance dict: {u: {v: meters}}."""
    return dict(nx.all_pairs_dijkstra_path_length(graph, weight="weight"))
