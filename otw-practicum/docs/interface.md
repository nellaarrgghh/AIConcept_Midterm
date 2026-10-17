# Campus Pursuit: Engine Interface

Owner: BE-1 (engine lead). This is the contract between the engine, the agents (BE-2), and the web page (FE). **Do not change anything here without telling BE-1.** Source of truth: [`engine/game_state.py`](../engine/game_state.py).

All examples below use the stub map `maps/test_map.json` and were run against the real engine.

## 1. Rules in one table

| Rule | Detail |
| --- | --- |
| Sides | `student` (human) and `proctor` (AI) |
| Order | Alternating turns, Student first |
| A move | Go to a neighbor of your node, or stay on your node (wait) |
| Proctor wins | Both pieces on the same node (either side moving onto the other), or `turn` reaches `turn_limit` |
| Student wins | Student is on the goal node (`informatics`) and not on the Proctor's node |
| Check order | catch, then goal, then turn limit. So reaching the goal on the last round still wins |
| `turn` | Completed rounds. Goes up by 1 after each Proctor move |
| `turn_limit` | Default `ceil(1.5 * longest shortest path in hops)`. Test map: 5 |
| Player start | Chosen by the player. Must be at least `MIN_START_DISTANCE` = 250 m (shortest walking distance) from the goal |
| AI start | Random (seeded), any node except the player's start and the goal |

## 2. Map JSON

```json
{
  "nodes": [{"id": "gate_main", "x": 100, "y": 350}, ...],
  "edges": [{"from": "gate_main", "to": "library", "cost": 120}, ...],
  "goal": "informatics"
}
```

- Edges are **undirected**. `cost` is walking distance in meters. `x`, `y` are canvas pixels.
- Start nodes are not in the file. Extra keys (such as `_comment`) are ignored.
- The graph must be connected (the engine raises `ValueError` otherwise).

## 3. Moves

A move is a **node id string**, for example `"library"`. Waiting = returning your own current node id. There is no separate "wait" token.

## 4. GameState

```python
from engine.game_state import GameState, load_map
state = GameState.from_map(load_map("maps/test_map.json"), student="gate_main", proctor="tower")
```

### Fields (read them, never assign them)

| Field | Type | Meaning |
| --- | --- | --- |
| `turn` | int | Completed rounds, starts at 0 |
| `student` | str | Student's node id |
| `proctor` | str | Proctor's node id |
| `to_move` | str | `"student"` or `"proctor"` |
| `turn_limit` | int | Proctor wins when `turn >= turn_limit` |
| `goal` | str | Goal node id (`"informatics"`) |
| `adj` | dict | `{node: {neighbor: cost_in_meters}}`. **Shared by every state in a game. Never modify it.** Use it for UCS / Dijkstra |

### Methods

| Method | Returns | Notes |
| --- | --- | --- |
| `legal_moves()` | list of node ids | Current node (wait) first, then neighbors in map-file order. Empty list if the game is over. Order is fixed, so Minimax and Alpha-Beta see moves in the same order |
| `apply(move)` | new `GameState` | Never changes the old state. Raises `ValueError` for an illegal move or a finished game |
| `copy()` | new `GameState` | Cheap: copies small fields, shares `adj` |
| `winner()` | `"student"`, `"proctor"`, or `None` | |
| `is_terminal()` | bool | `winner() is not None` |
| `utility(player)` | +1, -1, or 0 | +1 if `player` has won, -1 if lost, 0 while ongoing |

### Helper functions (same module)

| Function | Use |
| --- | --- |
| `load_map(path)` | Read map JSON into a dict |
| `build_adjacency(map_data)` | The `adj` dict described above |
| `shortest_distances(adj, source)` | Dijkstra: `{node: meters}` from `source`. Handy for the evaluation function's distance table |
| `default_turn_limit(adj)` | The default `turn_limit` |
| `allowed_player_starts(map_data)` | Node ids the Student may start on (use this in tournaments too) |
| `pick_ai_start(map_data, player_start, seed)` | Checks the player's start, returns a random Proctor start |

### Example

```python
>>> s = GameState.from_map(m, "gate_main", "tower")
>>> s
GameState(turn=0/5, student='gate_main', proctor='tower', to_move='student')
>>> s.legal_moves()
['gate_main', 'library', 'rectorate']        # wait, then neighbors
>>> s.adj["gate_main"]
{'library': 120, 'rectorate': 150}
>>> s1 = s.apply("library")                  # Student moves
>>> s1.to_move, s1.legal_moves()
('proctor', ['tower', 'rectorate', 'informatics'])
>>> s2 = s1.apply("rectorate")               # Proctor moves, round complete
>>> s2.turn, s2.winner(), s2.utility("student")
(1, None, 0)
>>> s.student                                # original state unchanged
'gate_main'
```

## 5. Agent interface

Every agent is a class with one required method:

```python
class MyAgent:
    def choose_move(self, state):
        """Return one node id from state.legal_moves()."""
```

Rules for agents:

- Play the side given by `state.to_move` (the server only asks the Proctor, but tournaments may use agents for the Student too).
- Return a value that is in `state.legal_moves()`. The engine rejects anything else.
- Never modify `state` or `state.adj`. Use `state.apply(move)` to look ahead.
- Seed any randomness through the constructor (see `agents/random_agent.py`).
- Only `choose_move` is required. Extra attributes for experiments (such as `nodes_expanded`, `depth_reached`) are welcome; the server ignores them.

### How the server will create agents (proposed, confirm with BE-1)

| Difficulty | File | Class and constructor |
| --- | --- | --- |
| `easy` | `agents/ucs_agent.py` | `UCSAgent()` |
| `medium` | `agents/minimax_agent.py` | `MinimaxAgent(depth=3)` |
| `hard` | `agents/alphabeta_agent.py` | `AlphaBetaAgent(time_limit=1.0)` |

Until these files exist, the server uses a stub that plays random legal moves for every difficulty.

> Tip for Minimax / Alpha-Beta: `utility()` is only ±1, while the evaluation function is in meters. Score terminal states with a number larger than any evaluation value (for example ±100000) so a real win always beats a good-looking position.

### Minimal example

```python
from agents.random_agent import RandomAgent
from engine.game_state import GameState, load_map, pick_ai_start

m = load_map("maps/test_map.json")
state = GameState.from_map(m, "gate_main", pick_ai_start(m, "gate_main", seed=42))
student, proctor = RandomAgent(seed=1), RandomAgent(seed=2)
while not state.is_terminal():
    agent = student if state.to_move == "student" else proctor
    state = state.apply(agent.choose_move(state))
print(state.winner())
```

## 6. State JSON (Flask API)

The server is stateless: the browser keeps the state and sends it back with every move.

```json
{"turn": 0, "student": "gate_main", "proctor": "library", "to_move": "student", "winner": null, "difficulty": "easy"}
```

| Key | Type | Meaning |
| --- | --- | --- |
| `turn` | int | Same as `GameState.turn` |
| `student` | str | Student's node id |
| `proctor` | str | Proctor's node id |
| `to_move` | str | `"student"` or `"proctor"` |
| `winner` | str or null | `"student"`, `"proctor"`, or `null` while the game is on |
| `difficulty` | str | `"easy"`, `"medium"` or `"hard"`. Set by `/new_game`. The server is stateless, so this is how `/move` knows which AI replies. Send it back unchanged |

`turn_limit` is not in the JSON. The server derives it from the map on every request.

### Endpoints

Default address: `http://127.0.0.1:5001` (port 5000 is taken by AirPlay on macOS).

| Endpoint | Request body | Response |
| --- | --- | --- |
| `GET /map` | none | The map JSON (section 2) plus `"allowed_starts": ["gate_main", "library", "rectorate"]`, the nodes the player may pick as a start. Highlight only these in the start picker |
| `POST /new_game` | `{"difficulty": "easy", "player_start": "gate_main"}` | Initial state JSON |
| `POST /move` | `{"state": {...}, "move": "library"}` | `{"state": {...}, "ai_move": "tower"}` |

- `POST /move` applies the human's move, then the AI replies. If the human's move ends the game, `ai_move` is `null` and the returned state already has `winner` set.
- Invalid input returns HTTP 400 with `{"error": "..."}`: unknown difficulty, unknown node, start too close to the goal, illegal move, not the student's turn, or the game is already over.

Example game (real responses from the server with the stub agents):

```
POST /new_game {"difficulty": "easy", "player_start": "gate_main"}
-> {"turn": 0, "student": "gate_main", "proctor": "library", "to_move": "student", "winner": null, "difficulty": "easy"}

POST /move {"state": {"turn": 0, "student": "gate_main", "proctor": "tower", "to_move": "student", "winner": null, "difficulty": "medium"}, "move": "library"}
-> {"state": {"turn": 1, "student": "library", "proctor": "tower", "to_move": "student", "winner": null, "difficulty": "medium"},
    "ai_move": "tower"}

POST /move {"state": {..., "student": "gate_main", ...}, "move": "informatics"}
-> 400 {"error": "Illegal move 'informatics' from 'gate_main'. Legal moves: gate_main, library, rectorate"}
```

(Proctor start and replies depend on the server seed and the agent.)
