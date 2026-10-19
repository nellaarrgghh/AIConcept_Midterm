"""
Tests for engine/graph_utils.py (Nel).
Run from otw-practicum/: python -m pytest tests/test_graph_utils.py
"""

import os
import networkx as nx
import pytest

from engine.game_state import load_map, GameState
from engine.graph_utils import (
    build_graph, hop_distance, meter_distance,
    all_pairs_hop_distances, all_pairs_meter_distances
)

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "maps", "its_sukolilo.json")


@pytest.fixture
def map_data():
    return load_map(MAP_PATH)


def test_build_graph_from_map(map_data):
    g = build_graph(map_data)
    assert len(g.nodes) == len(map_data["nodes"])
    assert len(g.edges) == len(map_data["edges"])
    for u, v, data in g.edges(data=True):
        assert "weight" in data
        assert "cost" in data
        assert "meters" in data
        assert data["weight"] == data["cost"] == data["meters"]


def test_meter_distance_equals_sum_of_edge_costs(map_data):
    g = build_graph(map_data)
    # Known path: main_gate -> graha (550) -> d3_pens (280) = 830 meters
    dist = meter_distance(g, "main_gate", "d3_pens")
    assert dist == 550 + 280

    # Shortest path from main_gate to informatics
    # main_gate -> manarul_ilmi (450) -> library (350) -> informatics (350) = 1150 meters
    dist_informatics = meter_distance(g, "main_gate", "informatics")
    path = nx.shortest_path(g, "main_gate", "informatics", weight="weight")
    expected_sum = sum(g[path[i]][path[i+1]]["weight"] for i in range(len(path) - 1))
    assert dist_informatics == expected_sum
    assert dist_informatics == 1150


def test_hop_distance_equals_number_of_edges(map_data):
    g = build_graph(map_data)
    # main_gate to graha is 1 edge (1 hop)
    assert hop_distance(g, "main_gate", "graha") == 1
    # main_gate to d3_pens via graha is 2 edges (2 hops)
    assert hop_distance(g, "main_gate", "d3_pens") == 2
    # main_gate to informatics via graha -> d3_pens -> informatics is 3 hops
    assert hop_distance(g, "main_gate", "informatics") == 3


def test_all_pairs_cached_tables(map_data):
    g = build_graph(map_data)
    hops = all_pairs_hop_distances(g)
    meters = all_pairs_meter_distances(g)
    assert hops["main_gate"]["informatics"] == 3
    assert meters["main_gate"]["d3_pens"] == 830
