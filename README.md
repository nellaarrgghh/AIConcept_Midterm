# OTW Practicum: Campus Pursuit

Turn-based Human (Student) vs. AI (Proctor) chase game on an 11-node graph of the ITS Sukolilo campus.

| NRP | Name | Role |
| --- | --- | --- |
| 5025251258 | Naila Sa'ada Cahyani | BE-1 (Engine Lead, Server, Visuals) |
| 5025251171 | Daniel Pedrosaputra | BE-2 (Agents, Tournament, Plots) |
| 5025251001 | Naura Rizky Ameira | FE-1 (Map Dataset & Visuals) |
| 5025251168 | Lina Fatima Azzahra | FE-2 (Web UI & Interaction) |

---

## 1. Quick Start

All commands can be run from the `otw-practicum/` directory with the repository virtual environment:

```bash
cd otw-practicum
source ../../.venv/bin/activate  # venv located at searchAlgo_project/.venv
```

*(Dependencies: `flask`, `flask-cors`, `networkx`, `pandas`, `matplotlib`, `pytest`)*

### Run Unit Tests

```bash
python -m pytest
```

### Start the Game Server

```bash
python server.py
```
By default, the server runs on `http://127.0.0.1:5001`. (Port 5001 is used because AirPlay Receiver typically reserves 5000 on macOS).

### Play the Game
Open `http://127.0.0.1:5001/` in your browser.
* Select difficulty (`easy` = UCS, `medium` = Minimax depth 3, `hard` = Alpha-Beta with 1.0 s iterative deepening).
* Click a highlighted green node ($\ge 2$ hops away from the goal) to select your start position.
* Navigate edge-by-edge toward **Informatics** before the Proctor catches you or turn limits ($T = 6$) expire!
* Check or uncheck **Show distances** to toggle meter labels along edge paths.
* Notice: Student may wait; Proctor cannot wait. If an agent import fails, server halts unless `ALLOW_STUB_AGENTS=1`.

### Developer Preview Page
Visit `http://127.0.0.1:5001/preview.html` to inspect canvas rendering, edge curves, and piece animations.

---

## 2. Running Experiments & Analysis

Run the tournament simulations and pruning benchmark:
```bash
python experiments/tournament.py
```
Generate performance charts:
```bash
python experiments/plots.py
```
Generated plots are saved to `logs/plots/`:
* `win_rate_by_agent_student.png`
* `pruning_study_nodes_vs_depth.png`
* `nodes_expanded_comparison.png`
* `depth_reached_comparison.png`