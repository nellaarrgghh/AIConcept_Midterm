"""
Campus Pursuit Flask API (owned by Nel). Stateless: the browser keeps the
game state and sends it back with every move. See docs/interface.md.

Run (from otw-practicum/, with the venv active):
    python server.py                 # http://127.0.0.1:5001
Environment variables (all optional):
    CAMPUS_MAP         path to the map JSON  (default: maps/its_sukolilo.json if it exists, else maps/test_map.json)
    SERVER_SEED        seed for AI starts and stub agents (default: 0)
    PORT               port to listen on (default: 5001; macOS AirPlay already uses 5000)
    ALLOW_STUB_AGENTS  set to 1 to replace an agent that fails to import with a
                       RandomAgent stub. Without it the server refuses to start.
"""

import importlib
import json
import logging
import os
import random
import time

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from agents.random_agent import RandomAgent
from engine.game_state import (
    STUDENT, GameState, allowed_player_starts, load_map, pick_ai_start,
    validate_map, validate_player_start,
)

HERE = os.path.dirname(os.path.abspath(__file__))
logger = logging.getLogger("campus_pursuit")

# ---------------------------------------------------------------------------
# Game constants (single source of truth; the front end and
# experiments/tournament.py read these, never hardcode them)
# ---------------------------------------------------------------------------

TURN_LIMIT = 6        # rounds; the Proctor wins when turn reaches this
MIN_START_HOPS = 2    # player start must be at least this many edges from the goal


# ---------------------------------------------------------------------------
# Map & Startup Validation
# ---------------------------------------------------------------------------

def default_map_path():
    real = os.path.join(HERE, "maps", "its_sukolilo.json")
    stub = os.path.join(HERE, "maps", "test_map.json")
    return real if os.path.exists(real) else stub


MAP_PATH = os.environ.get("CAMPUS_MAP", default_map_path())
MAP_DATA = load_map(MAP_PATH)

# Startup validation check:
# Fails with a clear message unless: every edge endpoint is a node, no duplicate edges,
# the graph is connected, and the goal is reachable from every node.
try:
    ADJ = validate_map(MAP_DATA)
except ValueError as e:
    raise RuntimeError("Map validation failed for %s: %s" % (MAP_PATH, e)) from e

GOAL = MAP_DATA["goal"]
ALLOWED_STARTS = allowed_player_starts(MAP_DATA, MIN_START_HOPS)
if not ALLOWED_STARTS:
    raise RuntimeError("Map %s has no node at least %d hops from the goal %r"
                       % (MAP_PATH, MIN_START_HOPS, GOAL))

SEED = int(os.environ.get("SERVER_SEED", "0"))
server_rng = random.Random(SEED)


# ---------------------------------------------------------------------------
# Difficulty -> agent (one dict)
# ---------------------------------------------------------------------------

DIFFICULTIES = {
    "easy":   ("agents.ucs_agent",       "UCSAgent",       {}),
    "medium": ("agents.minimax_agent",   "MinimaxAgent",   {"depth": 3}),
    # Iterative deepening, 1 s per move, depth capped at the plies left until the turn limit.
    "hard":   ("agents.alphabeta_agent", "AlphaBetaAgent", {"iterative_deepening": True, "time_limit": 1.0}),
}


def stubs_allowed():
    return os.environ.get("ALLOW_STUB_AGENTS", "") == "1"


def load_agent(module_name, class_name, kwargs, allow_stub=None):
    """
    Create the real agent. If the import fails the server refuses to start
    (RuntimeError), unless stubs are allowed (ALLOW_STUB_AGENTS=1), in which
    case a RandomAgent stub is used and a loud warning is printed.
    """
    if allow_stub is None:
        allow_stub = stubs_allowed()
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return cls(**kwargs), class_name
    except Exception as e:
        if not allow_stub:
            raise RuntimeError(
                "Could not load agent %s.%s (%s: %s). Fix the import, or set "
                "ALLOW_STUB_AGENTS=1 to run with a RandomAgent stub instead."
                % (module_name, class_name, type(e).__name__, e)) from e
        logger.warning("Could not load %s.%s (%s). Using RandomAgent stub (ALLOW_STUB_AGENTS=1).", module_name, class_name, e)
        print("[server WARNING] Could not load %s.%s (%s). Using RandomAgent stub (ALLOW_STUB_AGENTS=1)." % (module_name, class_name, e))
        return RandomAgent(server_rng.randrange(2**32)), "RandomAgent (STUB)"


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
        "turn_limit": state.turn_limit,
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
    # Goal is always read from the map (GOAL = MAP_DATA["goal"])
    return GameState(ADJ, GOAL, data["student"], data["proctor"], STUDENT, turn, TURN_LIMIT)


def get_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise BadRequest("Request body must be a JSON object (send Content-Type: application/json)")
    return body


# ---------------------------------------------------------------------------
# Flask app & static routes
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)

WEB_DIR = os.path.join(HERE, "web")
ASSETS_DIR = os.path.join(HERE, "assets")


@app.errorhandler(BadRequest)
def handle_bad_request(err):
    return jsonify({"error": str(err)}), 400


@app.route("/")
def serve_root():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def serve_web(path):
    # Exclude API endpoints from static fallthrough
    if path in ("map", "new_game", "move"):
        raise BadRequest("Endpoint /%s requires HTTP method" % path)
    return send_from_directory(WEB_DIR, path)


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.get("/map")
def get_map():
    # The map JSON plus the server's game constants (extra fields, map is not modified)
    data = dict(MAP_DATA)
    data["turn_limit"] = TURN_LIMIT
    data["allowed_starts"] = list(ALLOWED_STARTS)
    data["min_start_hops"] = MIN_START_HOPS
    return jsonify(data)


@app.post("/new_game")
def new_game():
    body = get_body()
    difficulty = body.get("difficulty")
    player_start = body.get("player_start")
    check_difficulty(difficulty)

    if not player_start:
        raise BadRequest("player_start is required")

    try:
        # Must be a real node, not the goal, and at least MIN_START_HOPS from the goal
        validate_player_start(MAP_DATA, player_start, min_hops=MIN_START_HOPS)
        ai_start = pick_ai_start(MAP_DATA, player_start, server_rng.randrange(2**32))
    except ValueError as e:
        raise BadRequest(str(e))

    state = GameState(ADJ, GOAL, player_start, ai_start, STUDENT, 0, TURN_LIMIT)
    data = state_to_json(state, difficulty)
    data["allowed_starts"] = list(ALLOWED_STARTS)
    return jsonify(data)


REPLAYS_DIR = os.path.join(WEB_DIR, "replays")
os.makedirs(REPLAYS_DIR, exist_ok=True)


@app.get("/replays")
def list_replays():
    """List saved replay files in web/replays/."""
    try:
        files = [f for f in os.listdir(REPLAYS_DIR) if f.endswith(".json")]
        files.sort(reverse=True)
        return jsonify({"replays": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

    # Track moves history if provided by client (or initialize)
    moves_history = list(body.get("moves", []))
    player_start = body.get("player_start", state.student)
    ai_start = body.get("ai_start", state.proctor)

    state = state.apply(human_move)  # Student's move
    ai_move = None
    if not state.is_terminal():      # Proctor replies only if the game goes on
        ai_move = AGENTS[difficulty].choose_move(state)
        state = state.apply(ai_move)

    moves_history.append({
        "turn": state.turn,
        "student": state.student,
        "proctor": state.proctor,
    })

    # When a game ends, save replay JSON to web/replays/
    if state.is_terminal():
        replay_data = {
            "difficulty": difficulty,
            "player_start": player_start,
            "ai_start": ai_start,
            "moves": moves_history,
            "winner": state.winner(),
        }
        filename = f"replay_{int(time.time()*1000)}_{difficulty}_{state.winner()}.json"
        replay_path = os.path.join(REPLAYS_DIR, filename)
        try:
            with open(replay_path, "w", encoding="utf-8") as f:
                json.dump(replay_data, f, indent=2)
        except Exception as e:
            logger.error("Failed to write replay: %s", e)

    return jsonify({
        "state": state_to_json(state, difficulty),
        "ai_move": ai_move,
        "moves": moves_history
    })


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5001"))
    print("[server] map %s, turn limit %d, seed %d, listening on %s:%d" % (MAP_PATH, TURN_LIMIT, SEED, host, port))
    app.run(host=host, port=port, debug=False)
