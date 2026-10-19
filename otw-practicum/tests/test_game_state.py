"""
Tests for engine/game_state.py (Nel).
Run from otw-practicum/:  python -m pytest
"""

import os

import pytest

from engine.game_state import (
    DEFAULT_MIN_START_HOPS, GameState, allowed_player_starts, build_adjacency,
    default_turn_limit, hop_distances, load_map, pick_ai_start, shortest_distances,
)

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "maps", "test_map.json")


@pytest.fixture
def map_data():
    return load_map(MAP_PATH)


def new_game(map_data, student, proctor, **kwargs):
    return GameState.from_map(map_data, student, proctor, **kwargs)


# --- legal moves ------------------------------------------------------------

def test_legal_moves_student_may_wait_proctor_may_not(map_data):
    s = new_game(map_data, "gate_main", "tower")
    assert s.legal_moves() == ["gate_main", "library", "rectorate"]  # Student: wait first, then neighbors

    s = s.apply("library")  # now it is the Proctor's turn
    assert s.to_move == "proctor"
    assert s.legal_moves() == ["rectorate", "informatics"]  # Proctor: neighbors only, no waiting
    with pytest.raises(ValueError):
        s.apply("tower")  # waiting is illegal for the Proctor


def test_proctor_never_has_wait_move_on_any_state(map_data):
    adj = build_adjacency(map_data)
    goal = map_data["goal"]
    for student in adj:
        for proctor in adj:
            for turn in range(5):
                s = GameState(adj, goal, student, proctor, "proctor", turn, 5)
                if s.is_terminal():
                    continue
                assert proctor not in s.legal_moves()


def test_proctor_without_neighbors_does_not_crash():
    # Isolated Proctor node: it may stay put so the game can go on.
    adj = {"a": {"g": 1}, "g": {"a": 1}, "island": {}}
    s = GameState(adj, "g", "a", "island", "proctor", 0, 3)
    assert s.legal_moves() == ["island"]
    s2 = s.apply("island")
    assert (s2.proctor, s2.to_move, s2.turn) == ("island", "student", 1)


def test_illegal_move_is_rejected(map_data):
    s = new_game(map_data, "gate_main", "tower")
    with pytest.raises(ValueError):
        s.apply("informatics")  # not adjacent to gate_main


# --- apply / copy -----------------------------------------------------------

def test_apply_does_not_mutate_old_state(map_data):
    s0 = new_game(map_data, "gate_main", "tower")
    before = (s0.turn, s0.student, s0.proctor, s0.to_move, s0.turn_limit)

    s1 = s0.apply("library")
    s2 = s1.apply("rectorate")

    assert (s0.turn, s0.student, s0.proctor, s0.to_move, s0.turn_limit) == before
    assert (s1.student, s1.proctor, s1.to_move, s1.turn) == ("library", "tower", "proctor", 0)
    assert (s2.student, s2.proctor, s2.to_move, s2.turn) == ("library", "rectorate", "student", 1)
    assert s1.adj is s0.adj  # adjacency dict is shared, not copied


def test_copy_is_independent_but_shares_adjacency(map_data):
    s0 = new_game(map_data, "gate_main", "tower")
    c = s0.copy()
    c.student = "library"
    assert s0.student == "gate_main"
    assert c.adj is s0.adj


# --- winners ----------------------------------------------------------------

def test_student_wins_on_reaching_goal(map_data):
    s = new_game(map_data, "canteen", "gate_main").apply("informatics")
    assert s.winner() == "student"
    assert s.is_terminal()
    assert s.utility("student") == 1
    assert s.utility("proctor") == -1
    assert s.legal_moves() == []


def test_proctor_wins_by_landing_on_student(map_data):
    s = new_game(map_data, "gate_main", "library")
    s = s.apply("gate_main")  # Student waits
    assert s.winner() is None
    s = s.apply("gate_main")  # Proctor lands on the Student
    assert s.winner() == "proctor"
    assert s.utility("proctor") == 1
    assert s.utility("student") == -1


def test_proctor_wins_when_student_walks_into_proctor(map_data):
    s = new_game(map_data, "gate_main", "library").apply("library")
    assert s.winner() == "proctor"


def test_proctor_wins_at_turn_limit(map_data):
    s = new_game(map_data, "gate_main", "tower", turn_limit=2)
    # Student waits; the Proctor (which cannot wait) shuttles tower <-> informatics.
    for proctor_move in ("informatics", "tower"):
        assert s.winner() is None
        assert s.utility("student") == 0
        s = s.apply(s.student)
        s = s.apply(proctor_move)
    assert s.turn == 2
    assert s.winner() == "proctor"
    assert s.is_terminal()


def test_student_reaching_goal_on_last_round_still_wins(map_data):
    adj = build_adjacency(map_data)
    s = GameState(adj, "informatics", "canteen", "gate_main", turn=4, turn_limit=5)
    assert s.winner() is None
    assert s.apply("informatics").winner() == "student"


def test_default_turn_limit_uses_hops(map_data):
    # Longest shortest path on the test map is 3 hops -> ceil(1.5 * 3) = 5.
    adj = build_adjacency(map_data)
    assert default_turn_limit(adj) == 5
    assert new_game(map_data, "gate_main", "tower").turn_limit == 5


# --- player start rule ----------------------------------------------------------

def test_allowed_player_starts_respect_min_hops(map_data):
    # Hop distance to informatics on the test map:
    # canteen 1, tower 1 (too close); library 2, rectorate 2, gate_main 3 (allowed).
    assert DEFAULT_MIN_START_HOPS == 2
    assert hop_distances(build_adjacency(map_data), "informatics") == {
        "informatics": 0, "canteen": 1, "tower": 1,
        "library": 2, "rectorate": 2, "gate_main": 3}
    assert allowed_player_starts(map_data, 2) == ["gate_main", "library", "rectorate"]
    assert allowed_player_starts(map_data, 3) == ["gate_main"]
    assert "informatics" not in allowed_player_starts(map_data, 0)  # never the goal
    # Meter distances are still available for UCS-style checks.
    dist = shortest_distances(build_adjacency(map_data), "informatics")
    assert dist == {"informatics": 0, "canteen": 130, "tower": 140,
                    "rectorate": 270, "library": 280, "gate_main": 400}


@pytest.mark.parametrize("bad_start", ["informatics", "canteen", "tower", "not_a_node"])
def test_player_cannot_start_on_or_near_goal(map_data, bad_start):
    with pytest.raises(ValueError):
        pick_ai_start(map_data, bad_start, 0, min_hops=2)


# --- AI start -----------------------------------------------------------------

def test_ai_start_never_player_node_or_goal(map_data):
    goal = map_data["goal"]
    for player_start in allowed_player_starts(map_data):
        for seed in range(200):
            ai = pick_ai_start(map_data, player_start, seed)
            assert ai != player_start
            assert ai != goal


def test_ai_start_is_reproducible_with_seed(map_data):
    a = [pick_ai_start(map_data, "gate_main", seed) for seed in range(20)]
    b = [pick_ai_start(map_data, "gate_main", seed) for seed in range(20)]
    assert a == b
    assert len(set(a)) > 1  # different seeds do give different starts
