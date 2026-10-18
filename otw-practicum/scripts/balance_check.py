"""
Balance check script (scripts/balance_check.py).

Simulates 1,000 seeded games per difficulty against Greedy and Random students,
from allowed starts (>= 2 hops from goal), for turn limits T in (5, 6, 8).
Prints win rates, checks Hard >= Medium >= Easy for Proctor win rate,
and flags win rates under 20% or over 80%.

Usage:
    python scripts/balance_check.py
"""

import os
import random
import sys
import time
import networkx as nx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.game_state import GameState, load_map, pick_ai_start, allowed_player_starts
from engine.graph_utils import build_graph
from agents.ucs_agent import UCSAgent
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent
from agents.evaluation import EvaluationFunction


class GreedyStudent:
    """Always chooses the first step along the shortest hop path to the goal."""
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
    """Chooses a uniformly random legal move."""
    def __init__(self, rng):
        self.rng = rng

    def choose_move(self, state):
        legal = state.legal_moves()
        return self.rng.choice(legal) if legal else None


def run_balance_check(map_path="maps/its_sukolilo.json", num_games=1000, turn_limits=(5, 6, 8), base_seed=42):
    map_data = load_map(map_path)
    goal = map_data["goal"]
    graph = build_graph(map_data)
    eval_func = EvaluationFunction(graph)

    candidate_starts = allowed_player_starts(map_data, min_hops=2)
    print(f"Loaded map: {map_path} (goal: {goal})")
    print(f"Allowed player starts (>= 2 hops): {candidate_starts}")
    print(f"Simulating {num_games} games per configuration across T in {turn_limits}...\n")

    difficulties = [
        ("Easy (UCS)", lambda: UCSAgent(graph)),
        ("Medium (Minimax d3)", lambda: MinimaxAgent(eval_func, depth=3)),
        ("Hard (AlphaBeta ID)", lambda: AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=1.0)),
    ]

    all_results = {}

    for t_limit in turn_limits:
        print(f"=== Simulating Turn Limit T = {t_limit} ===")
        all_results[t_limit] = {}

        for diff_name, proc_factory in difficulties:
            all_results[t_limit][diff_name] = {}

            for student_type in ["Greedy", "Random"]:
                student_wins = 0
                proctor_wins = 0

                t0 = time.time()
                for i in range(num_games):
                    seed = base_seed + i
                    rng = random.Random(seed)
                    s_start = candidate_starts[i % len(candidate_starts)]
                    p_start = pick_ai_start(map_data, s_start, seed=seed)

                    state = GameState.from_map(map_data, student=s_start, proctor=p_start, turn_limit=t_limit)
                    proctor_agent = proc_factory()

                    if student_type == "Greedy":
                        student_agent = GreedyStudent(graph, goal)
                    else:
                        student_agent = RandomStudent(random.Random(seed + 10000))

                    while not state.is_terminal():
                        if state.to_move == "student":
                            mv = student_agent.choose_move(state)
                        else:
                            mv = proctor_agent.choose_move(state)
                        if mv is None:
                            break
                        state = state.apply(mv)

                    w = state.winner()
                    if w == "student":
                        student_wins += 1
                    elif w == "proctor":
                        proctor_wins += 1

                elapsed = time.time() - t0
                s_rate = (student_wins / num_games) * 100.0
                p_rate = (proctor_wins / num_games) * 100.0

                all_results[t_limit][diff_name][student_type] = {
                    "student_wins": student_wins,
                    "proctor_wins": proctor_wins,
                    "student_rate": s_rate,
                    "proctor_rate": p_rate,
                    "elapsed": elapsed,
                }
                print(f"  T={t_limit} | {diff_name:20s} vs {student_type:6s}: "
                      f"Student Win {s_rate:5.1f}% | Proctor Win {p_rate:5.1f}% ({elapsed:.1f}s)")
        print()

    # Formatted summary report
    print("\n" + "=" * 80)
    print("BALANCE SIMULATION SUMMARY TABLE (1,000 games per cell)")
    print("=" * 80)
    header = f"{'Turn Limit':^10} | {'Student Type':^12} | {'Easy (UCS)':^18} | {'Medium (Minimax)':^18} | {'Hard (Alpha-Beta)':^18}"
    print(header)
    print("-" * 80)

    for t_limit in turn_limits:
        for student_type in ["Greedy", "Random"]:
            cols = [f"T = {t_limit}", student_type]
            for diff_name, _ in difficulties:
                data = all_results[t_limit][diff_name][student_type]
                s_pct = data["student_rate"]
                p_pct = data["proctor_rate"]
                flag = ""
                if s_pct < 20.0 or s_pct > 80.0:
                    flag = " *"
                cols.append(f"S:{s_pct:4.1f}% P:{p_pct:4.1f}%{flag}")
            print(f"{cols[0]:^10} | {cols[1]:^12} | {cols[2]:^18} | {cols[3]:^18} | {cols[4]:^18}")
        print("-" * 80)

    print("\nNote: '*' flags extreme win rates where Student win rate is < 20% or > 80%.")

    # Difficulty hierarchy check: Hard Proctor Win >= Medium Proctor Win >= Easy Proctor Win
    print("\n" + "=" * 80)
    print("DIFFICULTY HIERARCHY CHECK (Proctor Win Rate: Hard >= Medium >= Easy)")
    print("=" * 80)
    for t_limit in turn_limits:
        for student_type in ["Greedy", "Random"]:
            e_p = all_results[t_limit]["Easy (UCS)"][student_type]["proctor_rate"]
            m_p = all_results[t_limit]["Medium (Minimax d3)"][student_type]["proctor_rate"]
            h_p = all_results[t_limit]["Hard (AlphaBeta ID)"][student_type]["proctor_rate"]

            h_ge_m = h_p >= m_p
            m_ge_e = m_p >= e_p
            status = "PASS" if (h_ge_m and m_ge_e) else "NOTICE"
            print(f"T = {t_limit} vs {student_type:6s}: Easy {e_p:5.1f}% | Medium {m_p:5.1f}% | Hard {h_p:5.1f}% -> [{status}]")
            if not h_ge_m:
                print(f"   Notice: Hard ({h_p:.1f}%) < Medium ({m_p:.1f}%)")
            if not m_ge_e:
                print(f"   Notice: Medium ({m_p:.1f}%) < Easy ({e_p:.1f}%)")


if __name__ == "__main__":
    run_balance_check()
