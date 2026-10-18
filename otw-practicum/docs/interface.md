# Campus Pursuit: Engine & API Interface Contract

Owner: BE-1 (Engine Lead). This document describes the formal contract between the game engine, the AI agents (BE-2), and the frontend client (FE). Source of truth: [`engine/game_state.py`](../engine/game_state.py).

---

## 1. Rules

| Rule | Detail |
| --- | --- |
| Sides | `student` (human) and `proctor` (AI) |
| Order | Alternating turns, Student moves first |
| Move | Traverse one undirected edge to an adjacent neighbor. The Student may also wait (stay on current node). The Proctor may **not** wait (neighbors only; stays put only if isolated without neighbors) |
| Proctor wins | Proctor lands on the Student's node, Student steps onto Proctor, or `turn >= turn_limit` |
| Student wins | Student reaches the goal node (`state.goal`) and does not share a node with the Proctor |
| Resolution Order | Catch is checked first, then Goal, then Turn limit |
| Turn count | `turn` represents completed rounds (increments after the Proctor moves) |
| Turn limit | $T = 6$ completed rounds (defined once as `TURN_LIMIT = 6` in `server.py`) |
| Start positions | Player picks their start node ($\ge 2$ hops away from the goal, `MIN_START_HOPS = 2`). Proctor start is randomly selected (seeded), excluding player start and goal |

---

## 2. Map JSON (`maps/its_sukolilo.json`)

```json
{
  "nodes": [
    {"id": "main_gate", "label": "Main Gate", "x": 60, "y": 275},
    {"id": "informatics", "label": "Informatics", "x": 880, "y": 202}
  ],
  "edges": [
    {"from": "main_gate", "to": "graha", "cost": 550},
    {"from": "informatics", "to": "electrical_eng", "cost": 1400, "curve": -160}
  ],
  "goal": "informatics"
}
```

* **Attributes**:
  * `id`: unique string node identifier.
  * `label`: display name rendered above nodes.
  * `x`, `y`: pixel coordinates for the canvas ($1000 \times 700$ viewBox).
  * `cost`: walking distance in meters along the edge.
  * `curve` (optional): magnitude of curvature for curved paths (e.g., `-160` for `informatics`-`electrical_eng` bowing outward around Chemical Eng).
  * `goal`: goal node identifier string (dynamic, never hardcoded).

---

## 3. Python Engine Interface (`engine/game_state.py`)

```python
from engine.game_state import GameState, load_map
map_data = load_map("maps/its_sukolilo.json")
state = GameState.from_map(map_data, student="main_gate", proctor="graha", turn_limit=6)
```

### Fields (Read-Only)
* `state.turn`: current completed turn rounds (starts at 0).
* `state.student`: current node id of the student.
* `state.proctor`: current node id of the proctor.
* `state.to_move`: `"student"` or `"proctor"`.
* `state.turn_limit`: maximum turn limit before timeout loss ($T = 6$).
* `state.goal`: target node id (read dynamically from map).
* `state.adj`: shared adjacency dict `{node: {neighbor: cost}}`.

### Methods
* `state.legal_moves()`: Returns list of legal destination node ids:
  * For `student`: waiting (current node) first, then neighbors.
  * For `proctor`: neighbors only (no waiting).
* `state.apply(move)`: Returns a new immutable `GameState` after applying `move`.
* `state.copy()`: Returns a cheap shallow copy sharing the underlying graph.
* `state.winner()`: Returns `"student"`, `"proctor"`, or `None`.
* `state.is_terminal()`: Returns `True` if game has ended.
* `state.utility(player)`: Returns `+1` (win), `-1` (loss), or `0` (ongoing).

---

## 4. Agent Interface (`agents/`)

Every agent provides:
```python
class Agent:
    def choose_move(self, state: GameState) -> str:
        """Return a node id from state.legal_moves()."""
```

* **Easy (`UCSAgent`)**: Uniform Cost Search navigating the shortest meter path to target (`weight='weight'`).
* **Medium (`MinimaxAgent(depth=3)`)**: Fixed-depth game tree search evaluated with BFS hop table (`EvaluationFunction.evaluate`). Depth-dependent terminal score and hop distance tie-breaker.
* **Hard (`AlphaBetaAgent(iterative_deepening=True, time_limit=1.0)`)**: Alpha-Beta pruning with iterative deepening and 1.0 s budget per move. Search depth is capped at remaining plies until the turn limit, always finishes at least depth 1, and stops early when reaching game termination. Records `depth_reached` and `nodes_expanded`.
* **Minimax and Alpha-Beta Equivalence**: At the same fixed depth, both agents produce identical move decisions.

---

## 5. REST API (`server.py`)

Default URL: `http://127.0.0.1:5001`
Startup policy: Refuses to start if agent imports fail, unless `ALLOW_STUB_AGENTS=1` is explicitly set.

### Endpoints

#### 1. `GET /map`
Returns the map JSON with attached server constants.
* **Response (200 OK)**:
  ```json
  {
    "nodes": [...],
    "edges": [...],
    "goal": "informatics",
    "turn_limit": 6,
    "allowed_starts": ["main_gate", "graha", "manarul_ilmi", "canteen", "biology"],
    "min_start_hops": 2
  }
  ```

#### 2. `POST /new_game`
Starts a new session and returns the initial state. Enforces $\ge 2$ hops from goal (returns HTTP 400 if violated).
* **Request**:
  ```json
  {"difficulty": "medium", "player_start": "main_gate"}
  ```
* **Response (200 OK)**:
  ```json
  {
    "difficulty": "medium",
    "proctor": "graha",
    "student": "main_gate",
    "to_move": "student",
    "turn": 0,
    "turn_limit": 6,
    "allowed_starts": ["main_gate", "graha", "manarul_ilmi", "canteen", "biology"],
    "winner": null
  }
  ```

#### 3. `POST /move`
Applies the player's move, calculates the AI's counter-move, and saves replays upon game completion.
* **Request**:
  ```json
  {
    "state": {
      "difficulty": "medium",
      "proctor": "graha",
      "student": "main_gate",
      "to_move": "student",
      "turn": 0,
      "turn_limit": 6,
      "winner": null
    },
    "move": "manarul_ilmi",
    "moves": []
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "ai_move": "main_gate",
    "state": {
      "difficulty": "medium",
      "proctor": "main_gate",
      "student": "manarul_ilmi",
      "to_move": "student",
      "turn": 1,
      "turn_limit": 6,
      "winner": null
    },
    "moves": [{"turn": 1, "student": "manarul_ilmi", "proctor": "main_gate"}]
  }
  ```

#### 4. `GET /replays`
Lists all recorded game replay JSON files stored in `web/replays/`.
* **Response (200 OK)**:
  ```json
  {
    "replays": ["replay_1729241850123_medium_student.json"]
  }
  ```
