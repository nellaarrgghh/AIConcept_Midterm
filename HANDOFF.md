# Project Handoff

## 1. PROJECT
Turn-based Human (Student) vs. AI (Proctor) chase on the ITS Sukolilo hand-drawn schematic graph (11 nodes, 18 edges, goal `informatics`). Human races to Informatics; AI catches human or turn limit runs out. Alternating turns, Student first. Player picks start ($\ge 2$ hops from goal); AI start is random (seeded, not player's, not goal). Difficulty: Easy = UCS, Medium = Minimax (depth 3), Hard = Alpha-Beta (iterative deepening with 1.0 s budget, capped at remaining plies). Midterm project comparing 3 algorithms for AI Concept course.

## 2. DECISIONS
- Hand-drawn 11-node schematic map used (`maps/its_sukolilo.json`), NOT OSM. No rain/shade.
- Edge costs are walking meters. UCS navigates by shortest meter distance.
- Minimax & Alpha-Beta evaluate using shortest hop distance: `dist(proctor, student) - dist(student, goal)` (cached all-pairs BFS table).
- Goal ID is read dynamically from `map_data["goal"]` / `state.goal` across engine, agents, and server. Never hardcoded.
- Turn limit is $T = 6$ rounds. The Proctor wins when `turn >= turn_limit`.
- Start rule: player start must be $\ge 2$ hops from the goal (`MIN_START_HOPS = 2`). Enforced strictly by server `/new_game` (returns HTTP 400 if violated).
- Proctor cannot wait: `state.legal_moves()` for the Proctor excludes its current node (unless isolated without neighbors). The Student can still wait.
- Minimax and Alpha-Beta use depth-dependent terminal scores (faster catch scores higher for Proctor, later loss is preferred) and tie-breaking by hop distance to student so they choose identical moves at equal depth.
- Hard mode: iterative deepening with 1.0 s time limit, capped at remaining plies until turn limit, always finishes at least depth 1.
- Agent loading: server fails at startup with a clear `RuntimeError` if an agent cannot be imported, unless `ALLOW_STUB_AGENTS=1` is explicitly set.

## 3. FILE MAP & INTERFACES
- `otw-practicum/engine/`:
  - `game_state.py`: `GameState(adj, goal, student, proctor, to_move, turn, turn_limit)` with `.legal_moves()`, `.apply(move)`, `.winner()`, `.utility(player)`. Helpers: `load_map(path)`, `build_adjacency(m)`, `validate_map(m)`, `pick_ai_start(m, start, seed, min_hops)`, `allowed_player_starts(m, min_hops)`.
  - `graph_utils.py`: `build_graph(map_or_state)`, `hop_distance(g, a, b)`, `meter_distance(g, a, b)`, `all_pairs_hop_distances(g)`, `all_pairs_meter_distances(g)`.
- `otw-practicum/agents/`:
  - `ucs_agent.py`: `UCSAgent(graph=None)` with `.choose_move(state)`.
  - `evaluation.py`: `EvaluationFunction(graph_or_adj)` with `.evaluate(state)`, `.terminal_score(state, depth)`, `.tiebreak_key(state, move)`, and `pick_root_move()`.
  - `minimax_agent.py`: `MinimaxAgent(eval_func=None, depth=3)` with `.choose_move(state)`.
  - `alphabeta_agent.py`: `AlphaBetaAgent(eval_func=None, depth=3, iterative_deepening=False, time_limit=1.0)` with `.choose_move(state)`, tracks `.depth_reached` and `.nodes_expanded`.
  - `random_agent.py`: `RandomAgent(seed=None)`.
- `otw-practicum/server.py`: Flask stateless REST API running on port 5001. Constants: `TURN_LIMIT = 6`, `MIN_START_HOPS = 2`.
  - `GET /map` -> returns map JSON with extra fields `turn_limit`, `allowed_starts`, `min_start_hops`.
  - `POST /new_game` -> `{"difficulty": "...", "player_start": "..."}` -> returns state JSON with `turn_limit` and `allowed_starts`.
  - `POST /move` -> `{"state": {...}, "move": "...", "moves": [...]}` -> returns `{"state": {...}, "ai_move": "...", "moves": [...]}`.
  - `GET /replays` -> returns `{"replays": [...]}` from `web/replays/`.
  - Static: `/` serves `web/index.html`, `/assets/<file>` serves `assets/`.
- `otw-practicum/web/`: `game.js` (`CampusMapRenderer.render`, `animateMove`, `setStudentState`, `hopDistance`), `index.html`, `style.css`, `preview.html`.
- `otw-practicum/scripts/`: `balance_check.py` (game balance simulation across turn limits and difficulties).
- `otw-practicum/experiments/`: `tournament.py` (tournament & depth 1-5 pruning study), `plots.py` (generates plots in `logs/plots/`).

## 4. DONE & VERIFIED
- Engine & Server: 58/58 unit tests pass (`pytest tests/`). Validated startup checks, hop-based start validation, and agent loader fallback guard.
- Graph weights: `build_graph()` ensures explicit `weight`/`meters` attributes; true meter cost verified.
- Minimax & Alpha-Beta equivalence: Verified identical moves across 100 random states for depths 1-4.
- Idle bug eliminated: Proctor cannot wait, catch depth scoring rewards immediate captures, and secondary tie-break moves toward student.
- Curve & Canvas rendering: Informatics &rarr; Electrical Eng edge curve set to `-160` (arcs outward around Chemical Eng). Edge costs drawn as pills at edge midpoints with a "Show distances" toggle. Legend moved to top-left to avoid covering Electrical Eng.
- Endpoints verified via tests: `/map`, `/new_game`, `/move`, `/replays`. Replays auto-saved on terminal moves.
- Player sprites: HUD and canvas circular crop ($r=20$) support `avg`, `scared`, `lose`, `win`.

## 5. KNOWN ISSUES AND TODO
- [x] Proctor idle bug: Resolved (no Proctor waiting, depth-dependent terminal scores, distance tie-break).
- [x] Edge curve direction: In `maps/its_sukolilo.json`, curve on `informatics`-`electrical_eng` changed to `-160`.
- [x] Distance labels: Walking distance in meters drawn along edge midpoints with toggle.
- [x] Legend positioning: Legend moved to top-left (x=16, y=16), completely clearing Electrical Eng.
- [x] Turn limit balance: Turn limit $T=6$ and $\ge 2$ hops start rule set as single source of truth in `server.py`.
- [ ] Group D: Run `scripts/balance_check.py`, inspect balance table, confirm $T$, then rerun tournament and plots.

## 6. HOW TO RUN
From the workspace (`searchAlgo_project`):
```bash
# Virtual environment is at searchAlgo_project/.venv
cd otw-practicum
../../.venv/bin/pytest tests/
../../.venv/bin/python3 server.py                # Server runs on http://127.0.0.1:5001
# In another terminal:
../../.venv/bin/python3 experiments/tournament.py
../../.venv/bin/python3 experiments/plots.py
```
Open game: `http://127.0.0.1:5001/` | Preview page: `http://127.0.0.1:5001/preview.html`

## 7. RULES FOR THE NEXT AGENT
- Keep changes minimal and focused. Do not refactor unnecessarily.
- Do NOT rename public classes, functions, or API endpoints.
- Ensure Minimax and Alpha-Beta always choose identical moves at matching search depths.
- Run `pytest tests/` and show test outputs after each modification.
- Never commit; the user manages git commits.
