"""
Orchestrates automated game tournaments between AI
agents and simulated students for BE-2.

Run from project root: py experiments/tournament.py
"""

import os
import csv
import sys
import time
import random
import networkx as nx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.game_state import load_map, pick_ai_start, allowed_player_starts, GameState
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent
from agents.ucs_agent import UCSAgent
from agents.evaluation import EvaluationFunction

class SimulatedStudentGreedy:
    def __init__(self, graph):
        self.graph = graph if isinstance(graph, nx.Graph) else nx.Graph(graph)

    def choose_move(self, state):
        try:
            path = nx.shortest_path(self.graph, source=state.student, target=state.goal, weight='meters')
            if len(path) > 1:
                next_node = path[1]
                for move in state.legal_moves():
                    if move == next_node:
                        return move
        except Exception:
            pass
        legal = state.legal_moves()
        return random.choice(legal) if legal else None

class SimulatedStudentRandom:
    def choose_move(self, state):
        legal = state.legal_moves()
        return random.choice(legal) if legal else None

def run_tournament(map_file_path="maps/test_map.json", num_games=100, seed=42):
    os.makedirs('logs', exist_ok=True)
    csv_path = 'logs/tournament_results.csv'
    
    map_data = load_map(map_file_path)
    sample_state = GameState.from_map(map_data, map_data["nodes"][0]["id"], map_data["nodes"][1]["id"])
    graph = nx.Graph(sample_state.adj)
    eval_func = EvaluationFunction(graph)
    
    proctors = {
        'UCS': UCSAgent(graph),
        'Minimax_Depth3': MinimaxAgent(eval_func, depth=3),
        'AlphaBeta': AlphaBetaAgent(eval_func, depth=3, iterative_deepening=True, time_limit=1.0)
    }
    
    students = {
        'Greedy': SimulatedStudentGreedy(graph),
        'Random': SimulatedStudentRandom()
    }
    
    fieldnames = ['agent', 'student_type', 'starts', 'winner', 'turns', 'nodes_expanded', 'time_per_move']
    
    print(f"Starting tournament: {num_games} games per agent/student pairing...")
    with open(csv_path, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for agent_name, proctor_agent in proctors.items():
            for student_name, student_agent in students.items():
                for game_id in range(num_games):
                    current_seed = seed + game_id
                    rng = random.Random(current_seed)
                    
                    valid_nodes = allowed_player_starts(map_data)
                    student_start = rng.choice(valid_nodes)
                    proctor_start = pick_ai_start(map_data, student_start, seed=current_seed)
                    
                    state = GameState.from_map(map_data, student=student_start, proctor=proctor_start)
                    starts_str = f"Student:{student_start}|Proctor:{proctor_start}"
                    
                    turns = 0
                    total_nodes = 0
                    total_time = 0.0
                    move_counts = 0
                    
                    while not state.is_terminal() and turns < state.turn_limit:
                        t_start = time.time()
                        if state.to_move == 'proctor':
                            move = proctor_agent.choose_move(state)
                            if hasattr(proctor_agent, 'nodes_expanded'):
                                total_nodes += proctor_agent.nodes_expanded
                        else:
                            move = student_agent.choose_move(state)
                        
                        t_end = time.time()
                        if state.to_move == 'proctor':
                            total_time += (t_end - t_start)
                            move_counts += 1
                        
                        if move is None:
                            break
                        state = state.apply(move)
                        turns += 1
                        
                    winner = state.winner() or 'draw'
                    avg_time = total_time / max(1, move_counts)
                    
                    writer.writerow({
                        'agent': agent_name,
                        'student_type': student_name,
                        'starts': starts_str,
                        'winner': winner,
                        'turns': turns,
                        'nodes_expanded': total_nodes,
                        'time_per_move': round(avg_time, 4)
                    })
    print(f"Tournament completed. Logged to {csv_path}")

if __name__ == "__main__":
    run_tournament()