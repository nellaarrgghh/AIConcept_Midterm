"""
Tournament runner and pruning study experiments (experiments/tournament.py).

Usage:
    python experiments/tournament.py
"""

import csv
import os
import random
import sys
import time
import networkx as nx

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.game_state import GameState, load_map, pick_ai_start, allowed_player_starts
from engine.graph_utils import build_graph
from agents.ucs_agent import UCSAgent
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent
from agents.evaluation import EvaluationFunction
# Game constants live in server.py (single source of truth).
from server import TURN_LIMIT, MIN_START_HOPS


class SimulatedStudentGreedy:
    """Greedy student: shortest hop path to the goal."""
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


class SimulatedStudentRandom:
    """Random student: selects uniform random legal move."""
    def __init__(self, rng=None):
        self.rng = rng or random.Random(42)

    def choose_move(self, state):
        legal = state.legal_moves()
        return self.rng.choice(legal) if legal else None


def run_tournament(map_file_path="maps/its_sukolilo.json", num_games=100, turn_limit=TURN_LIMIT, seed=42):
    os.makedirs("logs", exist_ok=True)
    csv_path = "logs/tournament_results.csv"

    map_data = load_map(map_file_path)
    goal = map_data["goal"]
    graph = build_graph(map_data)
    eval_func = EvaluationFunction(graph)

    # Eligible start nodes for the player: same rule as the server (>= MIN_START_HOPS from the goal)
    candidate_starts = allowed_player_starts(map_data, MIN_START_HOPS)

    proctors = {
        "UCS": lambda: UCSAgent(graph),
        "Minimax_Depth3": lambda: MinimaxAgent(eval_func, depth=3),
        "AlphaBeta": lambda: AlphaBetaAgent(eval_func, iterative_deepening=True, time_limit=1.0),
    }

    students = {
        "Greedy": lambda: SimulatedStudentGreedy(graph, goal),
        "Random": lambda rng: SimulatedStudentRandom(rng),
    }

    fieldnames = [
        "agent", "student_type", "starts", "winner", "turns",
        "nodes_expanded", "time_per_move", "depth_reached"
    ]

    print(f"Starting tournament: {num_games} games per pairing (Turn Limit T={turn_limit})...")
    with open(csv_path, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for agent_name, proc_factory in proctors.items():
            for student_name, student_factory in students.items():
                print(f"  -> Simulating {agent_name} vs {student_name}...")
                for game_id in range(num_games):
                    current_seed = seed + game_id
                    rng = random.Random(current_seed)

                    student_start = rng.choice(candidate_starts)
                    proctor_start = pick_ai_start(map_data, student_start, seed=current_seed)

                    state = GameState.from_map(map_data, student=student_start, proctor=proctor_start, turn_limit=turn_limit)
                    starts_str = f"Student:{student_start}|Proctor:{proctor_start}"

                    proctor_agent = proc_factory()
                    if student_name == "Random":
                        student_agent = student_factory(random.Random(current_seed + 100))
                    else:
                        student_agent = student_factory()

                    turns = 0
                    total_nodes = 0
                    total_time = 0.0
                    proctor_moves = 0
                    last_depth_reached = getattr(proctor_agent, "depth", 1)

                    while not state.is_terminal():
                        if state.to_move == "student":
                            move = student_agent.choose_move(state)
                        else:
                            t_start = time.time()
                            move = proctor_agent.choose_move(state)
                            t_end = time.time()

                            total_time += (t_end - t_start)
                            proctor_moves += 1
                            if hasattr(proctor_agent, "nodes_expanded"):
                                total_nodes += proctor_agent.nodes_expanded
                            if hasattr(proctor_agent, "depth_reached"):
                                last_depth_reached = proctor_agent.depth_reached

                        if move is None:
                            break
                        state = state.apply(move)
                        turns = state.turn

                    winner = state.winner() or "draw"
                    avg_time = total_time / max(1, proctor_moves)

                    writer.writerow({
                        "agent": agent_name,
                        "student_type": student_name,
                        "starts": starts_str,
                        "winner": winner,
                        "turns": turns,
                        "nodes_expanded": total_nodes,
                        "time_per_move": round(avg_time, 5),
                        "depth_reached": last_depth_reached,
                    })

    print(f"Tournament results saved to {csv_path}")


def run_pruning_study(map_file_path="maps/its_sukolilo.json", num_games=50, depths=(1, 2, 3, 4, 5), seed=123):
    """
    Pruning study: compare Minimax(d) and fixed-depth AlphaBeta(d) for d=1..5.
    Logs to logs/pruning_study.csv.
    """
    csv_path = "logs/pruning_study.csv"
    map_data = load_map(map_file_path)
    goal = map_data["goal"]
    graph = build_graph(map_data)
    eval_func = EvaluationFunction(graph)

    candidate_starts = allowed_player_starts(map_data, MIN_START_HOPS)

    fieldnames = ["depth", "agent", "avg_nodes_expanded", "avg_time_per_move"]
    print(f"\nRunning Pruning Study (depths {depths}, {num_games} games each)...")

    rows = []
    for d in depths:
        print(f"  -> Testing Depth {d}...")
        for agent_type in ["Minimax", "AlphaBeta"]:
            total_nodes = 0
            total_time = 0.0
            total_moves = 0

            for game_id in range(num_games):
                current_seed = seed + game_id
                rng = random.Random(current_seed)
                student_start = rng.choice(candidate_starts)
                proctor_start = pick_ai_start(map_data, student_start, seed=current_seed)

                state = GameState.from_map(map_data, student=student_start, proctor=proctor_start, turn_limit=TURN_LIMIT)
                student = SimulatedStudentGreedy(graph, goal)

                if agent_type == "Minimax":
                    proctor = MinimaxAgent(eval_func, depth=d)
                else:
                    proctor = AlphaBetaAgent(eval_func, depth=d, iterative_deepening=False)

                while not state.is_terminal():
                    if state.to_move == "student":
                        mv = student.choose_move(state)
                    else:
                        t0 = time.time()
                        mv = proctor.choose_move(state)
                        t1 = time.time()
                        total_time += (t1 - t0)
                        total_nodes += proctor.nodes_expanded
                        total_moves += 1
                    if mv is None:
                        break
                    state = state.apply(mv)

            avg_nodes = total_nodes / max(1, total_moves)
            avg_time = total_time / max(1, total_moves)
            rows.append({
                "depth": d,
                "agent": agent_type,
                "avg_nodes_expanded": round(avg_nodes, 2),
                "avg_time_per_move": round(avg_time, 5),
            })

    with open(csv_path, mode="w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Pruning study saved to {csv_path}")


if __name__ == "__main__":
    run_tournament()
    run_pruning_study()