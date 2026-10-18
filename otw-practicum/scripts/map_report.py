"""
Map analysis and tournament balance check (scripts/map_report.py).

Usage:
    python scripts/map_report.py
"""

import math
import os
import random
import sys
import networkx as nx

# Add otw-practicum to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.game_state import GameState, load_map, pick_ai_start
from engine.graph_utils import build_graph, all_pairs_hop_distances
from agents.ucs_agent import UCSAgent
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent
from agents.evaluation import EvaluationFunction


class GreedyStudent:
    """Simulated student that always takes the shortest hop path to the goal."""
    def __init__(self, graph, goal):
        self.graph = graph
        self.goal = goal

    def choose_move(self, state):
        try:
            path = nx.shortest_path(self.graph, source=state.student, target=self.goal, weight=None)
            if len(path) > 1:
                next_node = path[1]
                if next_node in state.legal_moves():
                    return next_node
        except Exception:
            pass
        legal = state.legal_moves()
        return legal[0] if legal else None


class RandomStudent:
    """Simulated student that moves randomly among legal moves."""
    def __init__(self, rng):
        self.rng = rng

    def choose_move(self, state):
        legal = state.legal_moves()
        return self.rng.choice(legal) if legal else None


def analyze_map(map_path="maps/its_sukolilo.json"):
    map_data = load_map(map_path)
    g = build_graph(map_data)
    goal = map_data["goal"]

    node_count = len(g.nodes)
    edge_count = len(g.edges)
    avg_degree = sum(dict(g.degree()).values()) / node_count
    goal_neighbors = list(g.neighbors(goal))
    goal_neighbor_count = len(goal_neighbors)

    hop_table = all_pairs_hop_distances(g)
    hops_to_goal = {n: hop_table[n][goal] for n in g.nodes}
    longest_hop = max(hops_to_goal.values())
    suggested_turn_limit = math.ceil(1.5 * longest_hop)

    print("==================================================")
    print("           CAMPUS PURSUIT: MAP REPORT             ")
    print("==================================================")
    print(f"Map file:                  {map_path}")
    print(f"Goal node:                 {goal}")
    print(f"Node count:                {node_count}")
    print(f"Edge count:                {edge_count}")
    print(f"Average degree:            {avg_degree:.2f}")
    print(f"Goal neighbors ({goal_neighbor_count}):       {', '.join(goal_neighbors)}")
    print("\nHop distance to goal from each node:")
    for n, h in sorted(hops_to_goal.items(), key=lambda x: (x[1], x[0])):
        print(f"  - {n:16s}: {h} hop(s)")
    print(f"\nLongest hop distance:      {longest_hop}")
    print(f"Suggested turn_limit:      ceil(1.5 * {longest_hop}) = {suggested_turn_limit}")
    print("==================================================\n")

    return map_data, g, hops_to_goal, suggested_turn_limit


def simulate_game(state, student_agent, proctor_agent):
    while not state.is_terminal():
        if state.to_move == "student":
            mv = student_agent.choose_move(state)
        else:
            mv = proctor_agent.choose_move(state)
        state = state.apply(mv)
    return state.winner()


def run_balance_tournament(map_data, g, hops_to_goal, num_games=1000, seed=42):
    goal = map_data["goal"]
    eval_func = EvaluationFunction(g)

    # Agents to test
    # Difficulty: Easy = UCS, Medium = Minimax depth 3, Hard = AlphaBeta depth 5 (depth-limited for deterministic fast sim)
    turn_limits = [5, 6, 8, 10]
    all_non_goal_nodes = [n for n in g.nodes if n != goal]
    nodes_2plus_hops = [n for n in g.nodes if n != goal and hops_to_goal[n] >= 2]

    print("==================================================")
    print(f"RUNNING TOURNAMENT SIMULATION ({num_games} games per cell)")
    print("==================================================")
    print(f"All non-goal start nodes ({len(all_non_goal_nodes)}): {', '.join(all_non_goal_nodes)}")
    print(f"Restricted 2+ hops nodes ({len(nodes_2plus_hops)}): {', '.join(nodes_2plus_hops)}\n")

    # We test with Hard = AlphaBetaAgent(depth=4) and (depth=5)
    proctor_configs = [
        ("Easy (UCS)", lambda: UCSAgent(g)),
        ("Medium (Minimax d=3)", lambda: MinimaxAgent(eval_func, depth=3)),
        ("Hard (AlphaBeta d=4)", lambda: AlphaBetaAgent(eval_func, depth=4, iterative_deepening=False)),
    ]

    # Tables to collect:
    # 1. Any start (1+ hops)
    # 2. Restricted start (2+ hops)
    for start_rule_name, candidate_starts in [
        ("ALL START NODES (1+ hops from goal)", all_non_goal_nodes),
        ("RESTRICTED START NODES (2+ hops from goal)", nodes_2plus_hops)
    ]:
        print(f"--- Student Win Rates: {start_rule_name} ---")
        header = f"{'Turn Limit':<12} | {'Student Type':<15} | " + " | ".join([f"{name:<20}" for name, _ in proctor_configs])
        print(header)
        print("-" * len(header))

        for t_limit in turn_limits:
            for student_type in ["Greedy", "Random"]:
                row_str = f"T={t_limit:<10} | {student_type:<15} | "
                for proc_name, proc_factory in proctor_configs:
                    proctor = proc_factory()
                    student_wins = 0
                    rng = random.Random(seed + t_limit * 10000)

                    if student_type == "Greedy":
                        student = GreedyStudent(g, goal)
                    else:
                        student = RandomStudent(random.Random(seed + 777))

                    for i in range(num_games):
                        s_start = rng.choice(candidate_starts)
                        # AI start: any node except s_start and goal
                        p_candidates = [n for n in g.nodes if n != s_start and n != goal]
                        p_start = rng.choice(p_candidates)

                        init_state = GameState.from_map(map_data, s_start, p_start, turn_limit=t_limit)
                        winner = simulate_game(init_state, student, proctor)
                        if winner == "student":
                            student_wins += 1

                    win_rate = (student_wins / num_games) * 100.0
                    flag = " (!)" if (win_rate < 20.0 or win_rate > 80.0) else "    "
                    row_str += f"{win_rate:6.1f}%{flag}          | "
                print(row_str)
            print()


if __name__ == "__main__":
    map_data, g, hops_to_goal, suggested_limit = analyze_map()
    run_balance_tournament(map_data, g, hops_to_goal, num_games=1000, seed=42)
