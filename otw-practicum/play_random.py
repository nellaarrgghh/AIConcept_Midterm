"""
Random vs. Random sanity check (Nel).

Plays N games on a map with random start pairs (Student start drawn from the
allowed starts, Proctor start from pick_ai_start) and prints win counts and
average game length. Everything is seeded, so the same command gives the same
numbers.

Usage (from otw-practicum/):
    python play_random.py                       # 100 games, map's default turn limit
    python play_random.py --turn-limit 8        # try a specific limit
    python play_random.py --sweep 1 12          # try limits 1..12 and print a table
"""

import argparse
import random

from agents.random_agent import RandomAgent
from engine.game_state import (
    GameState, allowed_player_starts, build_adjacency, default_turn_limit,
    load_map, pick_ai_start,
)


def play_game(map_data, student_agent, proctor_agent, student_start, proctor_start, turn_limit):
    """Play one game to the end. Returns (winner, rounds, how) where how is 'goal', 'catch' or 'timeout'."""
    state = GameState.from_map(map_data, student_start, proctor_start, turn_limit)
    while not state.is_terminal():
        agent = student_agent if state.to_move == "student" else proctor_agent
        state = state.apply(agent.choose_move(state))

    # Rounds played, counting a round the Student ended early by reaching the goal or walking into the Proctor.
    rounds = state.turn + (1 if state.to_move == "proctor" else 0)
    if state.student == state.proctor:
        how = "catch"
    elif state.student == state.goal:
        how = "goal"
    else:
        how = "timeout"
    return state.winner(), rounds, how


def run_games(map_data, games, turn_limit, seed):
    """Play `games` seeded games and return a summary dict."""
    master = random.Random(seed)  # one master generator; every other seed comes from it
    student = RandomAgent(master.randrange(2**32))
    proctor = RandomAgent(master.randrange(2**32))
    starts = allowed_player_starts(map_data)

    counts = {"goal": 0, "catch": 0, "timeout": 0}
    total_rounds = 0
    for _ in range(games):
        s_start = master.choice(starts)
        p_start = pick_ai_start(map_data, s_start, master.randrange(2**32))
        _, rounds, how = play_game(map_data, student, proctor, s_start, p_start, turn_limit)
        counts[how] += 1
        total_rounds += rounds

    return {
        "turn_limit": turn_limit,
        "student": counts["goal"],
        "proctor": counts["catch"] + counts["timeout"],
        "catch": counts["catch"],
        "timeout": counts["timeout"],
        "avg_rounds": total_rounds / games,
    }


def print_summary(r, games):
    print("Turn limit %d, %d games" % (r["turn_limit"], games))
    print("  Student wins: %3d  (%.0f%%)" % (r["student"], 100.0 * r["student"] / games))
    print("  Proctor wins: %3d  (%.0f%%)  catch %d, timeout %d"
          % (r["proctor"], 100.0 * r["proctor"] / games, r["catch"], r["timeout"]))
    print("  Average game length: %.2f rounds" % r["avg_rounds"])


def main():
    parser = argparse.ArgumentParser(description="Random vs. Random games")
    parser.add_argument("--map", default="maps/test_map.json")
    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--turn-limit", type=int, default=None,
                        help="default: ceil(1.5 * longest shortest path in hops)")
    parser.add_argument("--sweep", type=int, nargs=2, metavar=("LO", "HI"),
                        help="try every turn limit from LO to HI")
    args = parser.parse_args()

    map_data = load_map(args.map)

    if args.sweep:
        lo, hi = args.sweep
        print("%d games per limit, seed %d" % (args.games, args.seed))
        print("limit  student%  proctor%  (catch / timeout)  avg rounds")
        for t in range(lo, hi + 1):
            r = run_games(map_data, args.games, t, args.seed)
            print("%5d  %7.0f%%  %7.0f%%  (%5d / %7d)  %10.2f"
                  % (t, 100.0 * r["student"] / args.games, 100.0 * r["proctor"] / args.games,
                     r["catch"], r["timeout"], r["avg_rounds"]))
        return

    limit = args.turn_limit if args.turn_limit is not None else default_turn_limit(build_adjacency(map_data))
    print_summary(run_games(map_data, args.games, limit, args.seed), args.games)


if __name__ == "__main__":
    main()
