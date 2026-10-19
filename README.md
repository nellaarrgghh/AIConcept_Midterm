# OTW Practicum: Campus Pursuit

Turn-based Human (Student) vs. AI (Proctor) chase game on an 11-node graph of the ITS Sukolilo campus.

**Live Demo:** https://aiconcept-midterm.onrender.com/

| NRP | Name |
| --- | --- |
| 5025251258 | Naila Sa'ada Cahyani |
| 5025251171 | Daniel Pedrosaputra |
| 5025251001 | Naura Rizky Ameira | 
| 5025251168 | Lina Fatima Azzahra |

---

## How to Play

### Objective
You play as the Student trying to reach the Informatics (`Teknik Informatika`) building within 6 turns without getting caught by the Proctor (AI).

### Rules
* **Turns:** The game is turn-based. You move first, then the Proctor moves.
* **Actions:**
  * Move to an adjacent node connected by an edge.
  * Wait by clicking your current node (Student can wait; Proctor cannot wait and must move to an adjacent node).
* **Win/Loss Conditions:**
  * **Win:** Reach the Informatics node within 6 turns.
  * **Loss:** The Proctor lands on your node (or you land on the Proctor's node), or 6 turns pass before you reach the goal.

### Controls and Game Flow
1. Open the game via the live demo link or locally at `http://127.0.0.1:5001/`.
2. Choose a difficulty level:
   * **Easy:** Uniform Cost Search (UCS) follows the shortest path.
   * **Medium:** Minimax at depth 3.
   * **Hard:** Alpha-Beta pruning with 1.0 s iterative deepening.
3. Choose your starting position by clicking one of the highlighted green nodes (nodes at least 2 hops away from Informatics).
4. Each turn, click an adjacent connected node to move, or click your own node to wait.
5. Toggle "Show distances" to show or hide edge distances in meters.
6. The HUD tracks the current turn (out of 6), player status, and the move history log.

---

## Directory Structure

```text
AIConcept_Midterm/
├── Procfile                    # Render start command
├── README.md                   # Project documentation
├── render.yaml                 # Render deployment configuration
├── requirements.txt            # Python dependencies for deployment
└── otw-practicum/              # Main game code
    ├── agents/                 # AI algorithms (UCS, Minimax, Alpha-Beta, Random)
    ├── assets/                 # Images, sprites, and campus map graphic
    ├── engine/                 # Game rules, state tracking, and graph utilities
    ├── experiments/            # Tournament and plotting scripts
    ├── logs/                   # Simulation CSVs and generated plot images
    ├── maps/                   # Campus map graph JSON files and builder script
    ├── scripts/                # Map diagnostics and game balance checks
    ├── tests/                  # Unit and integration tests (pytest)
    ├── web/                    # Frontend HTML, CSS, JavaScript files
    ├── play_random.py          # Script to run a random game simulation
    ├── pytest.ini              # Pytest configuration
    ├── requirements.txt        # Local environment dependencies
    └── server.py               # Flask backend server
```

### Directory Details

* **`otw-practicum/agents/`**: AI movement and decision logic.
  * `ucs_agent.py`: Chases using Dijkstra / Uniform Cost Search shortest path.
  * `minimax_agent.py`: Minimax search to depth 3.
  * `alphabeta_agent.py`: Minimax with Alpha-Beta pruning and time-limited iterative deepening.
  * `evaluation.py`: Heuristic scoring functions for Minimax and Alpha-Beta.
  * `random_agent.py`: Chooses random legal moves (used as a baseline).
* **`otw-practicum/assets/`**: Static images used by the web frontend.
  * `ITS_Sukolio.jpg`: Campus map background image.
  * `avg_player.jpg`, `scared_player.jpg`, `win_player.jpg`, `lose_player.jpg`: Student reaction avatars.
  * `proctor.jpeg`: Proctor avatar.
* **`otw-practicum/engine/`**: Core logic shared by the server and experiments.
  * `game_state.py`: Game rules, turn handling, valid move checks, and win/loss detection.
  * `graph_utils.py`: Shortest path calculations, hop distances, and graph validation.
* **`otw-practicum/experiments/`**:
  * `tournament.py`: Runs automated matches between agents to collect win rates and stats.
  * `plots.py`: Generates charts from experiment data.
* **`otw-practicum/logs/`**: Experiment output files.
  * `tournament_results.csv`, `pruning_study.csv`: Benchmark data.
  * `plots/`: Output folder for generated charts.
* **`otw-practicum/maps/`**: Graph data for the ITS Sukolilo campus.
  * `its_sukolilo.json`: Active map with 11 nodes, coordinates, and distances in meters.
  * `build_map.py`: Script used to build map JSON files from campus coordinates.
* **`otw-practicum/scripts/`**: Utility scripts for graph metrics and balance testing (`balance_check.py`, `map_report.py`).
* **`otw-practicum/tests/`**: Pytest test suite covering game rules, graph math, search algorithms, and server endpoints.
* **`otw-practicum/web/`**: Browser client files (`index.html`, `game.js`, `style.css`, `preview.html`).

---

## Quick Start (Local Setup)

Run from `otw-practicum/`:

```bash
cd otw-practicum
pip install -r requirements.txt
```

### Run Tests

```bash
python -m pytest
```

### Start Server

```bash
python server.py
```

The game runs at `http://127.0.0.1:5001`.

---

## Running Experiments

Run agent tournaments:
```bash
python experiments/tournament.py
```

Generate charts:
```bash
python experiments/plots.py
```

Generated plots are saved to `logs/plots/`:
* `win_rate_by_agent_student.png`
* `pruning_study_nodes_vs_depth.png`
* `nodes_expanded_comparison.png`
* `depth_reached_comparison.png`