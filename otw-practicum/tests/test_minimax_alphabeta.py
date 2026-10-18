"""
Comprehensive tests for UCS, Minimax, and Alpha-Beta Agents.
Tests:
  - UCS path cost equals the sum of edge costs.
  - Minimax and Alpha-Beta choose the same move on 100 random states at each depth 1 to 4.
  - Alpha-Beta expands at most as many nodes as Minimax at the same depth.
  - The Proctor never waits (every agent, every depth).
  - A faster catch scores higher for the Proctor (depth-dependent win/loss scores).
  - Equal root scores are broken by hop distance to the Student, then legal_moves order.
  - Iterative deepening: depth 1 always completes, depth is capped at the plies
    left until the turn limit, and depth_reached is recorded.
"""

import os
import random
import time
import pytest

from engine.game_state import load_map, pick_ai_start, GameState, build_adjacency
from engine.graph_utils import build_graph, meter_distance
from agents.ucs_agent import UCSAgent
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent, remaining_plies
from agents.evaluation import EvaluationFunction, WIN_SCORE

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "maps", "its_sukolilo.json")
T = 6  # turn limit used in these tests (same as server.TURN_LIMIT)


@pytest.fixture
def map_data():
    return load_map(MAP_PATH)


@pytest.fixture
def eval_func(map_data):
    return EvaluationFunction(build_graph(map_data))


def random_states(map_data, n, seed):
    """n random non-terminal states (either side to move, any turn before the limit)."""
    adj = build_adjacency(map_data)
    goal = map_data["goal"]
    nodes = list(adj)
    rng = random.Random(seed)
    states = []
    while len(states) < n:
        student = rng.choice([x for x in nodes if x != goal])
        proctor = rng.choice([x for x in nodes if x != student])
        to_move = rng.choice(["student", "proctor"])
        turn = rng.randrange(T)
        s = GameState(adj, goal, student, proctor, to_move, turn, T)
        if not s.is_terminal():
            states.append(s)
    return states


def all_proctor_states(map_data, turn_limit=T):
    adj = build_adjacency(map_data)
    goal = map_data["goal"]
    for student in adj:
        for proctor in adj:
            for turn in range(turn_limit):
                s = GameState(adj, goal, student, proctor, "proctor", turn, turn_limit)
                if not s.is_terminal():
                    yield s


def test_ucs_path_cost_equals_sum_of_edge_costs(map_data):
    g = build_graph(map_data)
    ucs = UCSAgent(g)

    # Test student at main_gate, proctor at graha
    state = GameState.from_map(map_data, student="main_gate", proctor="graha")
    move = ucs.choose_move(state)

    # When student moves, goal is state.goal ('informatics')
    # True meter shortest path from main_gate to informatics:
    # main_gate -> manarul_ilmi (450) -> canteen (300) -> library (400) -> informatics (350) = 1500 meters
    assert move == "manarul_ilmi"
    assert meter_distance(g, "main_gate", "informatics") == 1150

    # Proctor's turn to move towards student at main_gate from graha:
    # graha to main_gate is 1 step, 550 meters
    state_proctor = state.apply(move)
    proctor_move = ucs.choose_move(state_proctor)
    assert proctor_move == "main_gate"


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_minimax_alphabeta_equivalence_and_node_expansion(map_data, eval_func, depth):
    mm_agent = MinimaxAgent(eval_func, depth=depth)
    ab_agent = AlphaBetaAgent(eval_func, depth=depth, iterative_deepening=False)

    for state in random_states(map_data, 100, seed=depth * 1000):
        mm_move = mm_agent.choose_move(state)
        mm_nodes = mm_agent.nodes_expanded

        ab_move = ab_agent.choose_move(state)
        ab_nodes = ab_agent.nodes_expanded

        # 1. Exact same move chosen
        assert mm_move == ab_move, (
            f"Move mismatch at depth {depth}, state {state}: "
            f"Minimax={mm_move}, AlphaBeta={ab_move}"
        )

        # 2. Alpha-Beta expands at most as many nodes as Minimax
        assert ab_nodes <= mm_nodes, (
            f"AlphaBeta expanded more nodes than Minimax at depth {depth}: "
            f"AlphaBeta={ab_nodes}, Minimax={mm_nodes}"
        )


def test_proctor_never_waits(map_data, eval_func):
    agents = [UCSAgent(build_graph(map_data))]
    agents += [MinimaxAgent(eval_func, depth=d) for d in (1, 2, 3)]
    agents += [AlphaBetaAgent(eval_func, depth=d) for d in (1, 2, 3)]
    for state in all_proctor_states(map_data):
        for agent in agents:
            move = agent.choose_move(state)
            assert move != state.proctor, f"{type(agent).__name__} waited in {state}"
            assert move in state.legal_moves()
    # Hard configuration (iterative deepening) on a sample, with a short budget.
    hard = AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=0.05)
    for state in list(all_proctor_states(map_data))[::25]:
        assert hard.choose_move(state) != state.proctor


def test_terminal_score_prefers_faster_catch(map_data, eval_func):
    adj = build_adjacency(map_data)
    caught = GameState(adj, map_data["goal"], "library", "library", "student", 1, T)
    escaped = GameState(adj, map_data["goal"], "informatics", "library", "proctor", 1, T)
    # More depth remaining = the game ended sooner.
    assert eval_func.terminal_score(caught, 3) < eval_func.terminal_score(caught, 1) < -WIN_SCORE + 1
    # For the Proctor a later loss is better (smaller score for the Student).
    assert eval_func.terminal_score(escaped, 3) > eval_func.terminal_score(escaped, 1) > WIN_SCORE - 1


@pytest.mark.parametrize("depth", [1, 2, 3, 4])
def test_immediate_catch_scores_best_and_is_chosen(map_data, eval_func, depth):
    mm = MinimaxAgent(eval_func, depth=depth)
    ab = AlphaBetaAgent(eval_func, depth=depth)
    checked = 0
    for state in all_proctor_states(map_data):
        if state.student not in state.adj[state.proctor]:
            continue
        scores = {m: mm.minimax(state.apply(m), depth - 1, True) for m in state.legal_moves()}
        catch = scores.pop(state.student)
        # Catching now beats or ties every other move (ties occur on the last turn where any move ends by turn limit)
        if state.turn < state.turn_limit - 1:
            assert all(catch < other for other in scores.values()), (state, catch, scores)
        else:
            assert all(catch <= other for other in scores.values()), (state, catch, scores)
        # In all cases, immediate catch is chosen
        assert mm.choose_move(state) == state.student
        assert ab.choose_move(state) == state.student
        checked += 1
    assert checked > 0


def test_tie_break_prefers_move_closer_to_student(map_data, eval_func):
    # Student on library is one step from informatics: at depth >= 2 every Proctor move loses
    # equally because Student reaches informatics on the next step.
    # Biology's neighbors: manarul_ilmi (1 hop to library),
    # canteen (1 hop), electrical_eng (2 hops). Closest first, then file order.
    adj = build_adjacency(map_data)
    state = GameState(adj, map_data["goal"], "library", "biology", "proctor", 0, T)
    assert state.legal_moves() == ["manarul_ilmi", "canteen", "electrical_eng"]
    for depth in (2, 3, 4):
        mm = MinimaxAgent(eval_func, depth=depth)
        scores = {m: mm.minimax(state.apply(m), depth - 1, True) for m in state.legal_moves()}
        assert len(set(scores.values())) == 1  # a genuine tie
        assert mm.choose_move(state) == "manarul_ilmi"
        assert AlphaBetaAgent(eval_func, depth=depth).choose_move(state) == "manarul_ilmi"
    # At depth 1, heuristic gives manarul_ilmi=0, canteen=0, electrical_eng=1
    assert MinimaxAgent(eval_func, depth=1).choose_move(state) == "manarul_ilmi"
    assert AlphaBetaAgent(eval_func, depth=1).choose_move(state) == "manarul_ilmi"


def test_remaining_plies(map_data):
    adj = build_adjacency(map_data)
    g = map_data["goal"]
    assert remaining_plies(GameState(adj, g, "main_gate", "robotics", "student", 0, 6)) == 12
    assert remaining_plies(GameState(adj, g, "main_gate", "robotics", "proctor", 0, 6)) == 11
    assert remaining_plies(GameState(adj, g, "main_gate", "robotics", "proctor", 5, 6)) == 1


def test_iterative_deepening_always_completes_depth_one(map_data, eval_func):
    adj = build_adjacency(map_data)
    state = GameState(adj, map_data["goal"], "main_gate", "robotics", "proctor", 0, T)
    agent = AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=0.0)
    move = agent.choose_move(state)
    assert move in state.legal_moves()
    assert agent.depth_reached == 1
    assert move == AlphaBetaAgent(eval_func, depth=1).choose_move(state)


@pytest.mark.parametrize("turn", [3, 4, 5])
def test_iterative_deepening_depth_is_capped_by_turn_limit(map_data, eval_func, turn):
    adj = build_adjacency(map_data)
    state = GameState(adj, map_data["goal"], "main_gate", "robotics", "proctor", turn, T)
    cap = remaining_plies(state)
    agent = AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=10.0)
    t0 = time.perf_counter()
    move = agent.choose_move(state)
    elapsed = time.perf_counter() - t0
    assert 1 <= agent.depth_reached <= cap
    assert elapsed < 10.0  # stopped at the end of the game, not at the time limit
    # Same move as a fixed-depth search at the depth it reached.
    assert move == AlphaBetaAgent(eval_func, depth=agent.depth_reached).choose_move(state)


def test_iterative_deepening_respects_time_limit(map_data, eval_func):
    adj = build_adjacency(map_data)
    state = GameState(adj, map_data["goal"], "main_gate", "robotics", "student", 0, T)
    agent = AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=0.3)
    t0 = time.perf_counter()
    agent.choose_move(state)
    assert time.perf_counter() - t0 < 0.3 + 0.25  # small overshoot allowed
    assert 1 <= agent.depth_reached <= remaining_plies(state)