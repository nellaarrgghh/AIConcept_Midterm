"""
Test for Minimax & AlphaBeta Agents in BE-2.
Run from otw-practicum/: py tests/test_minimax_alphabeta.py
"""

import sys
import os
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.game_state import load_map, pick_ai_start, allowed_player_starts, GameState
from agents.minimax_agent import MinimaxAgent
from agents.alphabeta_agent import AlphaBetaAgent
from agents.evaluation import EvaluationFunction

def test_100_states_equivalence():
    map_path = os.path.join(os.path.dirname(__file__), '..', 'maps', 'test_map.json')
    map_data = load_map(map_path)
    
    valid_nodes = allowed_player_starts(map_data)
    if not valid_nodes:
        print("Error: No valid player start nodes found meeting the minimum distance requirement.")
        return

    sample_state = GameState.from_map(map_data, valid_nodes[0], pick_ai_start(map_data, valid_nodes[0], 42))
    eval_func = EvaluationFunction(sample_state.adj)
    
    depth = 3
    minimax_agent = MinimaxAgent(eval_func, depth=depth)
    alphabeta_agent = AlphaBetaAgent(eval_func, depth=depth, iterative_deepening=False)
    
    matches = 0
    num_tests = 100
    
    print(f"Running {num_tests} state equivalence test between Minimax and Alpha-Beta at depth {depth}...")
    
    for i in range(num_tests):
        seed = 1000 + i
        rng = random.Random(seed)
        student_start = rng.choice(valid_nodes)
        proctor_start = pick_ai_start(map_data, student_start, seed=seed)
        
        state = GameState.from_map(map_data, student=student_start, proctor=proctor_start)
        if state.is_terminal():
            continue
        
        move_mm = minimax_agent.choose_move(state)
        move_ab = alphabeta_agent.choose_move(state)
        
        if move_mm == move_ab:
            matches += 1
        else:
            print(f"Mismatch on seed {seed}: Minimax chose {move_mm}, AlphaBeta chose {move_ab}")
    
    print(f"Result: {matches}/{num_tests} states matched.")
    assert matches == num_tests, f"Requirement 3 FAILED: Only {matches}/{num_tests} matched!"
    print("Minimax and Alpha-Beta are fully equivalent.")

if __name__ == "__main__":
    test_100_states_equivalence()