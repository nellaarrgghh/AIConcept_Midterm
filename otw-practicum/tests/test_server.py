"""
Tests for server.py (BE-1), using Flask's test client (no real server needed).
Run from otw-practicum/:  python -m pytest
"""

import pytest

import server


@pytest.fixture
def client():
    return server.app.test_client()


def start(client, difficulty="easy", player_start="gate_main"):
    return client.post("/new_game", json={"difficulty": difficulty, "player_start": player_start})


def test_get_map(client):
    r = client.get("/map")
    assert r.status_code == 200
    assert r.get_json()["goal"] == "informatics"
    assert r.get_json()["allowed_starts"] == ["gate_main", "library", "rectorate"]
    assert r.headers.get("Access-Control-Allow-Origin") == "*"  # CORS enabled


def test_new_game_returns_initial_state(client):
    r = start(client)
    assert r.status_code == 200
    s = r.get_json()
    assert s["turn"] == 0 and s["student"] == "gate_main" and s["to_move"] == "student"
    assert s["winner"] is None and s["difficulty"] == "easy"
    assert s["proctor"] not in ("gate_main", "informatics")


@pytest.mark.parametrize("body", [
    {"difficulty": "easy", "player_start": "nowhere"},       # not a node
    {"difficulty": "easy", "player_start": "informatics"},   # the goal
    {"difficulty": "easy", "player_start": "canteen"},       # within 250 m
    {"difficulty": "impossible", "player_start": "gate_main"},
    {},
])
def test_new_game_rejects_bad_input(client, body):
    r = client.post("/new_game", json=body)
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_move_applies_human_then_ai(client):
    state = {"turn": 0, "student": "gate_main", "proctor": "tower",
             "to_move": "student", "winner": None, "difficulty": "medium"}
    r = client.post("/move", json={"state": state, "move": "library"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["state"]["student"] == "library"
    assert data["ai_move"] in ("tower", "rectorate", "informatics")
    assert data["state"]["proctor"] == data["ai_move"]
    assert data["state"]["turn"] == 1 and data["state"]["to_move"] == "student"


def test_move_that_ends_game_has_no_ai_reply(client):
    state = {"turn": 0, "student": "canteen", "proctor": "gate_main",
             "to_move": "student", "winner": None, "difficulty": "hard"}
    r = client.post("/move", json={"state": state, "move": "informatics"})
    data = r.get_json()
    assert r.status_code == 200
    assert data["ai_move"] is None and data["state"]["winner"] == "student"


@pytest.mark.parametrize("state_patch, move", [
    ({}, "informatics"),                       # not adjacent to gate_main
    ({"student": "nowhere"}, "gate_main"),     # bad node in state
    ({"to_move": "proctor"}, "gate_main"),     # not the human's turn
    ({"difficulty": "x"}, "gate_main"),        # bad difficulty
    ({"turn": 5}, "gate_main"),                # turn limit (5) reached: game over
])
def test_move_rejects_bad_input(client, state_patch, move):
    state = {"turn": 0, "student": "gate_main", "proctor": "tower",
             "to_move": "student", "winner": None, "difficulty": "easy"}
    state.update(state_patch)
    r = client.post("/move", json={"state": state, "move": move})
    assert r.status_code == 400
    assert "error" in r.get_json()
