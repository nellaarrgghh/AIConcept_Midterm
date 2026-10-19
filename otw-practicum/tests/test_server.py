"""
Tests for server.py (Nel), using Flask's test client (no real server needed).
Run from otw-practicum/:  python -m pytest tests/test_server.py
"""

import os
import pytest

import server


@pytest.fixture
def client():
    return server.app.test_client()





def start(client, difficulty="easy", player_start=None):
    if player_start is None:
        player_start = server.ALLOWED_STARTS[0]
    return client.post("/new_game", json={"difficulty": difficulty, "player_start": player_start})


def test_get_map(client):
    r = client.get("/map")
    assert r.status_code == 200
    data = r.get_json()
    assert data["goal"] == server.GOAL
    assert data["turn_limit"] == server.TURN_LIMIT
    assert data["allowed_starts"] == list(server.ALLOWED_STARTS)
    assert data["min_start_hops"] == server.MIN_START_HOPS
    assert len(data["nodes"]) == len(server.MAP_DATA["nodes"])
    assert len(data["edges"]) == len(server.MAP_DATA["edges"])
    assert r.headers.get("Access-Control-Allow-Origin") == "*"  # CORS enabled


def test_new_game_returns_initial_state(client):
    start_node = server.ALLOWED_STARTS[0]
    r = start(client, player_start=start_node)
    assert r.status_code == 200
    s = r.get_json()
    assert s["turn"] == 0 and s["student"] == start_node and s["to_move"] == "student"
    assert s["winner"] is None and s["difficulty"] == "easy"
    assert s["turn_limit"] == server.TURN_LIMIT
    assert s["allowed_starts"] == list(server.ALLOWED_STARTS)
    assert s["proctor"] != start_node and s["proctor"] != server.GOAL


def test_new_game_enforces_start_rule(client):
    # Any node adjacent to the goal (1 hop away) must be rejected with 400
    goal_neighbors = list(server.ADJ[server.GOAL].keys())
    assert len(goal_neighbors) > 0
    bad_start = goal_neighbors[0]
    r = client.post("/new_game", json={"difficulty": "medium", "player_start": bad_start})
    assert r.status_code == 400
    err = r.get_json()["error"]
    assert "hop" in err.lower() and "allowed starts" in err.lower()


def test_server_agent_loader_refuses_missing_agent_without_flag(monkeypatch):
    # Without ALLOW_STUB_AGENTS=1, loading an invalid agent must raise RuntimeError
    monkeypatch.delenv("ALLOW_STUB_AGENTS", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        server.load_agent("agents.missing_module", "MissingAgent", {})
    assert "Could not load agent" in str(exc_info.value)
    assert "ALLOW_STUB_AGENTS=1" in str(exc_info.value)

    # With ALLOW_STUB_AGENTS=1, it must fall back to RandomAgent stub
    monkeypatch.setenv("ALLOW_STUB_AGENTS", "1")
    agent, label = server.load_agent("agents.missing_module", "MissingAgent", {})
    assert "RandomAgent (STUB)" in label
    assert isinstance(agent, server.RandomAgent)


@pytest.mark.parametrize("body", [
    {"difficulty": "easy", "player_start": "nowhere"},       # not a node
    {"difficulty": "easy", "player_start": server.GOAL},      # the goal
    {"difficulty": "impossible", "player_start": "main_gate"}, # invalid difficulty
    {},                                                        # missing fields
])
def test_new_game_rejects_bad_input(client, body):
    r = client.post("/new_game", json=body)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_move_applies_human_then_ai(client):
    # Find a valid start and one of its neighbors
    student_node = list(server.ADJ.keys())[0]
    neighbor = list(server.ADJ[student_node].keys())[0]
    proctor_node = [n for n in server.ADJ.keys() if n not in (student_node, neighbor)][0]

    state = {
        "turn": 0,
        "student": student_node,
        "proctor": proctor_node,
        "to_move": "student",
        "winner": None,
        "difficulty": "medium",
    }
    r = client.post("/move", json={"state": state, "move": neighbor})
    assert r.status_code == 200
    data = r.get_json()
    assert data["state"]["student"] == neighbor
    assert data["ai_move"] is not None
    assert data["state"]["proctor"] == data["ai_move"]
    assert data["state"]["turn"] == 1 and data["state"]["to_move"] == "student"


def test_move_that_ends_game_has_no_ai_reply(client):
    # Student adjacent to goal moves directly to goal
    goal = server.GOAL
    student_node = list(server.ADJ[goal].keys())[0]
    proctor_node = [n for n in server.ADJ.keys() if n not in (student_node, goal)][0]

    state = {
        "turn": 0,
        "student": student_node,
        "proctor": proctor_node,
        "to_move": "student",
        "winner": None,
        "difficulty": "hard",
    }
    r = client.post("/move", json={"state": state, "move": goal})
    data = r.get_json()
    assert r.status_code == 200
    assert data["ai_move"] is None and data["state"]["winner"] == "student"


@pytest.mark.parametrize("state_patch, move", [
    ({}, "non_existent_node"),                  # bad move
    ({"student": "nowhere"}, "main_gate"),       # bad node in state
    ({"to_move": "proctor"}, "main_gate"),       # not the human's turn
    ({"difficulty": "x"}, "main_gate"),          # bad difficulty
    ({"turn": 100}, "main_gate"),                # turn limit reached
])
def test_move_rejects_bad_input(client, state_patch, move):
    first_node = list(server.ADJ.keys())[0]
    second_node = list(server.ADJ.keys())[1]
    state = {
        "turn": 0,
        "student": first_node,
        "proctor": second_node,
        "to_move": "student",
        "winner": None,
        "difficulty": "easy",
    }
    state.update(state_patch)
    r = client.post("/move", json={"state": state, "move": move})
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_static_asset_serving(client):
    r = client.get("/assets/proctor.jpeg")
    assert r.status_code == 200


def test_replays_endpoint_and_saving(client):
    # Winning move saves a replay
    goal = server.GOAL
    student_node = list(server.ADJ[goal].keys())[0]
    proctor_node = [n for n in server.ADJ.keys() if n not in (student_node, goal)][0]

    state = {
        "turn": 0,
        "student": student_node,
        "proctor": proctor_node,
        "to_move": "student",
        "winner": None,
        "difficulty": "easy",
    }
    r = client.post("/move", json={"state": state, "move": goal})
    assert r.status_code == 200

    r_list = client.get("/replays")
    assert r_list.status_code == 200
    data = r_list.get_json()
    assert "replays" in data
    assert len(data["replays"]) > 0
