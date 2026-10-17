"""
Campus Pursuit Flask API (owned by BE-1). Stateless: the browser keeps the
game state and sends it back with every move. See docs/interface.md.

Run (from otw-practicum/, with the venv active):
    python server.py                 # http://127.0.0.1:5001
Environment variables (all optional):
    CAMPUS_MAP   path to the map JSON  (default: maps/its_sukolilo.json if it exists, else maps/test_map.json)
    SERVER_SEED  seed for AI starts and stub agents (default: 0)
    PORT         port to listen on (default: 5001; macOS AirPlay already uses 5000)
"""

import importlib
import os
import random

from flask import Flask, jsonify, request
from flask_cors import CORS

from agents.random_agent import RandomAgent
from engine.game_state import (
    STUDENT, GameState, allowed_player_starts, build_adjacency, default_turn_limit,
    load_map, pick_ai_start,
)

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Map (loaded once at startup)
# ---------------------------------------------------------------------------

def default_map_path():
    real = os.path.join(HERE, "maps", "its_sukolilo.json")  # FE-1's real map
    stub = os.path.join(HERE, "maps", "test_map.json")      # BE-1's stub
    return real if os.path.exists(real) else stub


MAP_PATH = os.environ.get("CAMPUS_MAP", default_map_path())
MAP_DATA = load_map(MAP_PATH)
ADJ = build_adjacency(MAP_DATA)        # shared by every GameState, never modified
GOAL = MAP_DATA["goal"]
TURN_LIMIT = default_turn_limit(ADJ)   # not in the state JSON; derived from the map
ALLOWED_STARTS = allowed_player_starts(MAP_DATA)  # sent with GET /map for the start picker

# One seeded generator for the whole server. Every random choice comes from it,
# so a fresh server with the same SERVER_SEED replays the same sequence.
SEED = int(os.environ.get("SERVER_SEED", "0"))
server_rng = random.Random(SEED)


# ---------------------------------------------------------------------------
# Difficulty -> agent (one dict)
# ---------------------------------------------------------------------------

# difficulty: (module, class name, constructor arguments). Agents come from BE-2.
DIFFICULTIES = {
    "easy":   ("agents.ucs_agent",       "UCSAgent",       {}),
    "medium": ("agents.minimax_agent",   "MinimaxAgent",   {"depth": 3}),
    "hard":   ("agents.alphabeta_agent", "AlphaBetaAgent", {"time_limit": 1.0}),
}


def load_agent(module_name, class_name, kwargs):
    """
    Create the real agent if its file exists. If the file is missing (the
    teammate has not pushed it yet), fall back to the random STUB agent.
    Bugs inside an existing agent file are NOT hidden: they crash at startup.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise  # the agent file exists but imports something missing: show it
        return RandomAgent(server_rng.randrange(2**32)), "RandomAgent (STUB, %s.py missing)" % module_name.replace(".", "/")
    return getattr(module, class_name)(**kwargs), class_name


AGENTS = {}
for _difficulty, (_module, _cls, _kwargs) in DIFFICULTIES.items():
    AGENTS[_difficulty], _label = load_agent(_module, _cls, _kwargs)
    print("[server] %-6s -> %s" % (_difficulty, _label))


# ---------------------------------------------------------------------------
# State JSON <-> GameState
# ---------------------------------------------------------------------------

class BadRequest(Exception):
    """Raised for invalid client input; turned into an HTTP 400 response."""


def state_to_json(state, difficulty):
    return {
        "turn": state.turn,
        "student": state.student,
        "proctor": state.proctor,
        "to_move": state.to_move,
        "winner": state.winner(),
        "difficulty": difficulty,
    }


def check_difficulty(difficulty):
    if difficulty not in DIFFICULTIES:
        raise BadRequest("Unknown difficulty %r. Use one of: %s"
                         % (difficulty, ", ".join(DIFFICULTIES)))


def state_from_json(data):
    """Rebuild a GameState from the client's JSON, checking every field."""
    if not isinstance(data, dict):
        raise BadRequest("'state' must be an object")
    for key in ("turn", "student", "proctor", "to_move", "difficulty"):
        if key not in data:
            raise BadRequest("state is missing %r" % key)
    check_difficulty(data["difficulty"])
    for key in ("student", "proctor"):
        if data[key] not in ADJ:
            raise BadRequest("state.%s %r is not a node on the map" % (key, data[key]))
    turn = data["turn"]
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 0:
        raise BadRequest("state.turn must be a non-negative integer")
    if data["to_move"] != STUDENT:
        raise BadRequest("It is not the student's turn (to_move is %r)" % data["to_move"])
    return GameState(ADJ, GOAL, data["student"], data["proctor"], STUDENT, turn, TURN_LIMIT)


def get_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("Request body must be a JSON object (send Content-Type: application/json)")
    return body


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)  # the page is hosted elsewhere (GitHub Pages / file://)


@app.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify({"error": str(err)}), 400


@app.get("/map")
def get_map():
    # The map file plus the nodes the player may start on (copy, so MAP_DATA is untouched).
    return jsonify(dict(MAP_DATA, allowed_starts=ALLOWED_STARTS))


@app.post("/new_game")
def new_game():
    body = get_body()
    difficulty = body.get("difficulty")
    player_start = body.get("player_start")
    check_difficulty(difficulty)
    if player_start not in ADJ:
        raise BadRequest("player_start %r is not a node on the map" % (player_start,))

    try:  # also enforces: not the goal, at least MIN_START_DISTANCE from it
        ai_start = pick_ai_start(MAP_DATA, player_start, server_rng.randrange(2**32))
    except ValueError as e:
        raise BadRequest(str(e))

    state = GameState(ADJ, GOAL, player_start, ai_start, STUDENT, 0, TURN_LIMIT)
    return jsonify(state_to_json(state, difficulty))


@app.post("/move")
def move():
    body = get_body()
    if "state" not in body or "move" not in body:
        raise BadRequest("Body must contain 'state' and 'move'")
    state = state_from_json(body["state"])
    difficulty = body["state"]["difficulty"]
    human_move = body["move"]

    if state.is_terminal():
        raise BadRequest("The game is already over (winner: %s)" % state.winner())
    legal = state.legal_moves()
    if human_move not in legal:
        raise BadRequest("Illegal move %r from %r. Legal moves: %s"
                         % (human_move, state.student, ", ".join(legal)))

    state = state.apply(human_move)  # Student's move
    ai_move = None
    if not state.is_terminal():      # Proctor replies only if the game goes on
        ai_move = AGENTS[difficulty].choose_move(state)
        state = state.apply(ai_move)  # raises (HTTP 500) if an agent returns an illegal move

    return jsonify({"state": state_to_json(state, difficulty), "ai_move": ai_move})


if __name__ == "__main__":
    print("[server] map %s, turn limit %d, seed %d" % (MAP_PATH, TURN_LIMIT, SEED))
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5001")), debug=False)
